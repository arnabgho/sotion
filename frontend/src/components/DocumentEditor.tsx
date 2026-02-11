import { useState } from "react";
import type { Document } from "../types";
import { MarkdownMessage } from "./MarkdownMessage";

const API_URL = "http://localhost:8000/api";

interface Props {
  channelId: string;
  document?: Document; // For editing existing doc
  onClose: () => void;
  onSave: () => void;
}

export function DocumentEditor({ channelId, document, onClose, onSave }: Props) {
  const [title, setTitle] = useState(document?.title || "");
  const [content, setContent] = useState(document?.content || "");
  const [docType, setDocType] = useState(document?.doc_type || "note");
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const handleSave = async () => {
    if (!title.trim()) {
      alert("Title is required");
      return;
    }

    setSaving(true);
    try {
      if (document) {
        // Edit existing document
        const response = await fetch(`${API_URL}/documents/${document.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
        });

        if (!response.ok) throw new Error("Failed to update document");
      } else {
        // Create new document
        const response = await fetch(`${API_URL}/documents`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            channel_id: channelId,
            title,
            content,
            doc_type: docType,
          }),
        });

        if (!response.ok) throw new Error("Failed to create document");
      }

      onSave();
      onClose();
    } catch (error) {
      console.error("Failed to save document:", error);
      alert("Failed to save document");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content doc-editor-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{document ? "Edit Document" : "New Document"}</h2>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label>Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Document title..."
              disabled={!!document} // Can't change title when editing
              autoFocus
            />
          </div>

          <div className="form-group">
            <label>Type</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              disabled={!!document} // Can't change type when editing
            >
              <option value="note">Note</option>
              <option value="project_plan">Project Plan</option>
              <option value="task">Task</option>
              <option value="learnings">Learnings</option>
            </select>
          </div>

          <div className="form-group">
            <div className="editor-toolbar">
              <label>Content (Markdown)</label>
              <button
                className="btn-preview-toggle"
                onClick={() => setShowPreview(!showPreview)}
                type="button"
              >
                {showPreview ? "Edit" : "Preview"}
              </button>
            </div>

            {showPreview ? (
              <div className="doc-preview">
                <MarkdownMessage content={content || "_No content yet_"} />
              </div>
            ) : (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={"Write in markdown...\n\n## Example\n- Bullet points\n- **Bold text**\n- `code`"}
                rows={15}
              />
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : document ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
