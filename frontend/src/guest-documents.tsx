import { useCallback, useEffect, useState } from "react";

type Document = { id: string; created_at: string; guest_id: string | null; label: string };
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

export function IDCollection({ revision, canUpload, request, refresh, guests }: Omit<Props, "guestId"> & {
  guests: { id: string; name: string }[];
}) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [matches, setMatches] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [unmatchedOnly, setUnmatchedOnly] = useState(false);
  const load = useCallback(async () => setDocuments((await request("/id-collection")).documents), [request]);
  useEffect(() => { load().catch((e) => setError(e.message)); }, [load]);
  async function upload() {
    setBusy(true); setError("");
    let nextRevision = revision;
    try {
      for (const file of files) {
        if (file.size > 5 * 1024 * 1024) throw Error("Choose images of up to 5 MiB each.");
        const body = new FormData();
        body.append("file", file); body.append("revision", String(nextRevision));
        nextRevision = (await request("/id-collection", { method: "POST", body })).revision;
      }
      setFiles([]);
    } catch (e: any) { setError(e.message); }
    finally { await load().catch((e) => setError(e.message)); await refresh().catch((e) => setError(e.message)); setBusy(false); }
  }
  async function match(doc: Document) {
    if (!matches[doc.id] || busy) return;
    setBusy(true); setError("");
    try {
      await request(`/id-collection/${doc.id}/match`, { method: "POST", body: JSON.stringify({ guest_id: matches[doc.id], revision }) });
      await load(); await refresh();
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }
  const visible = documents.filter((d) => (!unmatchedOnly || !d.guest_id) &&
    `${d.label} ${guests.find((g) => g.id === d.guest_id)?.name || ""}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="guest-documents">
    <p>{documents.length} images · {documents.filter((d) => !d.guest_id).length} awaiting a guest match. Unmatched images do not create guests or room assignments.</p>
    {error && <div className="alert error" role="alert">{error}</div>}
    <label>Find an ID<input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name or collection label" /></label>
    <label className="checkbox-label"><input type="checkbox" checked={unmatchedOnly} onChange={(e) => setUnmatchedOnly(e.target.checked)} />Show only unmatched images</label>
    {canUpload && <div className="id-upload-controls">
      <label>Collect ID images<input type="file" multiple accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(e) => setFiles(Array.from(e.target.files || []))} /></label>
      <small>Use this collection when the matching guest is not yet known. JPG, PNG or WebP; up to 5 MiB each.</small>
      <button className="primary compact" type="button" disabled={busy || !files.length} onClick={upload}>{busy ? "Saving…" : "Upload to collection"}</button>
    </div>}
    <div className="id-collection-list">
      {visible.map((doc) => <article className="id-collection-row" key={doc.id}>
        <a href={`/api/planning/id-collection/${doc.id}/image`} target="_blank" rel="noopener noreferrer"><img loading="lazy" src={`/api/planning/id-collection/${doc.id}/image`} alt={doc.label} /></a>
        <div>
          <strong>{doc.label}</strong>
          <p>{doc.guest_id ? `Attached to ${guests.find((g) => g.id === doc.guest_id)?.name || "guest"}` : "Awaiting match — name and RSVP need review"}</p>
          <div className="id-pdf-actions"><a href={`/api/planning/id-collection/${doc.id}/document.pdf`} target="_blank" rel="noopener noreferrer">Open / print PDF</a><a href={`/api/planning/id-collection/${doc.id}/document.pdf?download=true`} download>Download PDF</a></div>
          {canUpload && !doc.guest_id && <div className="id-match-controls">
            <label>Matching guest<select value={matches[doc.id] || ""} disabled={busy} onChange={(e) => setMatches({ ...matches, [doc.id]: e.target.value })}><option value="">Choose the correct person</option>{guests.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></label>
            <button className="secondary compact" type="button" disabled={busy || !matches[doc.id]} onClick={() => match(doc)}>Attach to guest</button>
          </div>}
        </div>
      </article>)}
    </div>
    {!documents.length && <p>No ID images collected yet.</p>}
  </section>;
}
