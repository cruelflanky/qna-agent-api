"""OpenAI function/tool definitions for the agent."""

KB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "Search the knowledge base for relevant information. "
            "Use this tool when you need factual information to answer user questions. "
            "The knowledge base contains documents about company policies, "
            "products, and procedures."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query to find relevant documents. "
                        "Use keywords related to the user's question."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}

# List of all available tools
AVAILABLE_TOOLS = [KB_SEARCH_TOOL]

# Tool name to function mapping (used by agent)
TOOL_NAMES = {
    "search_knowledge_base": "search_knowledge_base",
}
