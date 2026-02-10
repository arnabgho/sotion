"""Document lifecycle: staleness detection and review triggers."""

from datetime import datetime

from loguru import logger

from sotion.documents.manager import DocumentManager


class DocumentLifecycle:
    """Monitors document freshness and triggers reviews."""

    def __init__(self, doc_manager: DocumentManager):
        self.doc_manager = doc_manager

    async def check_staleness(self, channel_id: str) -> list[dict]:
        """Check for stale documents and return review suggestions."""
        stale = await self.doc_manager.find_stale_documents(channel_id)
        suggestions = []
        for doc in stale:
            days_old = (datetime.now() - doc.updated_at).days
            suggestions.append({
                "document_id": doc.id,
                "title": doc.title,
                "days_since_update": days_old,
                "suggestion": f"Document '{doc.title}' hasn't been updated in {days_old} days. "
                f"Consider reviewing or archiving.",
            })
            logger.info(f"Stale document: {doc.title} ({days_old} days)")
        return suggestions
