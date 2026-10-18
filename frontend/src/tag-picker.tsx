import { useState } from "react";

const presets: Record<string, string> = {
  friends: "Friends · share with same gender",
  ground_floor: "Ground floor required",
  near_restaurant: "Near restaurant",
  main_hotel: "Wyndham only",
  second_hotel: "Second-hotel eligible",
  second_hotel_only: "Second hotel only",
  arrival_unconfirmed: "Arrival date needs confirmation",
  headcount_unconfirmed: "Complete headcount needs confirmation",
};
const privateMetadata = (tag: string) =>
  /^(slot_|source_list_|role_|relation_)/.test(tag);
export function TagPicker({
  value,
  known,
  onChange,
  allowFriends = true,
}: {
  value: string[];
  known: string[];
  allowFriends?: boolean;
  onChange: (tags: string[]) => void;
}) {
  const [search, setSearch] = useState("");
  const [newTag, setNewTag] = useState("");
  const [error, setError] = useState("");
  const choices = [
    ...new Set([...Object.keys(presets), ...known, ...value]),
  ].filter((t) => !privateMetadata(t) && (allowFriends || t !== "friends"));
  const label = (t: string) => presets[t] || t.replaceAll("_", " ");
  function toggle(tag: string, checked: boolean) {
    let next = value.filter((t) => t !== tag);
    if (checked) next.push(tag);
    if (checked && tag === "second_hotel_only")
      next = [...next.filter((t) => t !== "main_hotel"), "second_hotel"];
    if (checked && tag === "main_hotel")
      next = next.filter((t) => t !== "second_hotel_only");
    if (!checked && tag === "second_hotel")
      next = next.filter((t) => t !== "second_hotel_only");
    onChange([...new Set(next)]);
  }
  function add() {
    const tag = newTag.trim().toLowerCase();
    if (!tag || tag.length > 40 || !/^[\p{L}\p{N}_ -]+$/u.test(tag)) {
      setError("Use a short tag with letters, numbers, spaces, - or _.");
      return;
    }
    toggle(tag, true);
    setNewTag("");
    setError("");
  }
  return (
    <fieldset className="tag-picker">
      <legend>Tick the tags</legend>
      <label>
        Find a tag
        <input
          value={search}
          placeholder="Search available tags"
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      <div className="tag-choices">
        {choices
          .filter((t) => label(t).toLowerCase().includes(search.toLowerCase()))
          .map((tag) => (
            <label className="checkbox-label tag-choice" key={tag}>
              <input
                type="checkbox"
                checked={value.includes(tag)}
                onChange={(e) => toggle(tag, e.target.checked)}
              />
              {label(tag)}
            </label>
          ))}
      </div>
      <div className="add-tag-row">
        <label>
          New tag
          <input
            value={newTag}
            maxLength={40}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                add();
              }
            }}
          />
        </label>
        <button type="button" className="secondary compact" onClick={add}>
          Add tag
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
    </fieldset>
  );
}
