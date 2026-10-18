import { TagPicker } from "./tag-picker";
import { WeddingDetailsPanel } from "./wedding-details";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  applyNodeChanges,
  type Node,
  type ReactFlowInstance,
} from "@xyflow/react";
import {
  ArrowRight,
  Check,
  Download,
  LockKeyhole,
  MapPin,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Undo2,
  Redo2,
  Upload,
  UsersRound,
  X,
} from "lucide-react";
import "@xyflow/react/dist/style.css";
import "./planning.css";

type Viewer = {
  id: string;
  role: "owner" | "family" | "reception";
  side: "bride" | "groom" | null;
};
type Family = {
  id: string;
  label: string;
  side: "bride" | "groom";
  reserved_eligible: boolean;
  couple_children: boolean;
};
type Guest = {
  id: string;
  family_id: string;
  name: string | null;
  age: number | null;
  age_band?: "adult" | "child" | "unknown";
  group_label?: string;
  gender?: "male" | "female" | "unspecified";
  sharing_mode?: "family" | "friends";
  category: string;
  phone?: string | null;
  arrival: string | null;
  tags: string[];
  notes?: string;
  side: string;
  reserved_eligible: boolean;
  couple_children: boolean;
};
type Resource = {
  id: string;
  number: string | null;
  hotel_id: string;
  category: string;
  block: number | null;
  floor: number | null;
  adult_capacity: number;
  reserved: boolean;
  near_restaurant: boolean;
  x: number;
  y: number;
};
type Assignment = { guest_id: string; night: string; resource_id: string };
type Warning = {
  id: string;
  message: string;
  guest_ids?: string[];
  resource_ids?: string[];
  night?: string;
};
type Plan = {
  revision: number;
  families: Family[];
  guests: Guest[];
  resources: Resource[];
  assignments: Assignment[];
  locks: { resource_id: string; night: string }[];
  links?: any[];
  connections: any[];
  rules?: any[];
  reserved_count: number;
  reserve_pool: number;
  summary: Record<string, any>;
  conflicts?: { errors: Warning[]; warnings: Warning[] };
  can_undo?: boolean;
  can_redo?: boolean;
  presence: {
    guest_id: string;
    status: string;
    arrived_at?: string | null;
    departed_at?: string | null;
  }[];
};
type Preview = {
  token: string | null;
  revision: number;
  errors: any[];
  warnings: Warning[];
  summary?: Record<string, any>;
  families?: number;
  guests?: number;
  importing?: boolean;
  family_edit?: boolean;
  reason?: string;
  edited_guests?: Guest[];
  changes?: {
    guest_id: string;
    night: string;
    from: string | null;
    to: string | null;
  }[];
  estimate?: { known_subtotal_paise: number; unpriced: number };
};
type Props = {
  user: Viewer;
  csrf: string;
  page: string;
  onExpired: () => void;
};
const nights = ["2026-11-24", "2026-11-25"],
  days = [...nights, "2026-11-26"];
const money = (v: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(v / 100);
const dayName = (s: string) =>
  new Date(s + "T12:00:00").toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
const roomName = (r: Resource) =>
  r.number || `Unnumbered · ${r.id.replace("second-", "")}`;
const guestName = (g?: Guest) =>
  !g
    ? "Guest no longer listed"
    : g.name ||
      `${g.group_label || "Unnamed guest"} · ${g.age_band === "adult" ? "Adult" : g.age_band === "child" ? "Child" : "Guest"} ${g.tags.find((t) => t.startsWith("slot_"))?.slice(5) || g.id.slice(0, 4)}`;
const guestCategory = (g: Guest) =>
  g.category === "guest" && g.sharing_mode === "friends"
    ? `Friends · ${g.gender === "unspecified" || !g.gender ? "gender pending" : g.gender}`
    : g.category;
const occupied = (g: Guest, n: string) => !!g.arrival && g.arrival <= n;
const emptyMember = () => ({
  name: "",
  age: "",
  age_band: "unknown",
  gender: "unspecified",
  sharing_mode: "family",
  category: "guest",
  phone: "",
  arrival: nights[0],
  tags: "",
  notes: "",
});
function detailMessage(d: any) {
  return typeof d === "string"
    ? d
    : (d?.message || "Please check this change.") +
        (d?.errors?.length
          ? " " +
            d.errors
              .slice(0, 4)
              .map((e: any) => e.message)
              .join(" ")
          : "");
}

function Dialog({
  title,
  close,
  children,
  wide = false,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    document.body.classList.add("modal-open");
    const box = ref.current;
    (box?.querySelector("input,button,select") as HTMLElement)?.focus();
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab" && box) {
        const list = Array.from(
          box.querySelectorAll<HTMLElement>(
            "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
          ),
        );
        if (e.shiftKey && document.activeElement === list[0]) {
          e.preventDefault();
          list.at(-1)?.focus();
        } else if (!e.shiftKey && document.activeElement === list.at(-1)) {
          e.preventDefault();
          list[0]?.focus();
        }
      }
    };
    document.addEventListener("keydown", keys);
    return () => {
      document.removeEventListener("keydown", keys);
      document.body.classList.remove("modal-open");
      previous?.focus();
    };
  }, []);
  return (
    <div className="modal-backdrop planning-backdrop">
      <section
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={"modal planning-dialog " + (wide ? "wide" : "")}
      >
        <button
          className="icon-button modal-close"
          aria-label="Close dialog"
          onClick={close}
        >
          <X />
        </button>
        <span className="eyebrow">YOUR WEDDING PLAN</span>
        <h2>{title}</h2>
        {children}
      </section>
    </div>
  );
}

type RoomData = {
  resource: Resource;
  people: Guest[];
  locked: boolean;
  selected: boolean;
  allowed?: boolean;
  reason?: string;
  owner: boolean;
  topology?: boolean;
  choose: (r: Resource) => void;
  info: (r: Resource) => void;
};
function RoomNode({ data }: { data: RoomData }) {
  const r = data.resource,
    sides = new Set(data.people.map((p) => p.side)),
    side = sides.size > 1 ? "mixed" : data.people[0]?.side || "empty";
  return (
    <div
      className={`plan-room ${side} ${r.reserved ? "reserved" : ""} ${data.selected && data.allowed !== undefined ? (data.allowed ? "can-place" : "cannot-place") : ""}`}
      title={data.reason || undefined}
      role="button"
      data-room-id={r.id}
      tabIndex={0}
      aria-label={`${r.hotel_id === "staff" ? "Dormitory" : "Room"} ${roomName(r)}, ${data.people.length} assigned${r.reserved ? ", reserved for family" : ""}${data.locked ? ", locked" : ""}`}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          data.choose(r);
        }
      }}
      onClick={() => data.choose(r)}
      onDragOver={(e) => {
        if (data.owner) e.preventDefault();
      }}
      onDrop={(e) => {
        e.preventDefault();
        if (!data.owner) return;
        const payload = e.dataTransfer.getData("application/wedding-guests");
        if (payload) {
          const ids = payload.split(",");
          window.dispatchEvent(
            new CustomEvent("planner-drop", {
              detail: { ids, resource: r.id },
            }),
          );
        }
      }}
    >
      {data.topology && (
        <>
          <Handle
            type="target"
            position={Position.Left}
            isConnectable={false}
          />
          <Handle
            type="source"
            position={Position.Right}
            isConnectable={false}
          />
        </>
      )}
      <div className="plan-room-title">
        <b>{roomName(r)}</b>
        <span>
          {data.locked && <LockKeyhole size={15} />}
          <button
            className="node-info"
            aria-label={`Details for ${roomName(r)}`}
            onClick={(e) => {
              e.stopPropagation();
              data.info(r);
            }}
          >
            •••
          </button>
        </span>
      </div>
      <div className="room-meta">
        {r.category === "pending" ? "Category pending" : r.category} ·{" "}
        {r.floor === null
          ? "Floor unconfirmed"
          : r.floor === 0
            ? "Ground"
            : "First"}
        {r.block ? ` · B${r.block}` : ""}
      </div>
      {r.reserved && <span className="reservation-label">Family reserved</span>}
      <div className="room-people">
        {data.people.length ? (
          data.people.map((g) => (
            <span key={g.id}>
              {guestName(g)}
              {(g.age !== null ? g.age <= 10 : g.age_band === "child") && (
                <small>Child</small>
              )}
            </span>
          ))
        ) : (
          <span className="room-vacant">
            {data.owner
              ? "Drop here or tap to assign"
              : "No visible assignment"}
          </span>
        )}
      </div>
      <div className="room-capacity">
        <span>{data.people.length} people</span>
        <span>{r.adult_capacity} adult-counted max</span>
      </div>
      {data.selected && data.allowed !== undefined && (
        <div className="placement-hint">
          {data.allowed
            ? "✓ Eligible · review any warnings"
            : "⚠ Placement conflict"}
        </div>
      )}
    </div>
  );
}
const nodeTypes = { room: RoomNode as any };

