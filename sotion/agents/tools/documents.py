"""Document tools: create, edit, and query channel documents."""

from typing import Any

from sotion.agent.tools.base import Tool
from sotion.db.queries import DBQueries
from sotion.db.models import Document


class CreateDocTool(Tool):
    """Tool to create a document in the current channel."""

    def __init__(self, db: DBQueries | None = None, channel_id: str = "", agent_id: str = ""):
        self._db = db
        self._channel_id = channel_id
        self._agent_id = agent_id

    def set_context(self, channel_id: str, agent_id: str) -> None:
        self._channel_id = channel_id
        self._agent_id = agent_id

    @property
    def name(self) -> str:
        return "create_doc"

    @property
    def description(self) -> str:
        return "Create a new document in the current channel. Returns the document ID."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {"type": "string", "description": "Document content (markdown)"},
                "doc_type": {
                    "type": "string",
                    "description": "Document type",
                    "enum": ["project_plan", "task", "note", "learnings"],
                },
            },
            "required": ["title", "content"],
        }

    async def execute(self, title: str = "", content: str = "", doc_type: str = "note", **kwargs: Any) -> str:
        if not self._db:
            return "Error: Database not configured"
        if not self._channel_id:
            return "Error: No channel context set"

        doc = Document(
            channel_id=self._channel_id,
            title=title,
            content=content,
            doc_type=doc_type,
            created_by=self._agent_id,
            last_edited_by=self._agent_id,
        )
        result = await self._db.create_document(doc)
        return f"Document created: '{result.title}' (id: {result.id})"


class EditDocTool(Tool):
    """Tool to edit an existing document."""

    def __init__(self, db: DBQueries | None = None, agent_id: str = ""):
        self._db = db
        self._agent_id = agent_id

    def set_context(self, agent_id: str) -> None:
        self._agent_id = agent_id

    @property
    def name(self) -> str:
        return "edit_doc"

    @property
    def description(self) -> str:
        return "Edit an existing document by ID. Replaces the full content and creates a version snapshot."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID to edit"},
                "content": {"type": "string", "description": "New document content (full replacement)"},
            },
            "required": ["document_id", "content"],
        }

    async def execute(self, document_id: str = "", content: str = "", **kwargs: Any) -> str:
        if not self._db:
            return "Error: Database not configured"

        result = await self._db.update_document(document_id, content, self._agent_id)
        if result:
            return f"Document updated: '{result.title}' (version {result.version})"
        return f"Error: Document '{document_id}' not found"


class QueryDocsTool(Tool):
    """Tool to search/list documents in a channel."""

    def __init__(self, db: DBQueries | None = None, channel_id: str = ""):
        self._db = db
        self._channel_id = channel_id

    def set_context(self, channel_id: str) -> None:
        self._channel_id = channel_id

    @property
    def name(self) -> str:
        return "query_docs"

    @property
    def description(self) -> str:
        return "List or search documents in the current channel."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "description": "Filter by doc type (optional)",
                    "enum": ["project_plan", "task", "note", "learnings"],
                },
            },
        }

    async def execute(self, doc_type: str | None = None, **kwargs: Any) -> str:
        if not self._db:
            return "Error: Database not configured"
        if not self._channel_id:
            return "Error: No channel context set"

        docs = await self._db.list_channel_documents(self._channel_id, doc_type)
        if not docs:
            return "No documents found."

        lines = [f"Found {len(docs)} document(s):\n"]
        for d in docs:
            preview = d.content[:100] + "..." if len(d.content) > 100 else d.content
            lines.append(f"- [{d.doc_type}] {d.title} (id: {d.id}, v{d.version})")
            lines.append(f"  Preview: {preview}\n")
        return "\n".join(lines)
