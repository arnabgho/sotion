"""Document manager: CRUD with versioning and lifecycle."""

from datetime import datetime, timedelta

from sotion.db.queries import DBQueries
from sotion.db.models import Document


class DocumentManager:
    """Manages document lifecycle including staleness detection."""

    STALENESS_DAYS = 14

    def __init__(self, db: DBQueries):
        self.db = db

    async def create(
        self,
        channel_id: str,
        title: str,
        content: str,
        doc_type: str = "note",
        created_by: str | None = None,
    ) -> Document:
        doc = Document(
            channel_id=channel_id,
            title=title,
            content=content,
            doc_type=doc_type,
            created_by=created_by,
            last_edited_by=created_by,
        )
        return await self.db.create_document(doc)

    async def update(
        self, doc_id: str, content: str, edited_by: str
    ) -> Document | None:
        return await self.db.update_document(doc_id, content, edited_by)

    async def get(self, doc_id: str) -> Document | None:
        return await self.db.get_document(doc_id)

    async def list_for_channel(
        self, channel_id: str, doc_type: str | None = None
    ) -> list[Document]:
        return await self.db.list_channel_documents(channel_id, doc_type)

    async def find_stale_documents(self, channel_id: str) -> list[Document]:
        """Find documents that haven't been updated in STALENESS_DAYS."""
        docs = await self.db.list_channel_documents(channel_id)
        cutoff = datetime.now() - timedelta(days=self.STALENESS_DAYS)
        return [d for d in docs if d.updated_at < cutoff]