export function PlanningWorkspace({ user, csrf, page, onExpired }: Props) {
  const owner = user.role === "owner";
  const [data, setData] = useState<Plan | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [night, setNight] = useState(nights[0]),
    [hotel, setHotel] = useState("wyndham"),
    [block, setBlock] = useState("all"),
    [floor, setFloor] = useState("all"),
    [search, setSearch] = useState(""),
    [side, setSide] = useState(user.role === "family" ? user.side! : "all");
  const [roomView, setRoomView] = useState("rooms");
  const [destinations, setDestinations] = useState<Record<string, any>>({});
  const [selection, setSelection] = useState<string[]>([]),
    [groupMode, setGroupMode] = useState(true),
    [mobilePanel, setMobilePanel] = useState("rooms"),
    [layoutMode, setLayoutMode] = useState(false),
    [swapFrom, setSwapFrom] = useState<Resource | null>(null);
  const [details, setDetails] = useState<Resource | null>(null),
    [familyDraft, setFamilyDraft] = useState<any>(null),
    [reserveDraft, setReserveDraft] = useState<string[] | null>(null),
    [preview, setPreview] = useState<Preview | null>(null),
    [acks, setAcks] = useState<string[]>([]);
  const [nodes, setNodes] = useState<Node[]>([]),
    [flow, setFlow] = useState<ReactFlowInstance | null>(null),
    [jobs, setJobs] = useState<any[]>([]),
    [bill, setBill] = useState<any>(null),
    [basis, setBasis] = useState("planned"),
    [rateDraft, setRateDraft] = useState<any>(null),
    [snapshots, setSnapshots] = useState<any[]>([]),
    [history, setHistory] = useState<any[]>([]);
  const [linkDraft, setLinkDraft] = useState<any>(null),
    [ruleDraft, setRuleDraft] = useState<any>(null),
    [connectionDraft, setConnectionDraft] = useState<any>(null);
  const [mealDay, setMealDay] = useState(days[0]),
    [mealKind, setMealKind] = useState("dinner"),
    [mealLocation, setMealLocation] = useState("wyndham"),
    [allMeals, setAllMeals] = useState<any[]>([]),
    [mealDraft, setMealDraft] = useState<Record<string, any>>({});
  const [functions, setFunctions] = useState<any>({ events: [], rows: [] }),
    [functionId, setFunctionId] = useState(""),
    [functionDraft, setFunctionDraft] = useState<Record<string, any>>({}),
    [eventDraft, setEventDraft] = useState({
      name: "",
      day: days[1],
      side: "",
      start_time: "",
      venue: "",
      source_url: "",
    });
  const [mealEditRevision, setMealEditRevision] = useState<number | null>(null),
    [functionEditRevision, setFunctionEditRevision] = useState<number | null>(
      null,
    );
  function changeMeals(value: React.SetStateAction<Record<string, any>>) {
    const next = typeof value === "function" ? value(mealDraft) : value;
    setMealDraft(next);
    setMealEditRevision(
      Object.keys(next).length
        ? (mealEditRevision ?? data?.revision ?? null)
        : null,
    );
  }
  function changeFunction(value: React.SetStateAction<Record<string, any>>) {
    const next = typeof value === "function" ? value(functionDraft) : value;
    setFunctionDraft(next);
    setFunctionEditRevision(
      Object.keys(next).length
        ? (functionEditRevision ?? data?.revision ?? null)
        : null,
    );
  }
  const upload = useRef<HTMLInputElement>(null),
    revisionRef = useRef(0);
  const pointerDrag = useRef<{
      ids: string[];
      x: number;
      y: number;
      moved: boolean;
    } | null>(null),
    dragFinished = useRef(0);
  function beginDrag(e: React.PointerEvent, ids: string[]) {
    if (!owner || e.pointerType !== "mouse" || e.button !== 0 || !ids.length)
      return;
    pointerDrag.current = { ids, x: e.clientX, y: e.clientY, moved: false };
  }
  useEffect(() => {
    const track = (e: PointerEvent) => {
      const drag = pointerDrag.current;
      if (
        drag &&
        !drag.moved &&
        Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 8
      ) {
        drag.moved = true;
        setSelection(drag.ids);
        setSwapFrom(null);
      }
    };
    const finish = (e: PointerEvent) => {
      const drag = pointerDrag.current;
      pointerDrag.current = null;
      if (!drag?.moved) return;
      const target = document
        .elementFromPoint(e.clientX, e.clientY)
        ?.closest("[data-room-id]");
      const id = target?.getAttribute("data-room-id");
      if (id) {
        dragFinished.current = Date.now();
        move(drag.ids, id);
      }
    };
    const cancel = () => {
      pointerDrag.current = null;
    };
    window.addEventListener("pointermove", track);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", cancel);
    return () => {
      window.removeEventListener("pointermove", track);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", cancel);
    };
  }, [data?.revision, night, owner]);
  const request = useCallback(
    async (path: string, options: RequestInit = {}) => {
      const multipart = options.body instanceof FormData;
      const response = await fetch("/api/planning" + path, {
        ...options,
        headers: {
          ...(multipart ? {} : { "Content-Type": "application/json" }),
          "X-CSRF-Token": csrf,
          ...options.headers,
        },
        credentials: "same-origin",
      });
      const body = await response.json();
      if (!response.ok) {
        if (response.status === 401) onExpired();
        throw Error(detailMessage(body.detail));
      }
      return body;
    },
    [csrf],
  );
  const refresh = useCallback(async () => {
    const d = await request("");
    revisionRef.current = d.revision;
    setData(d);
  }, [request]);
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
    const events = new EventSource("/api/planning/events");
    events.addEventListener("revision", (event) => {
      const v = JSON.parse((event as MessageEvent).data).revision;
      if (v !== revisionRef.current)
        refresh().catch((e) => setError(e.message));
    });
    events.addEventListener("expired", () => {
      events.close();
      onExpired();
    });
    const fallback = window.setInterval(() => refresh().catch(() => {}), 15000);
    return () => {
      events.close();
      window.clearInterval(fallback);
    };
  }, [refresh]);
  useEffect(() => {
    if (page !== "attendance" || !data) return;
    request("/functions")
      .then(setFunctions)
      .catch((e) => setError(e.message));
  }, [page, data?.revision]);
  useEffect(() => {
    if (!owner || !data) return;
    if (page === "billing" || page === "planner")
      request("/billing?basis=" + basis)
        .then(setBill)
        .catch((e) => setError(e.message));
    if (page === "billing") {
      request("/meals")
        .then((d) => setAllMeals(d.rows))
        .catch((e) => setError(e.message));
      request("/billing/snapshots")
        .then((d) => setSnapshots(d.snapshots))
        .catch(() => {});
    }
    if (page === "rules")
      request("/history")
        .then((d) => setHistory(d.items))
        .catch(() => {});
  }, [data?.revision, page, basis]);
  useEffect(() => {
    if (!owner || page !== "planner") return;
    const load = () =>
      request("/allocation")
        .then((d) => setJobs(d.runs))
        .catch(() => {});
    load();
    const timer = setInterval(load, 2500);
    return () => clearInterval(timer);
  }, [page, owner, request]);
  useEffect(() => {
    setDestinations({});
    if (!owner || !data || !selection.length) return;
    let stopped = false;
    request("/assignments/destinations", {
      method: "POST",
      body: JSON.stringify({
        revision: data.revision,
        guest_ids: selection,
        night,
      }),
    })
      .then((result) => {
        if (!stopped) setDestinations(result.choices);
      })
      .catch(() => {});
    return () => {
      stopped = true;
    };
  }, [selection, night, data?.revision]);
  useEffect(() => {
    setMealDraft({});
    setMealEditRevision(null);
  }, [mealDay, mealKind, mealLocation]);
  async function action(path: string, body: any, method = "POST") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await request(path, {
        method,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      await refresh();
      return result;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  function openPreview(result: Preview) {
    setPreview(result);
    setAcks([]);
  }
  async function move(ids: string[], destination: string | null) {
    if (!data || !owner || !ids.length) return;
    const result = await action("/assignments/preview", {
      revision: data.revision,
      moves: ids.map((id) => ({
        guest_id: id,
        night,
        resource_id: destination,
      })),
    });
    if (result) openPreview(result);
  }
  async function chooseRoom(r: Resource) {
    if (Date.now() - dragFinished.current < 250) return;
    if (layoutMode) {
      setDetails(r);
      return;
    }
    if (owner && swapFrom && data) {
      const moves = data.assignments
        .filter(
          (a) =>
            a.night === night && [swapFrom.id, r.id].includes(a.resource_id),
        )
        .map((a) => ({
          ...a,
          resource_id: a.resource_id === swapFrom.id ? r.id : swapFrom.id,
        }));
      setSwapFrom(null);
      if (moves.length) {
        const result = await action("/assignments/preview", {
          revision: data.revision,
          moves,
        });
        if (result) openPreview(result);
      }
      return;
    }
    if (owner && selection.length) move(selection, r.id);
    else setDetails(r);
  }
  useEffect(() => {
    const drop = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      move(detail.ids, detail.resource);
    };
    window.addEventListener("planner-drop", drop);
    return () => window.removeEventListener("planner-drop", drop);
  }, [data?.revision, night, owner]);
  const resourceList = useMemo(
    () =>
      data?.resources.filter(
        (r) =>
          r.hotel_id === hotel &&
          (hotel !== "wyndham" ||
            block === "all" ||
            String(r.block) === block) &&
          (floor === "all" || String(r.floor) === floor),
      ) || [],
    [data?.resources, hotel, block, floor],
  );
  useEffect(() => {
    if (!data) return;
    setNodes(
      resourceList.map((r) => ({
        id: r.id,
        type: "room",
        position: { x: r.x, y: r.y },
        draggable: layoutMode && owner,
        data: {
          resource: r,
          topology: true,
          people: data.guests.filter((g) =>
            data.assignments.some(
              (a) =>
                a.guest_id === g.id &&
                a.resource_id === r.id &&
                a.night === night,
            ),
          ),
          locked: data.locks.some(
            (l) => l.resource_id === r.id && l.night === night,
          ),
          selected: !!selection.length || !!swapFrom,
          allowed: destinations[r.id]?.allowed,
          reason: destinations[r.id]?.reason,
          owner,
          choose: chooseRoom,
          info: setDetails,
        },
      })),
    );
  }, [
    resourceList,
    data?.revision,
    night,
    layoutMode,
    selection,
    swapFrom,
    destinations,
  ]);
  useEffect(() => {
    if (flow)
      requestAnimationFrame(() =>
        flow.fitView({ padding: 0.15, maxZoom: 1.2 }),
      );
  }, [flow, hotel, block, floor]);
  const families =
    data?.families.filter(
      (f) =>
        (side === "all" || f.side === side) &&
        (!search ||
          f.label.toLowerCase().includes(search.toLowerCase()) ||
          data.guests.some(
            (g) =>
              g.family_id === f.id &&
              [g.name, g.phone].some((v) =>
                v?.toLowerCase().includes(search.toLowerCase()),
              ),
          )),
    ) || [];
  const filteredGuests =
    data?.guests.filter((g) => families.some((f) => f.id === g.family_id)) ||
    [];
  const selectedGuests =
    data?.guests.filter((g) => selection.includes(g.id)) || [];
  function selectGuests(ids: string[]) {
    setSelection(ids);
    setSwapFrom(null);
    setMobilePanel("rooms");
  }
  function editFamily(f?: Family) {
    if (!data) return;
    setError("");
    setFamilyDraft({
      revision: data.revision,
      id: f?.id,
      label: f?.label || "",
      side: f?.side || "bride",
      reserved_eligible: f?.reserved_eligible || false,
      couple_children: f?.couple_children || false,
      members: f
        ? data.guests
            .filter((g) => g.family_id === f.id)
            .map((g) => ({
              ...g,
              age: g.age === null ? "" : String(g.age),
              name: g.name || "",
              phone: g.phone || "",
              arrival: g.arrival || "",
              tags: g.tags.join(", "),
              notes: g.notes || "",
            }))
        : [emptyMember()],
    });
  }
  async function saveFamily(e: FormEvent) {
    e.preventDefault();
    const d = familyDraft;
    const payload = {
      revision: d.revision,
      label: d.label,
      side: d.side,
      reserved_eligible: d.reserved_eligible,
      couple_children: d.couple_children,
      members: d.members.map((g: any) => ({
        ...(g.id ? { id: g.id } : {}),
        name: g.name || null,
        age: g.age === "" ? null : Number(g.age),
        age_band:
          g.age === ""
            ? g.age_band || "unknown"
            : Number(g.age) > 10
              ? "adult"
              : "child",
        category: g.category,
        gender: g.gender || "unspecified",
        sharing_mode: g.sharing_mode || "family",
        phone: g.phone || null,
        arrival: g.arrival || null,
        tags: g.tags
          .split(",")
          .map((t: string) => t.trim())
          .filter(Boolean),
        notes: g.notes,
      })),
    };
    const result = await action(
      d.id ? "/families/" + d.id : "/families",
      payload,
      d.id ? "PUT" : "POST",
    );
    if (result?.family_edit) {
      openPreview(result);
    } else if (result) {
      setFamilyDraft(null);
      setNotice(
        "Guest slots saved. Names and ages complete the same people without duplicating them.",
      );
    }
  }
  async function confirmPreview() {
    if (!preview?.token) return;
    const result = await action(
      preview.importing
        ? "/import/apply"
        : preview.family_edit
          ? "/families/apply"
          : "/assignments/apply",
      { revision: preview.revision, token: preview.token, acknowledged: acks },
    );
    if (result) {
      if (preview.family_edit) setFamilyDraft(null);
      setPreview(null);
      setSelection([]);
      setNotice(
        preview.importing
          ? "Import applied."
          : "Plan saved. Other signed-in views update automatically.",
      );
    }
  }
  async function uploadFile(file: File) {
    if (!data) return;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const result = await request(
        "/import/preview?revision=" + data.revision,
        { method: "POST", body },
      );
      openPreview({ ...result, importing: true });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (upload.current) upload.current.value = "";
    }
  }
  async function runHistory(direction: string) {
    if (!data) return;
    const result = await action("/history", {
      revision: data.revision,
      direction,
    });
    if (result?.token) openPreview(result);
    else if (result)
      setNotice(
        direction === "undo"
          ? "Previous assignment restored."
          : "Assignment reapplied.",
      );
  }
  function personCard(g: Guest) {
    const assigned = data?.assignments.find(
      (a) => a.guest_id === g.id && a.night === night,
    );
    return (
      <button
        key={g.id}
        className={"guest-choice " + (selection.includes(g.id) ? "chosen" : "")}
        draggable={false}
        onPointerDown={(e) => occupied(g, night) && beginDrag(e, [g.id])}
        onClick={() => owner && occupied(g, night) && selectGuests([g.id])}
      >
        <span className={"side-dot " + g.side} />
        <span>
          <b>{guestName(g)}</b>
          <small>
            {g.age === null
              ? g.age_band && g.age_band !== "unknown"
                ? `${g.age_band} · exact age pending`
                : "Age or band needed"
              : g.age <= 10
                ? `Child · ${g.age}`
                : `Age ${g.age}`}{" "}
            · {g.arrival ? dayName(g.arrival) : "Event only"}
            {assigned ? " · Assigned" : ""}
          </small>
        </span>
      </button>
    );
  }
  if (!data)
    return (
      <div className="planning-loading">{error || "Opening your plan…"}</div>
    );
  const summary = data.summary[night];
  const currentJob = jobs[0];
  const currentMeals = Object.fromEntries(
    allMeals
      .filter(
        (m) =>
          m.day === mealDay &&
          m.meal === mealKind &&
          m.location === mealLocation,
      )
      .map((m) => [m.guest_id, m]),
  );
  const attendance = (g: Guest) =>
    mealDraft[g.id] ||
    currentMeals[g.id] || {
      guest_id: g.id,
      day: mealDay,
      meal: mealKind,
      location: mealLocation,
      planned: false,
      actual: null,
      inclusion: g.category === "guest" ? "unconfirmed" : "chargeable",
    };
  return (
    <div className="planning-workspace">
      <div className="page-heading">
        <div>
          <span className="eyebrow">EVERYONE, THOUGHTFULLY PLACED</span>
          <h1>
            {page === "guests"
              ? "Your guests"
              : page === "attendance"
                ? "Arrivals & functions"
                : page === "billing"
                  ? "Attendance & estimates"
                  : page === "rules"
                    ? "Rooms, rules & history"
                    : "The room plan"}
            <span className="heading-dot">.</span>
          </h1>
          <p>
            {page === "guests"
              ? "Add families or individuals. Complete details in the same guest slots."
              : page === "attendance"
                ? "Actual arrivals and departures, plus planned and attended functions. Meals are recorded separately for billing."
                : page === "billing"
                  ? "Known costs, confirmed inclusion and the items still to settle."
                  : page === "rules"
                    ? "Reservations and real room relationships guide every placement."
                    : "Drag a person or family to a room, or select them and tap a room."}
          </p>
        </div>
        <span className="live-label">
          <i />
          Live · Revision {data.revision}
        </span>
      </div>
      {error && (
        <div role="alert" className="alert error">
          {error}
        </div>
      )}
      {notice && (
        <div role="status" className="alert">
          {notice}
        </div>
      )}
      <div className="planner-toolbar">
        <label className="search-box">
          <Search size={16} />
          <input
            aria-label="Search guests or groups"
            placeholder="Find a guest or family…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="small-field">
          Side
          <select value={side} onChange={(e) => setSide(e.target.value)}>
            {user.role !== "family" && <option value="all">Both sides</option>}
            {(user.role !== "family" || user.side === "bride") && (
              <option value="bride">Bride</option>
            )}
            {(user.role !== "family" || user.side === "groom") && (
              <option value="groom">Groom</option>
            )}
          </select>
        </label>
        <a
          className="secondary compact"
          href="/api/planning/export.xlsx"
          download
        >
          <Download size={15} />
          Export Excel
        </a>
        {owner && (
          <>
            <button
              className="secondary compact"
              onClick={() => upload.current?.click()}
              disabled={busy}
            >
              <Upload size={15} />
              Import
            </button>
            <input
              ref={upload}
              className="sr-only"
              type="file"
              accept=".xlsx"
              aria-label="Import guest workbook"
              onChange={(e) =>
                e.target.files?.[0] && uploadFile(e.target.files[0])
              }
            />
            <button className="primary compact" onClick={() => editFamily()}>
              <Plus size={16} />
              Add guests
            </button>
          </>
        )}
      </div>
      {((page === "attendance" &&
        functionEditRevision !== null &&
        functionEditRevision !== data.revision) ||
        (page === "billing" &&
          mealEditRevision !== null &&
          mealEditRevision !== data.revision)) && (
        <div className="alert error" role="alert">
          The plan changed while you were editing attendance. Your unsaved
          entries are preserved, but cannot overwrite the newer revision.{" "}
          <button
            className="text-button"
            onClick={() => {
              changeMeals({});
              changeFunction({});
            }}
          >
            Discard drafts and use current records
          </button>
        </div>
      )}
      {page === "attendance" && (
        <div className="attendance-sections">
          <WeddingDetailsPanel
            owner={owner}
            revision={data.revision}
            request={request}
            action={action}
          />
          <section className="settings-card">
            <h2>Actual arrivals & departures</h2>
            <p>
              Arrival dates in the guest list are the accommodation plan. These
              records track what happened.
            </p>
            <div className="table-wrap">
              <table className="planning-table">
                <thead>
                  <tr>
                    <th>Guest</th>
                    <th>Planned arrival</th>
                    <th>Status</th>
                    <th>Recorded times</th>
                    {owner && <th>Record now</th>}
                  </tr>
                </thead>
                <tbody>
                  {filteredGuests.map((g) => {
                    const presence = data.presence.find(
                      (p) => p.guest_id === g.id,
                    );
                    return (
                      <tr key={g.id}>
                        <td>{guestName(g)}</td>
                        <td>
                          {g.arrival ? dayName(g.arrival) : "Non-resident"}
                        </td>
                        <td>
                          {presence?.status.replaceAll("_", " ") ||
                            "Not recorded"}
                        </td>
                        <td>
                          {presence?.arrived_at
                            ? new Date(presence.arrived_at).toLocaleString(
                                "en-IN",
                              )
                            : "—"}
                          {presence?.departed_at && (
                            <>
                              {" "}
                              →{" "}
                              {new Date(presence.departed_at).toLocaleString(
                                "en-IN",
                              )}
                            </>
                          )}
                        </td>
                        {owner && (
                          <td className="action-cell">
                            <button
                              className="secondary compact"
                              disabled={busy || !!presence?.arrived_at}
                              onClick={() =>
                                action(
                                  "/presence/" + g.id,
                                  {
                                    revision: data.revision,
                                    arrived_at: new Date().toISOString(),
                                    departed_at: null,
                                  },
                                  "PUT",
                                )
                              }
                            >
                              Arrived
                            </button>
                            <button
                              className="secondary compact"
                              disabled={
                                busy ||
                                !presence?.arrived_at ||
                                !!presence?.departed_at
                              }
                              onClick={() =>
                                action(
                                  "/presence/" + g.id,
                                  {
                                    revision: data.revision,
                                    arrived_at: presence?.arrived_at,
                                    departed_at: new Date().toISOString(),
                                  },
                                  "PUT",
                                )
                              }
                            >
                              Departed
                            </button>
                            {presence && (
                              <button
                                className="text-button"
                                disabled={busy}
                                onClick={() =>
                                  action(
                                    "/presence/" + g.id,
                                    {
                                      revision: data.revision,
                                      arrived_at: null,
                                      departed_at: null,
                                    },
                                    "PUT",
                                  )
                                }
                              >
                                Clear record
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!filteredGuests.length && (
              <p>Add guests to start recording arrivals.</p>
            )}
          </section>
          <section className="settings-card">
            <h2>Functions & attendance</h2>
            <p>
              Celebration times use Asia/Kolkata. Attendance and meals are
              recorded separately.
            </p>
            <div className="function-timeline">
              {functions.events.map((event: any) => (
                <article key={event.id}>
                  <span className="eyebrow">
                    {dayName(event.day)}
                    {event.start_time
                      ? ` · ${event.start_time}`
                      : " · Time pending"}
                  </span>
                  <h3>{event.name}</h3>
                  {event.venue && <p>{event.venue}</p>}
                  {event.source_url && (
                    <a href={event.source_url} target="_blank" rel="noreferrer">
                      Invitation source ↗
                    </a>
                  )}
                </article>
              ))}
            </div>
            {owner && (
              <form
                className="planner-toolbar"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const result = await action("/events", {
                    revision: data.revision,
                    ...eventDraft,
                    side: eventDraft.side || null,
                    start_time: eventDraft.start_time || null,
                  });
                  if (result) {
                    setFunctionId(result.id);
                    setEventDraft({ ...eventDraft, name: "" });
                  }
                }}
              >
                <label className="small-field">
                  Function name
                  <input
                    required
                    maxLength={100}
                    value={eventDraft.name}
                    onChange={(e) =>
                      setEventDraft({ ...eventDraft, name: e.target.value })
                    }
                  />
                </label>
                <label className="small-field">
                  Date
                  <select
                    value={eventDraft.day}
                    onChange={(e) =>
                      setEventDraft({ ...eventDraft, day: e.target.value })
                    }
                  >
                    {days.map((d) => (
                      <option key={d} value={d}>
                        {dayName(d)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="small-field">
                  Guests
                  <select
                    value={eventDraft.side}
                    onChange={(e) =>
                      setEventDraft({ ...eventDraft, side: e.target.value })
                    }
                  >
                    <option value="">Both sides</option>
                    <option value="bride">Bride side</option>
                    <option value="groom">Groom side</option>
                  </select>
                </label>
                <label className="small-field">
                  Time (Asia/Kolkata)
                  <input
                    type="time"
                    value={eventDraft.start_time}
                    onInput={(e) =>
                      setEventDraft({
                        ...eventDraft,
                        start_time: e.currentTarget.value,
                      })
                    }
                  />
                </label>
                <label className="small-field">
                  Venue
                  <input
                    maxLength={150}
                    value={eventDraft.venue}
                    onChange={(e) =>
                      setEventDraft({ ...eventDraft, venue: e.target.value })
                    }
                  />
                </label>
                <label className="small-field">
                  Source link
                  <input
                    type="url"
                    placeholder="https://"
                    maxLength={250}
                    value={eventDraft.source_url}
                    onChange={(e) =>
                      setEventDraft({
                        ...eventDraft,
                        source_url: e.target.value,
                      })
                    }
                  />
                </label>
                <button className="primary compact" disabled={busy}>
                  Add function
                </button>
              </form>
            )}
            <label className="small-field">
              Select function
              <select
                value={functionId}
                onChange={(e) => {
                  setFunctionId(e.target.value);
                  changeFunction({});
                }}
              >
                <option value="">Choose a function</option>
                {functions.events.map((event: any) => (
                  <option key={event.id} value={event.id}>
                    {event.name} · {dayName(event.day)}
                    {event.start_time ? ` · ${event.start_time}` : ""}
                  </option>
                ))}
              </select>
            </label>
            {functionId &&
              functions.events.some((e: any) => e.id === functionId) && (
                <>
                  <div className="table-wrap">
                    <table className="planning-table">
                      <thead>
                        <tr>
                          <th>Guest</th>
                          <th>Expected</th>
                          <th>Actual attendance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredGuests
                          .filter((g) => {
                            const event = functions.events.find(
                              (e: any) => e.id === functionId,
                            );
                            return !event.side || event.side === g.side;
                          })
                          .map((g) => {
                            const row = functionDraft[g.id] ||
                              functions.rows.find(
                                (r: any) =>
                                  r.event_id === functionId &&
                                  r.guest_id === g.id,
                              ) || {
                                event_id: functionId,
                                guest_id: g.id,
                                planned: false,
                                actual: null,
                              };
                            return (
                              <tr key={g.id}>
                                <td>{guestName(g)}</td>
                                <td>
                                  <input
                                    aria-label={"Expected " + guestName(g)}
                                    type="checkbox"
                                    disabled={!owner}
                                    checked={row.planned}
                                    onChange={(e) =>
                                      changeFunction({
                                        ...functionDraft,
                                        [g.id]: {
                                          ...row,
                                          planned: e.target.checked,
                                        },
                                      })
                                    }
                                  />
                                </td>
                                <td>
                                  <select
                                    aria-label={
                                      "Actual attendance " + guestName(g)
                                    }
                                    disabled={!owner}
                                    value={
                                      row.actual === null
                                        ? "unknown"
                                        : String(row.actual)
                                    }
                                    onChange={(e) =>
                                      changeFunction({
                                        ...functionDraft,
                                        [g.id]: {
                                          ...row,
                                          actual:
                                            e.target.value === "unknown"
                                              ? null
                                              : e.target.value === "true",
                                        },
                                      })
                                    }
                                  >
                                    <option value="unknown">
                                      Not recorded
                                    </option>
                                    <option value="true">Attended</option>
                                    <option value="false">
                                      Did not attend
                                    </option>
                                  </select>
                                </td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
                  {owner && (
                    <button
                      className="primary compact"
                      disabled={busy || !Object.keys(functionDraft).length}
                      onClick={async () => {
                        if (
                          await action(
                            "/functions/attendance",
                            {
                              revision: functionEditRevision ?? data.revision,
                              rows: Object.values(functionDraft),
                            },
                            "PUT",
                          )
                        )
                          changeFunction({});
                      }}
                    >
                      Save function attendance
                    </button>
                  )}
                </>
              )}
            {!functions.events.length && (
              <p>
                No functions recorded yet. Function attendance does not
                automatically add meal charges.
              </p>
            )}
          </section>
        </div>
      )}
      {page === "guests" && (
        <>
          <div className="guest-total">
            <b>{data.guests.length}</b> guest slots · {data.families.length}{" "}
            families/groups · {data.guests.filter((g) => g.age === null).length}{" "}
            ages to complete
            {owner && (
              <a href="/api/planning/export.xlsx?template=true" download>
                Download import template
              </a>
            )}
          </div>
          <div className="family-list">
            {families.map((f) => (
              <section className="family-panel" key={f.id}>
                <div className="family-heading">
                  <span className={"side-badge " + f.side}>
                    {f.side === "bride" ? "Bride" : "Groom"}
                  </span>
                  <h2>{f.label}</h2>
                  <b>
                    {data.guests.filter((g) => g.family_id === f.id).length}{" "}
                    people
                  </b>
                  {owner && (
                    <button
                      className="text-button"
                      onClick={() => editFamily(f)}
                    >
                      Edit details
                    </button>
                  )}
                </div>
                <div className="family-flags">
                  {f.reserved_eligible && <span>Family-room eligible</span>}
                  {f.couple_children && (
                    <span>Couple with children · Superior at Wyndham</span>
                  )}
                </div>
                <div className="guest-table-wrap">
                  <table className="guest-table">
                    <thead>
                      <tr>
                        <th>Guest</th>
                        <th>Age</th>
                        <th>Arrival</th>
                        <th>Category / tags</th>
                        {user.role !== "family" && <th>Contact</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {data.guests
                        .filter((g) => g.family_id === f.id)
                        .map((g) => (
                          <tr key={g.id}>
                            <td>
                              <b>{guestName(g)}</b>
                              {owner && g.notes && (
                                <small>Private note saved</small>
                              )}
                            </td>
                            <td>
                              {g.age ??
                                `${g.age_band || "unknown"} · age pending`}
                            </td>
                            <td>
                              {g.arrival ? dayName(g.arrival) : "Event only"}
                            </td>
                            <td>
                              {guestCategory(g)}
                              <small>{g.tags.join(", ") || "No tags"}</small>
                            </td>
                            {user.role !== "family" && (
                              <td>{g.phone || "—"}</td>
                            )}
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))}
            {!families.length && (
              <div className="planning-empty">
                <UsersRound />
                <h2>A place for your guest list.</h2>
                <p>
                  Add a family or one person. Names and ages can be completed
                  later.
                </p>
                {owner && (
                  <button
                    className="primary compact"
                    onClick={() => editFamily()}
                  >
                    Add the first guests
                  </button>
                )}
              </div>
            )}
          </div>
        </>
      )}
      {page === "planner" && (
        <>
          <div className="planner-controls">
            <label className="small-field">
              Night
              <select
                value={night}
                onChange={(e) => {
                  setNight(e.target.value);
                  setSelection([]);
                }}
              >
                {nights.map((n) => (
                  <option key={n} value={n}>
                    {dayName(n)} → {n === nights[0] ? "25" : "26"} Nov
                  </option>
                ))}
              </select>
            </label>
            <label className="small-field">
              Property
              <select
                value={hotel}
                onChange={(e) => {
                  setHotel(e.target.value);
                  setBlock("all");
                  setFloor("all");
                }}
              >
                <option value="wyndham">Wyndham Garden</option>
                <option value="second">Second hotel</option>
                <option value="staff">Staff dormitory</option>
              </select>
            </label>
            {hotel === "wyndham" && (
              <label className="small-field">
                Block
                <select
                  value={block}
                  onChange={(e) => setBlock(e.target.value)}
                >
                  <option value="all">All blocks</option>
                  {[1, 2, 3, 4, 5, 6].map((b) => (
                    <option key={b} value={b}>
                      Block {b}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {hotel !== "staff" && (
              <label className="small-field">
                Floor
                <select
                  value={floor}
                  onChange={(e) => setFloor(e.target.value)}
                >
                  <option value="all">All floors</option>
                  <option value="0">Ground</option>
                  <option value="1">First</option>
                </select>
              </label>
            )}
            {owner && (
              <>
                <button
                  className="secondary compact"
                  aria-label="Undo assignment"
                  disabled={busy || !data.can_undo}
                  onClick={() => runHistory("undo")}
                >
                  <Undo2 size={16} />
                </button>
                <button
                  className="secondary compact"
                  aria-label="Redo assignment"
                  disabled={busy || !data.can_redo}
                  onClick={() => runHistory("redo")}
                >
                  <Redo2 size={16} />
                </button>
                <button
                  className={
                    "secondary compact " +
                    (layoutMode ? "selected-control" : "")
                  }
                  onClick={() => {
                    setRoomView("topology");
                    setLayoutMode(!layoutMode);
                    setSelection([]);
                  }}
                >
                  <MapPin size={15} />
                  {layoutMode ? "Finish layout" : "Edit layout"}
                </button>
                <button
                  className="primary compact"
                  disabled={
                    busy ||
                    !!jobs.find((j) => ["queued", "running"].includes(j.status))
                  }
                  onClick={async () => {
                    const r = await action("/allocation", {
                      revision: data.revision,
                    });
                    if (r)
                      setNotice(
                        "Finding a proposal. Your current plan stays in place until you review and apply it.",
                      );
                  }}
                >
                  <Sparkles size={16} />
                  Suggest rooms
                </button>
              </>
            )}
          </div>
          {owner && data.reserved_count !== 4 && (
            <div className="alert">
              Four Premium rooms are held unused as a reserve pool across both
              nights. Choose their numbers later in Rooms & rules.
            </div>
          )}
          {data.guests.some(
            (g) =>
              g.tags.includes("arrival_unconfirmed") ||
              g.tags.includes("headcount_unconfirmed"),
          ) && (
            <div className="alert">
              Source details pending: some arrivals use 24 Nov as a draft and
              blank child counts still need confirmation. The roster includes
              only listed people; final attendance may change.
            </div>
          )}
          {summary.unconfirmed_ages > 0 && (
            <div className="alert">
              Provisional plan: {summary.unconfirmed_ages} exact ages are
              unconfirmed for this night. Supplied adult/child counts guide
              placement and estimates. Check who is 50+ or needs ground floor
              before finalising.
            </div>
          )}
          <div className="room-view-controls">
            <button
              className={
                roomView === "rooms" ? "primary compact" : "secondary compact"
              }
              onClick={() => {
                setRoomView("rooms");
                setLayoutMode(false);
              }}
            >
              All rooms
            </button>
            <button
              className={
                roomView === "topology"
                  ? "primary compact"
                  : "secondary compact"
              }
              onClick={() => setRoomView("topology")}
            >
              Topology
            </button>
            <span>
              Showing {resourceList.length} of{" "}
              {data.resources.filter((r) => r.hotel_id === hotel).length}{" "}
              {hotel === "staff" ? "beds" : "rooms"} · scroll for the full list
            </span>
          </div>
          {owner && currentJob && (
            <div className="job-panel">
              <div>
                <b>
                  Automatic proposal ·{" "}
                  {currentJob.status === "completed"
                    ? currentJob.result?.solver_status
                    : currentJob.status}
                </b>
                <p>
                  {["queued", "running"].includes(currentJob.status)
                    ? "The worker is considering family groups, capacities, eligibility and locks."
                    : currentJob.status === "applied"
                      ? "This automatic proposal has been applied to the plan."
                      : currentJob.status === "stale"
                        ? "The plan changed. Run a fresh proposal."
                        : currentJob.result?.assignments
                          ? `${currentJob.result.assigned_count} person-nights placed · ${currentJob.result.unassigned?.length || 0} person-nights unassigned`
                          : (currentJob.result?.diagnostics || []).join(" ")}
                </p>
              </div>
              {currentJob.status === "completed" &&
                currentJob.result?.assignments && (
                  <button
                    className="secondary compact"
                    disabled={busy}
                    onClick={async () => {
                      const result = await action(
                        "/allocation/" + currentJob.id + "/preview",
                        { revision: data.revision },
                      );
                      if (result) openPreview(result);
                    }}
                  >
                    Review proposal
                    <ArrowRight size={15} />
                  </button>
                )}
              {currentJob.result?.unassigned?.length > 0 && (
                <details>
                  <summary>See who remains unassigned</summary>
                  {currentJob.result.unassigned.map((u: any) => (
                    <p key={u.guest_id + u.night}>
                      {guestName(data.guests.find((g) => g.id === u.guest_id))}{" "}
                      · {dayName(u.night)}: {u.reasons.join(" ")}
                    </p>
                  ))}
                </details>
              )}
            </div>
          )}
          <div className="mobile-planner-tabs">
            {["guests", "rooms", "summary"].map((p) => (
              <button
                key={p}
                className={mobilePanel === p ? "active" : ""}
                onClick={() => setMobilePanel(p)}
              >
                {p}
              </button>
            ))}
          </div>
          {owner && (
            <div className="selection-banner">
              <span>
                {swapFrom
                  ? `Swap ${roomName(swapFrom)} with another room.`
                  : selection.length
                    ? `${selection.length} selected: ${selectedGuests.map(guestName).join(", ")}. Tap or drop on a room.`
                    : "Select or drag a guest or family to begin a placement."}
              </span>
              <button
                onClick={() => {
                  setSelection([]);
                  setSwapFrom(null);
                }}
                className="text-button"
                disabled={!selection.length && !swapFrom}
              >
                Cancel
              </button>
              {selection.length > 0 && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => move(selection, null)}
                >
                  Unassign selected
                </button>
              )}
            </div>
          )}
          <div className={"planner-grid show-" + mobilePanel}>
            <section className="guest-drawer">
              <div className="drawer-title">
                <h2>People to place</h2>
                <span>{summary.unassigned} unassigned</span>
              </div>
              <div className="segmented">
                <button
                  className={groupMode ? "active" : ""}
                  onClick={() => setGroupMode(true)}
                >
                  Families
                </button>
                <button
                  className={!groupMode ? "active" : ""}
                  onClick={() => setGroupMode(false)}
                >
                  Individuals
                </button>
              </div>
              <div className="guest-scroll">
                {groupMode
                  ? families.map((f) => {
                      const members = data.guests.filter(
                        (g) => g.family_id === f.id && occupied(g, night),
                      );
                      if (!members.length) return null;
                      const chosen = members.every((g) =>
                        selection.includes(g.id),
                      );
                      return (
                        <button
                          key={f.id}
                          className={
                            "guest-choice group-choice " +
                            (chosen ? "chosen" : "")
                          }
                          draggable={false}
                          onPointerDown={(e) =>
                            beginDrag(
                              e,
                              members.map((g) => g.id),
                            )
                          }
                          onClick={() =>
                            owner && selectGuests(members.map((g) => g.id))
                          }
                        >
                          <span className={"side-dot " + f.side} />
                          <span>
                            <b>{f.label}</b>
                            <small>
                              {members.length} people ·{" "}
                              {
                                members.filter(
                                  (g) =>
                                    !data.assignments.some(
                                      (a) =>
                                        a.guest_id === g.id &&
                                        a.night === night,
                                    ),
                                ).length
                              }{" "}
                              unassigned
                            </small>
                            {members.some((g) => g.age === null) && (
                              <em>Age details needed</em>
                            )}
                          </span>
                        </button>
                      );
                    })
                  : filteredGuests
                      .filter((g) => occupied(g, night))
                      .map(personCard)}
                {!data.guests.length && (
                  <p className="drawer-help">
                    Add guests first, then place individuals or families here.
                  </p>
                )}
              </div>
              <p className="drawer-help">
                On a phone, select a person or family, then tap a room. Staff
                use separate dormitory beds.
              </p>
            </section>
            <section className="topology-panel">
              <div className="canvas-caption">
                <b>
                  {layoutMode
                    ? "Move the room cards to save a schematic layout"
                    : roomView === "rooms"
                      ? "All rooms"
                      : "Room topology"}
                </b>
                <span>
                  Schematic · Corridor proximity uses confirmed links only
                </span>
              </div>
              {roomView === "rooms" ? (
                <div
                  className="flow-canvas all-room-grid"
                  role="region"
                  aria-label="All rooms"
                >
                  <>
                    {nodes.map((node) => (
                      <RoomNode
                        key={node.id}
                        data={{ ...(node.data as RoomData), topology: false }}
                      />
                    ))}
                  </>
                </div>
              ) : (
                <div className="flow-canvas">
                  <ReactFlow
                    nodes={nodes}
                    onNodeClick={() => {}}
                    edges={data.connections
                      .filter(
                        (c) =>
                          resourceList.some((r) => r.id === c.a) &&
                          resourceList.some((r) => r.id === c.b),
                      )
                      .map((c) => ({
                        id: c.a + "-" + c.b,
                        source: c.a,
                        target: c.b,
                        label: c.kind,
                        type: "straight",
                        style: { stroke: "#af8b57" },
                      }))}
                    nodeTypes={nodeTypes}
                    onNodesChange={(changes) =>
                      setNodes((current) => applyNodeChanges(changes, current))
                    }
                    onNodeDragStop={async (_, node) => {
                      if (layoutMode && owner)
                        await action(
                          "/layout",
                          {
                            revision: data.revision,
                            positions: [
                              {
                                resource_id: node.id,
                                x: Math.max(0, node.position.x),
                                y: Math.max(0, node.position.y),
                              },
                            ],
                          },
                          "PUT",
                        );
                    }}
                    onInit={setFlow}
                    fitView
                    minZoom={0.1}
                    maxZoom={2}
                    nodesConnectable={false}
                    nodesDraggable={layoutMode && owner}
                    elementsSelectable={false}
                  >
                    <Background gap={24} color="#d9dfd4" />
                    <Controls showInteractive={false} />
                  </ReactFlow>
                </div>
              )}
              <div className="canvas-legend">
                <span>
                  <i className="side-dot bride" />
                  Bride
                </span>
                <span>
                  <i className="side-dot groom" />
                  Groom
                </span>
                <span>
                  <i className="side-dot mixed" />
                  Mixed
                </span>
                <span>
                  <LockKeyhole size={12} />
                  Family reserved / locked
                </span>
              </div>
            </section>
            <aside className="live-summary">
              <span className="eyebrow">THE NIGHT AT A GLANCE</span>
              <h2>{dayName(night)}</h2>
              {[
                ["Resident people", summary.residents],
                ["Assigned", summary.assigned],
                ["Unassigned", summary.unassigned],
                ["Rooms used", summary.used_rooms],
                ["Wyndham used / 44", summary.properties.wyndham.used],
                [
                  "Wyndham rooms empty",
                  summary.properties.wyndham.empty ?? "Usage hidden",
                ],
                ["Second hotel used / 6", summary.properties.second.used],
                [
                  "Rooms empty",
                  summary.free_rooms === null
                    ? "Other-side usage hidden"
                    : summary.free_rooms,
                ],
                ["Family rooms held", data.reserved_count || data.reserve_pool],
                [
                  "Wyndham general rooms left",
                  owner
                    ? Math.max(
                        0,
                        summary.properties.wyndham.empty -
                          (data.reserve_pool ||
                            data.resources.filter(
                              (r) =>
                                r.reserved &&
                                !data.assignments.some(
                                  (a) =>
                                    a.night === night && a.resource_id === r.id,
                                ),
                            ).length),
                      )
                    : "Usage hidden",
                ],
                ["Unnamed reserve pool", data.reserve_pool],
                ["Exact ages pending", summary.unconfirmed_ages],
                ["Staff beds used", summary.staff_beds_used],
                ["Extra bedding", summary.extra_bedding],
              ].map(([k, v]) => (
                <div className="live-summary-row" key={String(k)}>
                  <span>{k}</span>
                  <b>{v}</b>
                </div>
              ))}
              {Object.entries(summary.side_rooms).map(([s, v]) => (
                <div key={s} className="live-summary-row">
                  <span className={"side-text " + s}>
                    {s === "bride" ? "Bride" : "Groom"} rooms
                  </span>
                  <b>{String(v)}</b>
                </div>
              ))}
              {owner && bill && (
                <div className="summary-cost">
                  <small>Known estimate · all dates</small>
                  <b>{money(bill.known_subtotal_paise)}</b>
                  <p>
                    {bill.unpriced.length} unresolved items · provisional
                    pricing
                  </p>
                  {bill.nights[night].excess > 0 && (
                    <strong className="overage">
                      ⚠ {bill.nights[night].excess} over Wyndham allowance ·{" "}
                      {money(bill.nights[night].excess_paise)}
                    </strong>
                  )}
                </div>
              )}
              {owner &&
                data.conflicts &&
                (data.conflicts.errors.length > 0 ||
                  data.conflicts.warnings.length > 0) && (
                  <details className="conflict-list">
                    <summary>
                      {data.conflicts.errors.length} conflicts ·{" "}
                      {data.conflicts.warnings.length} warnings
                    </summary>
                    {[...data.conflicts.errors, ...data.conflicts.warnings].map(
                      (w) => (
                        <p key={w.id}>{w.message}</p>
                      ),
                    )}
                  </details>
                )}
            </aside>
          </div>
        </>
      )}
      {page === "rules" && owner && (
        <div className="settings-grid">
          <section className="settings-card">
            <h2>Four rooms for family</h2>
            <p>
              Four Premium rooms stay unused as a reserve pool until you select
              their exact numbers. Named family rooms remain blocked from
              general guests.
            </p>
            <b>
              {data.reserved_count
                ? `${data.reserved_count} named rooms selected`
                : "4-room unnamed reserve pool active"}
            </b>
            {data.reserved_count > 0 && (
              <button
                className="text-button"
                onClick={() =>
                  action(
                    "/reservations",
                    { revision: data.revision, room_ids: [] },
                    "PUT",
                  )
                }
              >
                Use unnamed reserve pool instead
              </button>
            )}
            <div className="reservation-chips">
              {data.resources
                .filter((r) => r.reserved)
                .map((r) => (
                  <span key={r.id}>{roomName(r)}</span>
                ))}
            </div>
            <button
              className="secondary compact"
              onClick={() =>
                setReserveDraft(
                  data.resources.filter((r) => r.reserved).map((r) => r.id),
                )
              }
            >
              Choose reserved rooms
            </button>
          </section>
          <section className="settings-card">
            <h2>Sharing & placement links</h2>
            <p>
              Mark compatible guests, mandatory sharing, exclusions and
              nearby-room requests.
            </p>
            <button
              className="secondary compact"
              onClick={() =>
                setLinkDraft({
                  revision: data.revision,
                  a: "",
                  b: "",
                  kind: "may_share",
                  severity: "hard",
                })
              }
            >
              <Plus size={14} />
              Add relationship
            </button>
            <div className="settings-items">
              {data.links?.map((l) => (
                <div key={l.id}>
                  <span>
                    {guestName(data.guests.find((g) => g.id === l.a)!)} ↔{" "}
                    {guestName(data.guests.find((g) => g.id === l.b)!)}
                    <small>
                      {l.kind.replaceAll("_", " ")} ·{" "}
                      {l.severity === "hard" ? "Mandatory" : "Warning"}
                    </small>
                  </span>
                  <button
                    className="text-button"
                    onClick={() =>
                      action(
                        "/links/" + l.id + "?revision=" + data.revision,
                        undefined,
                        "DELETE",
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </section>
          <section className="settings-card">
            <h2>Conditional placement rules</h2>
            <p>
              Limit rooms by side/tag, cap room usage, or keep sides apart. No
              equal-side split is assumed.
            </p>
            <button
              className="secondary compact"
              onClick={() =>
                setRuleDraft({
                  revision: data.revision,
                  name: "",
                  kind: "allowed_resources",
                  severity: "hard",
                  side: "",
                  tag: "",
                  resource_ids: [],
                  maximum: 20,
                  scope: "room",
                })
              }
            >
              <Plus size={14} />
              Add rule
            </button>
            <div className="settings-items">
              {data.rules?.map((r) => (
                <div key={r.id}>
                  <span>
                    {r.name}
                    <small>
                      {r.kind.replaceAll("_", " ")} ·{" "}
                      {r.severity === "hard" ? "Mandatory" : "Warning"}
                    </small>
                  </span>
                  <button
                    className="text-button"
                    onClick={() =>
                      action(
                        "/rules/" + r.id + "?revision=" + data.revision,
                        undefined,
                        "DELETE",
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </section>
          <section className="settings-card">
            <h2>Verified corridor connections</h2>
            <p>
              Drawing room cards close together does not establish adjacency.
              Record only neighbours or opposite rooms you know.
            </p>
            <button
              className="secondary compact"
              onClick={() =>
                setConnectionDraft({
                  revision: data.revision,
                  a: "",
                  b: "",
                  kind: "neighbour",
                  confirmed: false,
                })
              }
            >
              <Plus size={14} />
              Confirm a connection
            </button>
            <div className="settings-items">
              {data.connections.map((c) => (
                <div key={c.a + c.b}>
                  <span>
                    {roomName(data.resources.find((r) => r.id === c.a)!)} ↔{" "}
                    {roomName(data.resources.find((r) => r.id === c.b)!)}
                    <small>{c.kind}</small>
                  </span>
                  <button
                    className="text-button"
                    onClick={() =>
                      action(
                        `/connections?a=${encodeURIComponent(c.a)}&b=${encodeURIComponent(c.b)}&revision=${data.revision}`,
                        undefined,
                        "DELETE",
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </section>
          <section className="settings-card history-card">
            <h2>Change history</h2>
            <p>
              Owner actions are recorded. Assignment undo/redo is available from
              the planner.
            </p>
            {history.map((h) => (
              <div className="history-row" key={h.id}>
                <span>
                  {h.action.replaceAll(".", " · ").replaceAll("_", " ")}
                </span>
                <small>{new Date(h.created_at).toLocaleString("en-IN")}</small>
              </div>
            ))}
          </section>
        </div>
      )}
      {page === "billing" && owner && bill && (
        <>
          <div className="billing-top">
            <div className="estimate-total">
              <span className="eyebrow">KNOWN PRICED SUBTOTAL</span>
              <h2>{money(bill.known_subtotal_paise)}</h2>
              <p>
                {bill.unpriced.length} unpriced/unresolved items. This is a
                provisional planning estimate.
              </p>
            </div>
            <div className="billing-actions">
              <label className="small-field">
                Attendance basis
                <select
                  value={basis}
                  onChange={(e) => setBasis(e.target.value)}
                >
                  <option value="planned">Planned</option>
                  <option value="actual">Actual recorded</option>
                </select>
              </label>
              <button
                className="secondary compact"
                onClick={() =>
                  setRateDraft({
                    revision: data.revision,
                    ...bill.policy,
                    guest_meals: bill.settings.guest_meals,
                    second_extra_paise: bill.settings.second_extra_paise,
                    charge_days: bill.charge_days,
                  })
                }
              >
                <Settings2 size={15} />
                Rates & hotel days
              </button>
              <button
                className="secondary compact"
                disabled={busy}
                onClick={async () => {
                  const r = await action("/billing/snapshots", {
                    revision: data.revision,
                    basis,
                  });
                  if (r) {
                    setNotice(
                      "Estimate snapshot saved with its rates and revision.",
                    );
                    request("/billing/snapshots").then((d) =>
                      setSnapshots(d.snapshots),
                    );
                  }
                }}
              >
                <Save size={15} />
                Save estimate
              </button>
            </div>
          </div>
          <div className="night-cost-grid">
            {nights.map((n) => (
              <div className="settings-card" key={n}>
                <h2>{dayName(n)} · Wyndham</h2>
                <div className="live-summary-row">
                  <span>Actual resident heads</span>
                  <b>{bill.nights[n].wyndham_heads}</b>
                </div>
                <div className="live-summary-row">
                  <span>Chargeable adults / allowance</span>
                  <b>
                    {bill.nights[n].chargeable} /{" "}
                    {bill.policy.wyndham_allowance}
                  </b>
                </div>
                <div className="live-summary-row">
                  <span>Excess residents</span>
                  <b>{bill.nights[n].excess}</b>
                </div>
                <strong>{money(bill.nights[n].excess_paise)}</strong>
              </div>
            ))}
          </div>
          {bill.unpriced.length > 0 && (
            <details className="settings-card unpriced-card" open>
              <summary>
                <b>{bill.unpriced.length} items still to settle</b>
              </summary>
              {bill.unpriced.map((u: any, i: number) => (
                <p key={i}>
                  {u.day && <b>{dayName(u.day)} · </b>}
                  {u.reason}
                  {u.quantity ? ` (${u.quantity})` : ""}
                </p>
              ))}
            </details>
          )}
          <section className="settings-card attendance-card">
            <div className="section-heading">
              <div>
                <h2>Meals & attendance</h2>
                <p>
                  Record each meal once. Mark package-covered food Included;
                  keep uncertain coverage Unconfirmed.
                </p>
              </div>
            </div>
            <div className="planner-controls">
              <label className="small-field">
                Date
                <select
                  value={mealDay}
                  onChange={(e) => setMealDay(e.target.value)}
                >
                  {days.map((d) => (
                    <option key={d} value={d}>
                      {dayName(d)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="small-field">
                Meal
                <select
                  value={mealKind}
                  onChange={(e) => setMealKind(e.target.value)}
                >
                  {["breakfast", "lunch", "dinner"].map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </label>
              <label className="small-field">
                Location
                <select
                  value={mealLocation}
                  onChange={(e) => setMealLocation(e.target.value)}
                >
                  <option value="wyndham">Wyndham</option>
                  <option value="second">Second hotel</option>
                  <option value="external">Other / external</option>
                </select>
              </label>
              <button
                className="secondary compact"
                onClick={() =>
                  changeMeals(
                    Object.fromEntries(
                      filteredGuests.map((g) => [
                        g.id,
                        { ...attendance(g), planned: true },
                      ]),
                    ),
                  )
                }
              >
                Plan for all shown
              </button>
              <button
                className="primary compact"
                disabled={busy || !Object.keys(mealDraft).length}
                onClick={async () => {
                  const r = await action(
                    "/meals",
                    {
                      revision: mealEditRevision ?? data.revision,
                      rows: Object.values(mealDraft),
                    },
                    "PUT",
                  );
                  if (r) {
                    setNotice("Meal attendance saved.");
                    request("/meals").then((d) => setAllMeals(d.rows));
                    changeMeals({});
                  }
                }}
              >
                Save meal changes
              </button>
            </div>
            <div className="guest-table-wrap">
              <table className="meal-table">
                <thead>
                  <tr>
                    <th>Guest</th>
                    <th>Planned</th>
                    <th>Actual</th>
                    <th>Meal coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredGuests.map((g) => {
                    const m = attendance(g);
                    const change = (key: string, value: any) =>
                      changeMeals((current) => ({
                        ...current,
                        [g.id]: { ...m, [key]: value },
                      }));
                    return (
                      <tr key={g.id}>
                        <td>
                          <b>{guestName(g)}</b>
                          <small>{guestCategory(g)}</small>
                        </td>
                        <td>
                          <input
                            aria-label={`Planned meal for ${guestName(g)}`}
                            type="checkbox"
                            checked={m.planned}
                            onChange={(e) =>
                              change("planned", e.target.checked)
                            }
                          />
                        </td>
                        <td>
                          <select
                            aria-label={`Actual attendance for ${guestName(g)}`}
                            value={
                              m.actual === null
                                ? "unknown"
                                : m.actual
                                  ? "yes"
                                  : "no"
                            }
                            onChange={(e) =>
                              change(
                                "actual",
                                e.target.value === "unknown"
                                  ? null
                                  : e.target.value === "yes",
                              )
                            }
                          >
                            <option value="unknown">Not recorded</option>
                            <option value="yes">Attended</option>
                            <option value="no">Did not attend</option>
                          </select>
                        </td>
                        <td>
                          <select
                            aria-label={`Meal coverage for ${guestName(g)}`}
                            value={m.inclusion}
                            onChange={(e) =>
                              change("inclusion", e.target.value)
                            }
                          >
                            <option value="unconfirmed">Unconfirmed</option>
                            <option value="included">
                              Included in package
                            </option>
                            <option value="chargeable">
                              Charge separately
                            </option>
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
          <details className="settings-card">
            <summary>
              <b>Cost lines & assumptions</b>
            </summary>
            {bill.lines.map((l: any, i: number) => (
              <div className="cost-line" key={i}>
                <span>
                  {l.day && dayName(l.day)} · {l.kind.replaceAll("_", " ")} ·{" "}
                  {l.quantity} × {money(l.rate_paise)}
                </span>
                <b>{money(l.amount_paise)}</b>
              </div>
            ))}
            {bill.assumptions.map((a: string) => (
              <p className="assumption" key={a}>
                {a}
              </p>
            ))}
          </details>
          <section className="settings-card">
            <h2>Saved estimates</h2>
            <p>
              Saved snapshots keep the amounts and rates from that revision.
            </p>
            {snapshots.map((s) => (
              <div className="cost-line" key={s.id}>
                <span>
                  {new Date(s.created_at).toLocaleString("en-IN")} · revision{" "}
                  {s.revision} · {s.data.basis}
                </span>
                <b>{money(s.data.known_subtotal_paise)}</b>
              </div>
            ))}
          </section>
        </>
      )}
      {familyDraft && !preview?.family_edit && (
        <Dialog
          title={familyDraft.id ? "Edit family / group" : "Add guests"}
          close={() => setFamilyDraft(null)}
          wide
        >
          <form onSubmit={saveFamily}>
            {error && <div className="alert error">{error}</div>}
            <div className="form-row">
              <label>
                Family or group name
                <input
                  required
                  maxLength={100}
                  value={familyDraft.label}
                  onChange={(e) =>
                    setFamilyDraft({ ...familyDraft, label: e.target.value })
                  }
                />
              </label>
              <label>
                Side
                <select
                  value={familyDraft.side}
                  onChange={(e) =>
                    setFamilyDraft({ ...familyDraft, side: e.target.value })
                  }
                >
                  <option value="bride">Bride</option>
                  <option value="groom">Groom</option>
                </select>
              </label>
            </div>
            <div className="family-options">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={familyDraft.reserved_eligible}
                  onChange={(e) =>
                    setFamilyDraft({
                      ...familyDraft,
                      reserved_eligible: e.target.checked,
                    })
                  }
                />
                Eligible for reserved family rooms
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={familyDraft.couple_children}
                  onChange={(e) =>
                    setFamilyDraft({
                      ...familyDraft,
                      couple_children: e.target.checked,
                    })
                  }
                />
                Couple with children · Superior at Wyndham
              </label>
            </div>
            <p className="form-help">
              {familyDraft.members.length} guest slots. Blank names are allowed;
              enter exact ages or an adult/child band for provisional placement.
              Add one slot for each person.
            </p>
            <div className="member-cards">
              {familyDraft.members.map((g: any, i: number) => {
                const edit = (key: string, value: any) =>
                  setFamilyDraft((d: any) => ({
                    ...d,
                    members: d.members.map((m: any, j: number) =>
                      j === i ? { ...m, [key]: value } : m,
                    ),
                  }));
                return (
                  <fieldset key={g.id || i}>
                    <legend>
                      Guest {i + 1}
                      {g.id ? " · existing slot" : ""}
                    </legend>
                    <div className="form-row">
                      <label>
                        Name
                        <input
                          maxLength={100}
                          value={g.name}
                          onChange={(e) => edit("name", e.target.value)}
                          placeholder="Complete later if unknown"
                        />
                      </label>
                      <label>
                        Age
                        <input
                          type="number"
                          min={0}
                          max={120}
                          step={1}
                          value={g.age}
                          onChange={(e) => edit("age", e.target.value)}
                          placeholder="Unknown"
                        />
                      </label>
                      <label>
                        Adult / child count
                        <select
                          value={g.age_band || "unknown"}
                          onChange={(e) => edit("age_band", e.target.value)}
                          disabled={g.age !== ""}
                        >
                          <option value="unknown">Unknown</option>
                          <option value="adult">Adult (above 10)</option>
                          <option value="child">Child (10 or below)</option>
                        </select>
                      </label>
                    </div>
                    <div className="form-row">
                      <label>
                        Category
                        <select
                          value={
                            g.category === "guest" &&
                            g.sharing_mode === "friends"
                              ? "friends"
                              : g.category
                          }
                          onChange={(e) => {
                            edit(
                              "category",
                              e.target.value === "friends"
                                ? "guest"
                                : e.target.value,
                            );
                            edit(
                              "sharing_mode",
                              e.target.value === "friends"
                                ? "friends"
                                : "family",
                            );
                            edit(
                              "tags",
                              g.tags
                                .split(",")
                                .map((t: string) => t.trim())
                                .filter((t: string) => t !== "friends")
                                .join(", "),
                            );
                          }}
                        >
                          {[
                            "guest",
                            "friends",
                            "driver",
                            "staff",
                            "vendor",
                          ].map((c) => (
                            <option key={c} value={c}>
                              {c === "guest"
                                ? "Guest / family"
                                : c === "friends"
                                  ? "Friends"
                                  : c}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Male / female
                        <select
                          value={g.gender || "unspecified"}
                          onChange={(e) => edit("gender", e.target.value)}
                        >
                          <option value="unspecified">Not specified yet</option>
                          <option value="male">Male</option>
                          <option value="female">Female</option>
                        </select>
                      </label>
                      <label>
                        Arrival
                        <select
                          value={g.arrival}
                          onChange={(e) => edit("arrival", e.target.value)}
                        >
                          <option value="">Non-resident / event only</option>
                          {nights.map((n) => (
                            <option key={n} value={n}>
                              {dayName(n)} · 2 PM
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <label>
                      Contact number
                      <input
                        maxLength={40}
                        value={g.phone}
                        onChange={(e) => edit("phone", e.target.value)}
                        inputMode="tel"
                      />
                    </label>
                    <TagPicker
                      allowFriends={g.category === "guest"}
                      value={[
                        ...g.tags
                          .split(",")
                          .map((t: string) => t.trim())
                          .filter((t: string) => t && t !== "friends"),
                        ...(g.sharing_mode === "friends" ? ["friends"] : []),
                      ]}
                      known={
                        [
                          ...new Set(
                            data.guests
                              .flatMap((p) => p.tags)
                              .concat(
                                data.rules?.map((r) => r.tag).filter(Boolean) ||
                                  [],
                              ),
                          ),
                        ] as string[]
                      }
                      onChange={(tags) => {
                        edit(
                          "tags",
                          tags.filter((t) => t !== "friends").join(", "),
                        );
                        edit(
                          "sharing_mode",
                          tags.includes("friends") && g.category === "guest"
                            ? "friends"
                            : "family",
                        );
                      }}
                    />
                    {g.sharing_mode === "friends" && (
                      <p className="form-help">
                        Automatic sharing uses the same specified gender and
                        side. Not specified guests keep a separate room. Couples
                        and linked children stay together.
                      </p>
                    )}
                    <label>
                      Private owner note
                      <textarea
                        maxLength={2000}
                        value={g.notes}
                        onChange={(e) => edit("notes", e.target.value)}
                      />
                    </label>
                    {!g.id && familyDraft.members.length > 1 && (
                      <button
                        type="button"
                        className="text-button"
                        onClick={() =>
                          setFamilyDraft({
                            ...familyDraft,
                            members: familyDraft.members.filter(
                              (_: any, j: number) => j !== i,
                            ),
                          })
                        }
                      >
                        Remove new slot
                      </button>
                    )}
                  </fieldset>
                );
              })}
            </div>
            <div className="dialog-actions">
              <button
                type="button"
                className="secondary compact"
                disabled={familyDraft.members.length >= 80}
                onClick={() =>
                  setFamilyDraft({
                    ...familyDraft,
                    members: [...familyDraft.members, emptyMember()],
                  })
                }
              >
                <Plus size={14} />
                Add guest slot
              </button>
              <button className="primary compact" disabled={busy}>
                Save {familyDraft.members.length} guests
                <Check size={15} />
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {reserveDraft && (
        <Dialog
          title="Reserve four Premium rooms"
          close={() => setReserveDraft(null)}
        >
          <p className="form-help">
            {reserveDraft.length} selected. Reservations apply to both nights.
          </p>
          <div className="room-checkbox-grid">
            {data.resources
              .filter(
                (r) => r.hotel_id === "wyndham" && r.category === "premium",
              )
              .map((r) => (
                <label key={r.id}>
                  <input
                    type="checkbox"
                    checked={reserveDraft.includes(r.id)}
                    onChange={(e) =>
                      setReserveDraft(
                        e.target.checked
                          ? [...reserveDraft, r.id]
                          : reserveDraft.filter((id) => id !== r.id),
                      )
                    }
                  />
                  {roomName(r)}
                  <small>
                    Block {r.block} · {r.floor === 0 ? "Ground" : "First"}
                  </small>
                </label>
              ))}
          </div>
          {error && <div className="alert error">{error}</div>}
          <button
            className="primary compact"
            disabled={busy || reserveDraft.length !== 4}
            onClick={async () => {
              const r = await action(
                "/reservations",
                { revision: data.revision, room_ids: reserveDraft },
                "PUT",
              );
              if (r) setReserveDraft(null);
            }}
          >
            Save four reservations
          </button>
        </Dialog>
      )}
      {preview && (
        <Dialog
          title={
            preview.importing
              ? "Review guest import"
              : preview.family_edit
                ? "Review guest details & room changes"
                : "Review assignment change"
          }
          close={() => setPreview(null)}
        >
          <p className="form-help">
            {preview.importing
              ? `${preview.guests} guest rows in ${preview.families} families/groups. Nothing is saved until you apply.`
              : "Your current plan stays unchanged until you apply this exact preview."}
          </p>
          {preview.reason && <p className="alert">{preview.reason}</p>}
          {preview.family_edit && (
            <div className="edited-details">
              {preview.edited_guests?.map((g) => (
                <p key={g.id}>
                  <b>{guestName(g)}</b> · Age {g.age ?? "pending"}
                </p>
              ))}
            </div>
          )}
          {preview.summary &&
            nights.map((n) => (
              <div className="cost-line" key={n}>
                <span>{dayName(n)}</span>
                <b>
                  {preview.summary![n].assigned} assigned ·{" "}
                  {preview.summary![n].unassigned} unassigned
                </b>
              </div>
            ))}
          {preview.errors.map((e: any, i: number) => (
            <div className="alert error" key={i}>
              {e.row ? `Row ${e.row}: ` : ""}
              {e.message}
            </div>
          ))}
          {preview.changes && (
            <div className="table-wrap">
              <table className="planning-table">
                <thead>
                  <tr>
                    <th>Guest</th>
                    <th>Night</th>
                    <th>From</th>
                    <th>To</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.changes.map((c) => (
                    <tr key={c.guest_id + c.night}>
                      <td>
                        {guestName(
                          preview.edited_guests?.find(
                            (g) => g.id === c.guest_id,
                          ) || data.guests.find((g) => g.id === c.guest_id),
                        )}
                      </td>
                      <td>{dayName(c.night)}</td>
                      <td>
                        {c.from
                          ? roomName(
                              data.resources.find((r) => r.id === c.from)!,
                            )
                          : "Unassigned"}
                      </td>
                      <td>
                        {c.to
                          ? roomName(data.resources.find((r) => r.id === c.to)!)
                          : "Unassigned"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {preview.estimate && (
            <p className="form-help">
              After this change: known estimate{" "}
              {money(preview.estimate.known_subtotal_paise)} ·{" "}
              {preview.estimate.unpriced} unresolved pricing items. Provisional.
            </p>
          )}
          {preview.warnings.map((w) => (
            <label className="warning-review" key={w.id}>
              <input
                type="checkbox"
                checked={acks.includes(w.id)}
                onChange={(e) =>
                  setAcks(
                    e.target.checked
                      ? [...acks, w.id]
                      : acks.filter((id) => id !== w.id),
                  )
                }
              />
              <span>
                <b>⚠ {w.night && dayName(w.night)}</b>
                {w.message}
                {w.guest_ids?.length ? (
                  <small>
                    {w.guest_ids
                      .map((id) =>
                        guestName(data.guests.find((g) => g.id === id)),
                      )
                      .join(", ")}
                  </small>
                ) : null}
                {w.resource_ids?.length ? (
                  <small>
                    Room/bed:{" "}
                    {w.resource_ids
                      .map((id) => {
                        const r = data.resources.find((r) => r.id === id);
                        return r ? roomName(r) : id;
                      })
                      .join(", ")}
                  </small>
                ) : null}
              </span>
            </label>
          ))}
          {error && <div className="alert error">{error}</div>}
          <button
            className="primary"
            disabled={
              busy ||
              !preview.token ||
              preview.errors.length > 0 ||
              acks.length !== preview.warnings.length
            }
            onClick={confirmPreview}
          >
            Apply reviewed change
            <Check size={16} />
          </button>
        </Dialog>
      )}
      {details && (
        <Dialog title={roomName(details)} close={() => setDetails(null)}>
          <p className="form-help">
            {details.hotel_id} · {details.category} ·{" "}
            {details.floor === null
              ? "Floor unconfirmed"
              : details.floor === 0
                ? "Ground floor"
                : "First floor"}{" "}
            · {details.adult_capacity} adult-counted capacity
          </p>
          {data.guests
            .filter((g) =>
              data.assignments.some(
                (a) =>
                  a.guest_id === g.id &&
                  a.resource_id === details.id &&
                  a.night === night,
              ),
            )
            .map((g) => (
              <p className="room-person-detail" key={g.id}>
                {guestName(g)} ·{" "}
                {g.age === null ? "Unknown age" : g.age + " years"}
              </p>
            ))}
          {owner && (
            <>
              <div className="dialog-actions">
                <button
                  className="secondary compact"
                  onClick={async () => {
                    await action(
                      "/locks",
                      {
                        revision: data.revision,
                        resource_id: details.id,
                        night,
                        locked: !data.locks.some(
                          (l) =>
                            l.resource_id === details.id && l.night === night,
                        ),
                      },
                      "PUT",
                    );
                    setDetails(null);
                  }}
                >
                  <LockKeyhole size={14} />
                  {data.locks.some(
                    (l) => l.resource_id === details.id && l.night === night,
                  )
                    ? "Unlock"
                    : "Lock"}{" "}
                  this night
                </button>
                <button
                  className="secondary compact"
                  onClick={() => {
                    setSwapFrom(details);
                    setSelection([]);
                    setDetails(null);
                  }}
                >
                  Swap occupants
                </button>
                <button
                  className="text-button"
                  onClick={() => {
                    move(
                      data.assignments
                        .filter(
                          (a) =>
                            a.resource_id === details.id && a.night === night,
                        )
                        .map((a) => a.guest_id),
                      null,
                    );
                    setDetails(null);
                  }}
                >
                  Unassign occupants
                </button>
              </div>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const form = new FormData(e.currentTarget);
                  const r = await action(
                    "/rooms/" + details.id,
                    {
                      revision: data.revision,
                      number: form.get("number") || null,
                      near_restaurant: form.get("restaurant") === "on",
                    },
                    "PUT",
                  );
                  if (r) setDetails(null);
                }}
              >
                {details.hotel_id === "second" && (
                  <label>
                    Confirmed room number
                    <input
                      name="number"
                      maxLength={16}
                      defaultValue={details.number || ""}
                    />
                  </label>
                )}
                <label className="checkbox-label">
                  <input
                    name="restaurant"
                    type="checkbox"
                    defaultChecked={details.near_restaurant}
                  />
                  Restaurant proximity confirmed for this room
                </label>
                <button className="secondary compact" disabled={busy}>
                  Save room details
                </button>
              </form>
            </>
          )}
          {error && <div className="alert error">{error}</div>}
        </Dialog>
      )}
      {linkDraft && (
        <Dialog title="Guest relationship" close={() => setLinkDraft(null)}>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const r = await action("/links", linkDraft);
              if (r) setLinkDraft(null);
            }}
          >
            <GuestSelect
              title="First guest"
              guests={data.guests}
              value={linkDraft.a}
              change={(v) => setLinkDraft({ ...linkDraft, a: v })}
            />
            <GuestSelect
              title="Second guest"
              guests={data.guests}
              value={linkDraft.b}
              change={(v) => setLinkDraft({ ...linkDraft, b: v })}
            />
            <label>
              Relationship
              <select
                value={linkDraft.kind}
                onChange={(e) =>
                  setLinkDraft({ ...linkDraft, kind: e.target.value })
                }
              >
                {[
                  ["may_share", "Explicitly compatible to share"],
                  ["must_share", "Must share a room"],
                  ["cannot_share", "Must not share"],
                  ["nearby", "Neighbouring or opposite rooms"],
                  ["same_building", "Same building / block"],
                ].map(([v, t]) => (
                  <option key={v} value={v}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            {linkDraft.kind !== "may_share" && (
              <label>
                Strength
                <select
                  value={linkDraft.severity}
                  onChange={(e) =>
                    setLinkDraft({ ...linkDraft, severity: e.target.value })
                  }
                >
                  <option value="hard">Mandatory · cannot override</option>
                  <option value="warning">
                    Warning · owner review required
                  </option>
                </select>
              </label>
            )}
            {error && <div className="alert error">{error}</div>}
            <button
              className="primary compact"
              disabled={busy || !linkDraft.a || !linkDraft.b}
            >
              Save relationship
            </button>
          </form>
        </Dialog>
      )}
      {connectionDraft && (
        <Dialog
          title="Confirm room connection"
          close={() => setConnectionDraft(null)}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const r = await action("/connections", connectionDraft);
              if (r) setConnectionDraft(null);
            }}
          >
            {["a", "b"].map((key, i) => (
              <label key={key}>
                {i === 0 ? "First" : "Second"} room
                <select
                  required
                  value={connectionDraft[key]}
                  onChange={(e) =>
                    setConnectionDraft({
                      ...connectionDraft,
                      [key]: e.target.value,
                    })
                  }
                >
                  <option value="">Choose a room</option>
                  {data.resources.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.hotel_id} · {roomName(r)}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <label>
              Connection
              <select
                value={connectionDraft.kind}
                onChange={(e) =>
                  setConnectionDraft({
                    ...connectionDraft,
                    kind: e.target.value,
                  })
                }
              >
                <option value="neighbour">Direct neighbours</option>
                <option value="opposite">Opposite across the corridor</option>
              </select>
            </label>
            <label className="checkbox-label">
              <input
                required
                type="checkbox"
                checked={connectionDraft.confirmed}
                onChange={(e) =>
                  setConnectionDraft({
                    ...connectionDraft,
                    confirmed: e.target.checked,
                  })
                }
              />
              I know this physical relationship is correct
            </label>
            {error && <div className="alert error">{error}</div>}
            <button className="primary compact" disabled={busy}>
              Save confirmed connection
            </button>
          </form>
        </Dialog>
      )}
      {ruleDraft && (
        <Dialog
          title="Conditional placement rule"
          close={() => setRuleDraft(null)}
          wide
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const r = await action("/rules", {
                ...ruleDraft,
                side: ruleDraft.side || null,
                tag: ruleDraft.tag || null,
                maximum:
                  ruleDraft.kind === "side_quota"
                    ? Number(ruleDraft.maximum)
                    : null,
              });
              if (r) setRuleDraft(null);
            }}
          >
            <label>
              Rule name
              <input
                required
                maxLength={100}
                value={ruleDraft.name}
                onChange={(e) =>
                  setRuleDraft({ ...ruleDraft, name: e.target.value })
                }
              />
            </label>
            <div className="form-row">
              <label>
                Rule type
                <select
                  value={ruleDraft.kind}
                  onChange={(e) =>
                    setRuleDraft({
                      ...ruleDraft,
                      kind: e.target.value,
                      side:
                        e.target.value === "separate_sides"
                          ? ""
                          : ruleDraft.side,
                    })
                  }
                >
                  <option value="allowed_resources">
                    Only these rooms / beds
                  </option>
                  <option value="side_quota">Maximum rooms for a side</option>
                  <option value="separate_sides">
                    Keep bride and groom sides apart
                  </option>
                </select>
              </label>
              <label>
                Strength
                <select
                  value={ruleDraft.severity}
                  onChange={(e) =>
                    setRuleDraft({ ...ruleDraft, severity: e.target.value })
                  }
                >
                  <option value="hard">Mandatory</option>
                  <option value="warning">Warning with owner review</option>
                </select>
              </label>
            </div>
            <div className="form-row">
              {ruleDraft.kind !== "separate_sides" && (
                <label>
                  Applies to side
                  <select
                    value={ruleDraft.side}
                    onChange={(e) =>
                      setRuleDraft({ ...ruleDraft, side: e.target.value })
                    }
                  >
                    <option value="">Both sides</option>
                    <option value="bride">Bride</option>
                    <option value="groom">Groom</option>
                  </select>
                </label>
              )}
              <label>
                Only guests with tag (optional)
                <input
                  maxLength={40}
                  value={ruleDraft.tag}
                  onChange={(e) =>
                    setRuleDraft({ ...ruleDraft, tag: e.target.value })
                  }
                />
              </label>
            </div>
            {ruleDraft.kind === "allowed_resources" && (
              <div className="room-checkbox-grid">
                {data.resources.map((r) => (
                  <label key={r.id}>
                    <input
                      type="checkbox"
                      checked={ruleDraft.resource_ids.includes(r.id)}
                      onChange={(e) =>
                        setRuleDraft({
                          ...ruleDraft,
                          resource_ids: e.target.checked
                            ? [...ruleDraft.resource_ids, r.id]
                            : ruleDraft.resource_ids.filter(
                                (id: string) => id !== r.id,
                              ),
                        })
                      }
                    />
                    {roomName(r)}
                    <small>{r.hotel_id}</small>
                  </label>
                ))}
              </div>
            )}
            {ruleDraft.kind === "side_quota" && (
              <label>
                Maximum occupied rooms
                <input
                  type="number"
                  min={0}
                  max={50}
                  required
                  value={ruleDraft.maximum}
                  onChange={(e) =>
                    setRuleDraft({ ...ruleDraft, maximum: e.target.value })
                  }
                />
              </label>
            )}
            {ruleDraft.kind === "separate_sides" && (
              <label>
                Separate by
                <select
                  value={ruleDraft.scope}
                  onChange={(e) =>
                    setRuleDraft({ ...ruleDraft, scope: e.target.value })
                  }
                >
                  <option value="room">Room</option>
                  <option value="block">Building / block</option>
                  <option value="floor">Floor within a block</option>
                </select>
              </label>
            )}
            {error && <div className="alert error">{error}</div>}
            <button className="primary compact" disabled={busy}>
              Save conditional rule
            </button>
          </form>
        </Dialog>
      )}
      {rateDraft && (
        <RateDialog
          draft={rateDraft}
          close={() => setRateDraft(null)}
          save={async (payload) => {
            const r = await action("/billing/rates", payload, "PUT");
            if (r) setRateDraft(null);
          }}
          busy={busy}
          error={error}
        />
      )}
    </div>
  );
}

function GuestSelect({
  title,
  guests,
  value,
  change,
}: {
  title: string;
  guests: Guest[];
  value: string;
  change: (v: string) => void;
}) {
  return (
    <label>
      {title}
      <select required value={value} onChange={(e) => change(e.target.value)}>
        <option value="">Choose a guest</option>
        {guests.map((g) => (
          <option key={g.id} value={g.id}>
            {guestName(g)} · {g.side}
          </option>
        ))}
      </select>
    </label>
  );
}
function RateDialog({
  draft,
  close,
  save,
  busy,
  error,
}: {
  draft: any;
  close: () => void;
  save: (p: any) => void;
  busy: boolean;
  error: string;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const out: Record<string, string> = {};
    for (const k of [
      "wyndham_excess_paise",
      "staff_meal_paise",
      "second_hotel_day_paise",
      "second_extra_paise",
    ])
      out[k] = draft[k] === null ? "" : (draft[k] / 100).toFixed(2);
    for (const m of ["breakfast", "lunch", "dinner"])
      for (const a of ["adult", "child"]) {
        const k = m + "_" + a;
        out[k] =
          draft.guest_meals[k] == null
            ? ""
            : (draft.guest_meals[k] / 100).toFixed(2);
      }
    return out;
  });
  const [allowance, setAllowance] = useState(String(draft.wyndham_allowance)),
    [included, setIncluded] = useState(String(draft.second_hotel_included)),
    [chargeDays, setChargeDays] = useState<string[]>(draft.charge_days);
  function paise(value: string) {
    if (value === "") return null;
    const [a, b = ""] = value.split(".");
    return Number(a) * 100 + Number(b.padEnd(2, "0"));
  }
  function rate(key: string, label: string, required = false) {
    return (
      <label key={key}>
        {label} · ₹
        <input
          required={required}
          type="number"
          min="0"
          max="1000000"
          step="0.01"
          placeholder="Unpriced"
          value={values[key]}
          onChange={(e) => setValues({ ...values, [key]: e.target.value })}
        />
      </label>
    );
  }
  return (
    <Dialog title="Rates & second-hotel days" close={close} wide>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const p: any = {
            revision: draft.revision,
            wyndham_allowance: Number(allowance),
            second_hotel_included: Number(included),
            guest_meals: {},
            charge_days: chargeDays,
          };
          for (const k of [
            "wyndham_excess_paise",
            "staff_meal_paise",
            "second_hotel_day_paise",
            "second_extra_paise",
          ])
            p[k] = paise(values[k]);
          for (const m of ["breakfast", "lunch", "dinner"])
            for (const a of ["adult", "child"])
              p.guest_meals[m + "_" + a] = paise(values[m + "_" + a]);
          save(p);
        }}
      >
        <p className="form-help">
          Blank means unpriced, not free. Second-hotel amounts remain
          provisional. Enter the billable days you intend to estimate.
        </p>
        <div className="rate-grid">
          <label>
            Wyndham included adults per night
            <input
              required
              type="number"
              min={0}
              max={1000}
              value={allowance}
              onChange={(e) => setAllowance(e.target.value)}
            />
          </label>
          {rate(
            "wyndham_excess_paise",
            "Excess Wyndham resident / night",
            true,
          )}
          {rate("staff_meal_paise", "Driver / staff / vendor meal", true)}
          {rate(
            "second_hotel_day_paise",
            "All six second-hotel rooms / day",
            true,
          )}
          <label>
            Second-hotel included guests
            <input
              required
              type="number"
              min={0}
              max={1000}
              value={included}
              onChange={(e) => setIncluded(e.target.value)}
            />
          </label>
          {rate("second_extra_paise", "Second-hotel extra person / night")}
        </div>
        <h3>Non-resident Wyndham guest meals</h3>
        <div className="rate-grid">
          {["breakfast", "lunch", "dinner"].flatMap((m) =>
            ["adult", "child"].map((a) => rate(m + "_" + a, `${m} · ${a}`)),
          )}
        </div>
        <h3>Provisional second-hotel billable days</h3>
        <div className="family-options">
          {days.map((d) => (
            <label className="checkbox-label" key={d}>
              <input
                type="checkbox"
                checked={chargeDays.includes(d)}
                onChange={(e) =>
                  setChargeDays(
                    e.target.checked
                      ? [...chargeDays, d]
                      : chargeDays.filter((v) => v !== d),
                  )
                }
              />
              {dayName(d)}
            </label>
          ))}
        </div>
        {error && <div className="alert error">{error}</div>}
        <button className="primary compact" disabled={busy}>
          Save estimate rates
        </button>
      </form>
    </Dialog>
  );
}
