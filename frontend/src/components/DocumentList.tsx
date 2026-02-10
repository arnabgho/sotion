import { useEffect, useState } from "react";
import type { Document } from "../types";

const API_URL = "http://localhost:8000/api";

interface Props {
  channelId: string;
}

export function DocumentList({ channelId }: Props) {
  const [docs, setDocs] = useState<Document[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/channels/${channelId}/documents`)
      .then((r) => r.json())
      .then(setDocs)
      .catch(console.error);
  }, [channelId]);

  if (docs.length === 0) return null;

  return (
    <div className="document-list">
      <h3>Documents</h3>
      {docs.map((doc) => (
        <div key={doc.id} className="document-item">
          <span className="doc-type-badge">{doc.doc_type}</span>
          <span className="doc-title">{doc.title}</span>
          <span className="doc-version">v{doc.version}</span>
        </div>
      ))}
    </div>
  );
}
