import { useEffect, useState, type FormEvent } from "react";

type Person = { side: "bride" | "groom"; name: string; relationship: string };
type Details = {
  revision: number;
  bride_name: string;
  groom_name: string;
  source_url: string;
  family: Person[];
};
export function WeddingDetailsPanel({
  owner,
  revision,
  request,
  action,
}: {
  owner: boolean;
  revision: number;
  request: (path: string) => Promise<any>;
  action: (path: string, body: any, method?: string) => Promise<any>;
}) {
  const [details, setDetails] = useState<Details | null>(null);
  const [draft, setDraft] = useState<Details | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    request("/wedding-details")
      .then(setDetails)
      .catch((e) => setError(e.message));
  }, [revision]);
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!draft) return;
    setSaving(true);
    const result = await action("/wedding-details", draft, "PUT");
    if (result) {
      setDraft(null);
      setDetails(await request("/wedding-details"));
    }
    setSaving(false);
  }
  return (
    <section className="settings-card wedding-context">
      <div className="section-heading">
        <div>
          <span className="eyebrow">THE WEDDING PARTY</span>
          <h2>
            {details?.bride_name || details?.groom_name
              ? `${details.bride_name} & ${details.groom_name}`
              : "Couple & family details"}
          </h2>
        </div>
        {owner && !draft && (
          <button
            className="secondary compact"
            onClick={() => details && setDraft(structuredClone(details))}
          >
            Edit wedding details
          </button>
        )}
      </div>
      <p>
        Family information from the invitation. This directory does not add
        overnight guests or change room counts.
      </p>
      {error && <p role="alert">{error}</p>}
      {draft ? (
        <form onSubmit={save} className="wedding-detail-form">
          {draft.revision !== revision && (
            <p className="alert warning">
              The plan changed while this form was open. Cancel and reopen to
              use the current version.
            </p>
          )}
          <div className="form-row">
            <label>
              Bride name
              <input
                maxLength={100}
                value={draft.bride_name}
                onChange={(e) =>
                  setDraft({ ...draft, bride_name: e.target.value })
                }
              />
            </label>
            <label>
              Groom name
              <input
                maxLength={100}
                value={draft.groom_name}
                onChange={(e) =>
                  setDraft({ ...draft, groom_name: e.target.value })
                }
              />
            </label>
          </div>
          <label>
            Invitation source
            <input
              type="url"
              placeholder="https://"
              maxLength={250}
              value={draft.source_url}
              onChange={(e) =>
                setDraft({ ...draft, source_url: e.target.value })
              }
            />
          </label>
          {draft.family.map((person, index) => (
            <fieldset key={index} className="family-detail-row">
              <legend>Family person {index + 1}</legend>
              <label>
                Side
                <select
                  value={person.side}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      family: draft.family.map((p, i) =>
                        i === index
                          ? { ...p, side: e.target.value as Person["side"] }
                          : p,
                      ),
                    })
                  }
                >
                  <option value="bride">Bride</option>
                  <option value="groom">Groom</option>
                </select>
              </label>
              <label>
                Name
                <input
                  required
                  maxLength={100}
                  value={person.name}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      family: draft.family.map((p, i) =>
                        i === index ? { ...p, name: e.target.value } : p,
                      ),
                    })
                  }
                />
              </label>
              <label>
                Relationship
                <input
                  required
                  maxLength={80}
                  value={person.relationship}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      family: draft.family.map((p, i) =>
                        i === index
                          ? { ...p, relationship: e.target.value }
                          : p,
                      ),
                    })
                  }
                />
              </label>
              <button
                type="button"
                className="text-button"
                onClick={() =>
                  setDraft({
                    ...draft,
                    family: draft.family.filter((_, i) => i !== index),
                  })
                }
              >
                Remove person {index + 1}
              </button>
            </fieldset>
          ))}
          <div className="planner-toolbar">
            <button
              type="button"
              className="secondary compact"
              disabled={draft.family.length >= 60}
              onClick={() =>
                setDraft({
                  ...draft,
                  family: [
                    ...draft.family,
                    { side: "bride", name: "", relationship: "" },
                  ],
                })
              }
            >
              Add family person
            </button>
            <button
              className="primary compact"
              disabled={saving || draft.revision !== revision}
            >
              Save wedding details
            </button>
            <button
              type="button"
              className="secondary compact"
              onClick={() => setDraft(null)}
            >
              Cancel details edit
            </button>
          </div>
        </form>
      ) : (
        <>
          {!!details?.family.length && (
            <div className="wedding-family-columns">
              {(["bride", "groom"] as const).map((side) => (
                <div key={side}>
                  <h3>{side === "bride" ? "Bride family" : "Groom family"}</h3>
                  <dl>
                    {details.family
                      .filter((p) => p.side === side)
                      .map((p) => (
                        <div key={p.name}>
                          <dt>{p.relationship}</dt>
                          <dd>{p.name}</dd>
                        </div>
                      ))}
                  </dl>
                </div>
              ))}
            </div>
          )}
          {details?.source_url && (
            <a
              className="text-button"
              href={details.source_url}
              target="_blank"
              rel="noreferrer"
            >
              View invitation source ↗
            </a>
          )}
        </>
      )}
    </section>
  );
}
