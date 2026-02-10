import { useEffect, useState } from "react";
import type { Document } from "../types";

const API_URL = "http://localhost:8000/api";

interface Props {
  channelId: string;
}

export function DocumentList({ channelId }: Props) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  useEffect(() => {
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
  }, [channelId]);

  const handleDocClick = (doc: Document) => {
    setSelectedDoc(selectedDoc?.id === doc.id ? null : doc);
  };

  return (
    <div className="document-panel">
      <div className="document-panel-header">
        <h3>Documents</h3>
        <span className="doc-count">{docs.length}</span>
      </div>

      {loading ? (
        <div className="doc-loading">Loading documents...</div>
      ) : docs.length === 0 ? (
        <div className="doc-empty">
          <p>No documents yet</p>
          <p className="doc-hint">Agents can create docs using create_doc tool</p>
        </div>
      ) : (
        <div className="document-list">
          {docs.map((doc) => (
            <div key={doc.id}>
              <button
                className={`document-item ${selectedDoc?.id === doc.id ? "expanded" : ""}`}
                onClick={() => handleDocClick(doc)}
              >
                <div className="doc-header">
                  <span className="doc-type-badge">{doc.doc_type}</span>
                  <span className="doc-title">{doc.title}</span>
                  <span className="doc-version">v{doc.version}</span>
                </div>
              </button>
              {selectedDoc?.id === doc.id && (
                <div className="doc-content">
                  <div className="doc-meta">
                    <span>Status: {doc.status}</span>
                    <span>Created: {new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="doc-body">
                    {doc.content || <em>No content yet</em>}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
