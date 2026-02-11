import { useEffect, useState } from "react";
import type { Document } from "../types";
import { MarkdownMessage } from "./MarkdownMessage";
import { DocumentEditor } from "./DocumentEditor";

const API_URL = "http://localhost:8000/api";

interface Props {
  channelId: string;
}

export function DocumentList({ channelId }: Props) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);

  const refreshDocs = () => {
    setLoading(true);
    fetch(`${API_URL}/channels/${channelId}/documents`)
      .then((r) => r.json())
      .then((data) => {
        setDocs(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load documents:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    refreshDocs();
  }, [channelId]);

  const handleDocClick = (doc: Document) => {
    setSelectedDoc(selectedDoc?.id === doc.id ? null : doc);
  };

  const handleEdit = (doc: Document) => {
    setEditingDoc(doc);
    setShowEditor(true);
  };

  const isStale = (doc: Document) => {
    const daysSinceUpdate = Math.floor(
      (Date.now() - new Date(doc.updated_at).getTime()) / (1000 * 60 * 60 * 24)
    );
    return daysSinceUpdate > 14; // 14 days threshold
  };

  const filteredDocs = docs
    .filter((d) => !filterType || d.doc_type === filterType)
    .filter((d) =>
      searchQuery
        ? d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          d.content.toLowerCase().includes(searchQuery.toLowerCase())
        : true
    );

  return (
    <div className="document-panel">
      <div className="document-panel-header">
        <h3>Documents</h3>
        <button className="btn-new-doc" onClick={() => setShowEditor(true)}>
          + New
        </button>
        <input
          type="text"
          className="doc-search"
          placeholder="Search documents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select
          className="doc-type-filter"
          value={filterType || ""}
          onChange={(e) => setFilterType(e.target.value || null)}
        >
          <option value="">All Types</option>
          <option value="project_plan">Project Plans</option>
          <option value="task">Tasks</option>
          <option value="note">Notes</option>
          <option value="learnings">Learnings</option>
        </select>
        <span className="doc-count">{filteredDocs.length}</span>
      </div>

      {loading ? (
        <div className="doc-loading">Loading documents...</div>
      ) : filteredDocs.length === 0 ? (
        <div className="doc-empty">
          {docs.length === 0 ? (
            <>
              <p>No documents yet</p>
              <p className="doc-hint">Agents can create docs using create_doc tool</p>
            </>
          ) : (
            <p>No documents match your search</p>
          )}
        </div>
      ) : (
        <div className="document-list">
          {filteredDocs.map((doc) => (
            <div key={doc.id}>
              <button
                className={`document-item ${selectedDoc?.id === doc.id ? "expanded" : ""}`}
                onClick={() => handleDocClick(doc)}
              >
                <div className="doc-header">
                  <span className="doc-type-badge">{doc.doc_type}</span>
                  <span className="doc-title">{doc.title}</span>
                  {isStale(doc) && <span className="doc-stale-badge">⚠️ Stale</span>}
                  <span className="doc-version">v{doc.version}</span>
                </div>
              </button>
              {selectedDoc?.id === doc.id && (
                <div className="doc-content">
                  <div className="doc-meta">
                    <span>Status: {doc.status}</span>
                    <span>Created: {new Date(doc.created_at).toLocaleDateString()}</span>
                    <button className="btn-edit-doc" onClick={() => handleEdit(doc)}>
                      Edit
                    </button>
                  </div>
                  <div className="doc-body">
                    {doc.content ? (
                      <MarkdownMessage content={doc.content} />
                    ) : (
                      <em>No content yet</em>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showEditor && (
        <DocumentEditor
          channelId={channelId}
          document={editingDoc || undefined}
          onClose={() => {
            setShowEditor(false);
            setEditingDoc(null);
          }}
          onSave={() => {
            refreshDocs();
          }}
        />
      )}
    </div>
  );
}
