from dataclasses import dataclass
from pathlib import Path

from qna_agent.config import get_settings


@dataclass
class KBSearchResult:
    """Knowledge base search result."""
    filename: str
    content: str
    score: float


class KnowledgeBaseService:
    """Service for knowledge base operations."""

    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or get_settings().knowledge_dir

    def list_files(self) -> list[str]:
        """List all knowledge base files."""
        if not self.knowledge_dir.exists():
            return []

        return [
            f.name
            for f in self.knowledge_dir.iterdir()
            if f.is_file() and f.suffix == ".txt"
        ]

    def read_file(self, filename: str) -> str | None:
        """Read content of a knowledge base file."""
        file_path = self.knowledge_dir / filename
        if not file_path.exists() or not file_path.is_file():
            return None

        # Security: prevent path traversal
        if not file_path.resolve().is_relative_to(self.knowledge_dir.resolve()):
            return None

        return file_path.read_text(encoding="utf-8")

    def search(self, query: str, max_results: int = 3) -> list[KBSearchResult]:
        """
        Search knowledge base for relevant documents.

        Simple scoring algorithm:
        - Filename match: +10 per word match
        - Content match: +1 per occurrence
        """
        query_words = query.lower().split()
        results: list[KBSearchResult] = []

        for filename in self.list_files():
            content = self.read_file(filename)
            if content is None:
                continue

            # Calculate score
            score = 0.0
            filename_lower = filename.lower()
            content_lower = content.lower()

            # Filename matching (higher weight)
            for word in query_words:
                if word in filename_lower:
                    score += 10.0

            # Content matching
            for word in query_words:
                score += content_lower.count(word)

            if score > 0:
                results.append(
                    KBSearchResult(
                        filename=filename,
                        content=content,
                        score=score,
                    )
                )

        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:max_results]

    def format_search_results(self, results: list[KBSearchResult]) -> str:
        """Format search results for LLM consumption."""
        if not results:
            return "No relevant documents found in the knowledge base."

        formatted = []
        for result in results:
            # Truncate long content
            content = result.content
            if len(content) > 1000:
                content = content[:1000] + "..."

            formatted.append(
                f"=== {result.filename} ===\n{content}"
            )

        return "\n\n".join(formatted)
