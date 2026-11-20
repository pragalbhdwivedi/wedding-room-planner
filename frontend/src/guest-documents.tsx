import { useCallback, useEffect, useState } from "react";

type Document = { id: string; created_at: string };
type Props = {
  guestId: string;
  revision: number;
  canUpload: boolean;
  request: (path: string, options?: RequestInit) => Promise<any>;
  refresh: () => Promise<void>;
};

export function GuestDocuments({ guestId, revision, canUpload, request, refresh }: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState<File[]>([]);
  const [message, setMessage] = useState("");
  const base = `/guests/${guestId}/documents`;
  const load = useCallback(async () => {
    const result = await request(`/guests/${guestId}/documents`);
    setDocuments(result.documents);
  }, [guestId, request]);

  useEffect(() => {
    setLoading(true);
    load().catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [load]);

  async function upload() {
    if (!selected.length || uploading) return;
    setError("");
    setMessage("");
    setUploading(true);
    let nextRevision = revision;
    let added = 0;
    try {
      for (const file of selected) {
        if (file.size > 5 * 1024 * 1024) throw Error("Choose ID images of up to 5 MiB each.");
        const body = new FormData();
        body.append("file", file);
        body.append("revision", String(nextRevision));
        const result = await request(base, { method: "POST", body });
        nextRevision = result.revision;
        if (!result.duplicate) added++;
      }
      setSelected([]);
      setMessage(added ? `${added} ID image${added === 1 ? "" : "s"} uploaded.` : "These images are already attached.");
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load().catch((e) => setError(e.message));
      await refresh().catch((e) => setError(e.message));
      setUploading(false);
    }
  }

  return (
    <section className="guest-documents">
      <p>Reception can view these IDs and download or print the PDF.</p>
      {error && <div className="alert error" role="alert">{error}</div>}
      {message && <p role="status">{message}</p>}
      {canUpload && (
        <div className="id-upload-controls">
          <label>
            ID images (front and back)
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              disabled={uploading}
              onChange={(e) => setSelected(Array.from(e.target.files || []))}
            />
          </label>
          <small>JPG, PNG or WebP, up to 5 MiB each. Attach images to the matching person.</small>
          <button type="button" className="primary compact" onClick={upload} disabled={uploading || !selected.length}>
            {uploading ? "Uploading…" : `Upload${selected.length ? ` ${selected.length} image${selected.length === 1 ? "" : "s"}` : " ID images"}`}
          </button>
        </div>
      )}
      {loading && <p role="status">Loading ID images…</p>}
      {!loading && !documents.length && <p>No ID images attached yet.</p>}
      {documents.length > 0 && (
        <>
          <div className="id-pdf-actions">
            <a className="primary compact" href={`/api/planning/guests/${guestId}/documents.pdf`} target="_blank" rel="noopener noreferrer">Open / print PDF</a>
            <a href={`/api/planning/guests/${guestId}/documents.pdf?download=true`} download>Download PDF</a>
          </div>
          <div className="id-image-grid">
            {documents.map((doc, index) => (
              <a key={doc.id} href={`/api/planning${base}/${doc.id}/image`} target="_blank" rel="noopener noreferrer">
                <img src={`/api/planning${base}/${doc.id}/image`} alt={`ID image ${index + 1}`} loading="lazy" />
                <span>Image {index + 1}</span>
              </a>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
