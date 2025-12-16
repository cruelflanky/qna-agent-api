import asyncio
import json
import logging
from typing import Any

from openai import AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from sqlalchemy.ext.asyncio import AsyncSession

from qna_agent.config import get_settings
from qna_agent.models.db import Message
from qna_agent.services.chat import ChatService, MessageService
from qna_agent.services.knowledge import KnowledgeBaseService
from qna_agent.tools.definitions import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a helpful assistant that answers questions using the knowledge base.

When users ask questions, use the search_knowledge_base tool to find relevant information.
Always base your answers on the information found in the knowledge base.
If you cannot find relevant information, say so honestly.

Be concise and helpful in your responses."""


class AgentService:
    """OpenAI-based QnA agent with function calling."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
        )
        self.chat_service = ChatService(session)
        self.message_service = MessageService(session)
        self.kb_service = KnowledgeBaseService()

    async def process_message(
        self,
        chat_id: str,
        user_content: str,
    ) -> tuple[Message, Message]:
        """
        Process a user message and return the user message and final assistant response.

        This implements the agent loop:
        1. Save user message
        2. Build conversation context
        3. Call LLM with tools
        4. If tool call: execute and loop back to step 3
        5. Return final assistant response
        """
        # Verify chat exists
        chat = await self.chat_service.get_chat(chat_id)
        if chat is None:
            raise ValueError(f"Chat {chat_id} not found")

        # Save user message
        user_message = await self.message_service.create_message(
            chat_id=chat_id,
            role="user",
            content=user_content,
        )

        # Build conversation history
        messages = await self._build_conversation_context(chat_id)

        # Agent loop
        final_response = await self._agent_loop(chat_id, messages)

        # Update chat timestamp
        await self.chat_service.update_chat_timestamp(chat_id)

        return user_message, final_response

    async def _build_conversation_context(
        self,
        chat_id: str,
    ) -> list[ChatCompletionMessageParam]:
        """Build OpenAI messages from conversation history."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        db_messages = await self.message_service.get_all_messages(chat_id)

        for msg in db_messages:
            if msg.role == "user":
                messages.append({
                    "role": "user",
                    "content": msg.content or "",
                })
            elif msg.role == "assistant":
                if msg.tool_calls:
                    # Message with tool calls
                    tool_calls = json.loads(msg.tool_calls)
                    messages.append({
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": tool_calls,
                    })
                else:
                    # Regular assistant message
                    messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                    })
            elif msg.role == "tool":
                messages.append({
                    "role": "tool",
                    "content": msg.content or "",
                    "tool_call_id": msg.tool_call_id or "",
                })

        return messages

    async def _agent_loop(
        self,
        chat_id: str,
        messages: list[ChatCompletionMessageParam],
    ) -> Message:
        """Execute agent loop until final response."""
        max_iterations = 5  # Prevent infinite loops
        max_retries = 3  # Retries for rate limiting

        for iteration in range(max_iterations):
            logger.info(f"Agent loop iteration {iteration + 1}")

            # Call LLM with retry logic
            response = None
            for retry in range(max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.settings.openai_model,
                        messages=messages,
                        tools=AVAILABLE_TOOLS,  # type: ignore
                        tool_choice="auto",
                    )
                    break
                except RateLimitError:
                    if retry < max_retries - 1:
                        wait_time = (retry + 1) * 2  # Exponential backoff
                        logger.warning(f"Rate limited, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise

            if response is None or not response.choices:
                raise ValueError("Empty response from LLM")

            assistant_message = response.choices[0].message

            # Check if we have tool calls
            if assistant_message.tool_calls:
                # Save assistant message with tool calls
                await self.message_service.create_message(
                    chat_id=chat_id,
                    role="assistant",
                    content=assistant_message.content,
                    tool_calls=json.dumps([
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ]),
                )

                # Add to context
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                })

                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    result = await self._execute_tool(tool_call)

                    # Save tool result
                    await self.message_service.create_message(
                        chat_id=chat_id,
                        role="tool",
                        content=result,
                        tool_call_id=tool_call.id,
                    )

                    # Add to context
                    messages.append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": tool_call.id,
                    })

                # Continue loop to get next response
                continue

            # No tool calls - this is the final response
            final_message = await self.message_service.create_message(
                chat_id=chat_id,
                role="assistant",
                content=assistant_message.content or "",
            )
            return final_message

        # Max iterations reached
        error_message = await self.message_service.create_message(
            chat_id=chat_id,
            role="assistant",
            content="I apologize, but I was unable to complete your request. Please try again.",
        )
        return error_message

    async def _execute_tool(self, tool_call: Any) -> str:
        """Execute a tool call and return the result."""
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        logger.info(f"Executing tool: {function_name} with args: {arguments}")

        if function_name == "search_knowledge_base":
            query = arguments.get("query", "")
            results = self.kb_service.search(query)
            return self.kb_service.format_search_results(results)

        return f"Unknown tool: {function_name}"

    async def check_llm_connection(self) -> bool:
        """Check if LLM API is accessible."""
        try:
            # Simple test call
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"LLM connection check failed: {e}")
            return False
