import React, { useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  BedDouble,
  Building2,
  CalendarDays,
  ChevronRight,
  Eye,
  Flower2,
  LayoutGrid,
  LockKeyhole,
  LogOut,
  Plus,
  ShieldCheck,
  Moon,
  Sun,
  UsersRound,
  X,
} from "lucide-react";
import "./style.css";
import { PlanningWorkspace } from "./planning";
import "./wedding-theme.css";
import "./aadi-theme.css";

type Theme = "light" | "dark";
const initialTheme: Theme = (() => {
  try {
    const saved = localStorage.getItem("planner-theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch { /* Theme storage is optional. */ }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
})();
document.documentElement.dataset.theme = initialTheme;

function ThemeToggle({ theme, onToggle }: { theme: Theme; onToggle: () => void }) {
  return (
    <button type="button" className="theme-toggle" onClick={onToggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

type User = {
  id: string;
  username: string;
  display_name: string;
  role: "owner" | "editor" | "family" | "reception";
  side: "bride" | "groom" | null;
  active: boolean;
  version: number;
};
type Room = {
  id: string;
  hotel_id: string;
  number: string | null;
  category: string;
  block: number | null;
  floor: number | null;
  bed_type: string;
  adult_capacity: number;
};
type Inventory = {
  hotels: { id: string; name: string; kind: string }[];
  rooms: Room[];
  staff_beds: { id: number }[];
  family_reserve_pending: number;
  cost_policy?: {
    wyndham_allowance: number;
    wyndham_excess_paise: number;
    staff_meal_paise: number;
    second_hotel_day_paise: number;
    second_hotel_included: number;
  };
};
type Account = {
  username: string;
  display_name: string;
  password: string;
  role: "editor" | "family" | "reception";
  side: "bride" | "groom";
  active: boolean;
  version: number;
};
const blankAccount = (): Account => ({
  username: "",
  display_name: "",
  password: "",
  role: "family",
  side: "bride",
  active: true,
  version: 1,
});
const rupees = (paise: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(paise / 100);

function App() {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#0d1423" : "#f4f7ff");
    try { localStorage.setItem("planner-theme", theme); } catch { /* Theme storage is optional. */ }
  }, [theme]);
  const toggleTheme = () => setTheme((current) => current === "dark" ? "light" : "dark");
  const [user, setUser] = useState<User | null>(null),
    [csrf, setCsrf] = useState(""),
    [loading, setLoading] = useState(true),
    [setup, setSetup] = useState(false);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [page, setPage] = useState("planner"),
    [inventory, setInventory] = useState<Inventory | null>(null);
  const [hotel, setHotel] = useState("wyndham"),
    [floor, setFloor] = useState("all"),
    [selected, setSelected] = useState<Room | null>(null),
    [rules, setRules] = useState(false);
  const [accounts, setAccounts] = useState<User[]>([]),
    [editing, setEditing] = useState<User | null | undefined>(undefined),
    [account, setAccount] = useState<Account>(blankAccount),
    [busy, setBusy] = useState(false);

  async function api(path: string, options: RequestInit = {}) {
    const response = await fetch("/api" + path, {
      ...options,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        ...options.headers,
      },
    });
    const body = await response.json();
    if (!response.ok) {
      if (response.status === 401 && user) {
        setUser(null);
        setCsrf("");
        setInventory(null);
      }
      const detail = body.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : detail?.errors?.map((item: { message: string }) => item.message).join(" ") ||
              detail?.message ||
              "Something went wrong. Please try again.",
      );
    }
    return body;
  }
  async function updateSelectedRoom(kind: "category" | "number", value: string | null) {
    if (!selected || !owner) return;
    setBusy(true);
    setError("");
    try {
      const current = await api("/planning");
      await api("/planning/rooms/" + selected.id + "/" + kind, {
        method: "PUT",
        body: JSON.stringify({ revision: current.revision, [kind]: value }),
      });
      const next = await api("/inventory");
      setInventory(next);
      setSelected(next.rooms.find((r: Room) => r.id === selected.id) || null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    Promise.all([
      fetch("/api/setup/status").then((r) => {
        if (!r.ok)
          throw Error("The workspace is starting. Please refresh in a moment.");
        return r.json();
      }),
      fetch("/api/auth/me").then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([s, me]) => {
        setSetup(s.setup_required);
        if (me) {
          setUser(me.user);
          setCsrf(me.csrf_token);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (user && page === "rooms") {
      api("/inventory")
        .then(setInventory)
        .catch((e) => setError(e.message));
    }
  }, [user?.id, page]);
  useEffect(() => {
    if ((user?.role === "owner" || user?.role === "editor") && page === "users") loadAccounts();
  }, [page, user?.id]);
  useEffect(() => {
    if (!selected && !rules && editing === undefined) return;
    const previous = document.activeElement as HTMLElement | null,
      modal = document.querySelector<HTMLElement>(".modal");
    if (!modal) return;
    document.body.classList.add("modal-open");
    (
      modal.querySelector<HTMLElement>("input") ||
      modal.querySelector<HTMLElement>("button")
    )?.focus();
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelected(null);
        setRules(false);
        setEditing(undefined);
        setError("");
      }
      if (e.key === "Tab") {
        const items = Array.from(
          modal.querySelectorAll<HTMLElement>(
            'button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]',
          ),
        );
        if (e.shiftKey && document.activeElement === items[0]) {
          e.preventDefault();
          items.at(-1)?.focus();
        } else if (!e.shiftKey && document.activeElement === items.at(-1)) {
          e.preventDefault();
          items[0]?.focus();
        }
      }
    };
    document.addEventListener("keydown", keys);
    return () => {
      document.removeEventListener("keydown", keys);
      document.body.classList.remove("modal-open");
      previous?.focus();
    };
  }, [selected, rules, editing, user?.id]);
  function loadAccounts() {
    api("/users")
      .then((d) => setAccounts(d.users))
      .catch((e) => setError(e.message));
  }
  async function authenticate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget),
      body: any = { username: f.get("username"), password: f.get("password") };
    if (setup) body.display_name = f.get("display_name");
    try {
      const d = await api(setup ? "/setup" : "/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
        headers: setup
          ? { "X-Bootstrap-Token": String(f.get("setup_key")) }
          : {},
      });
      setUser(d.user);
      setCsrf(d.csrf_token);
      setSetup(false);
      setNotice("");
      setPage("planner");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST", body: "{}" });
      setUser(null);
      setCsrf("");
      setInventory(null);
      setError("");
      setNotice("You have signed out.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function saveAccount(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const body: any = {
      display_name: account.display_name,
      role: account.role,
      side: account.role === "family" ? account.side : null,
    };
    if (editing) {
      Object.assign(body, { version: account.version, active: account.active });
      if (account.password) body.password = account.password;
    } else
      Object.assign(body, {
        username: account.username,
        password: account.password,
      });
    try {
      await api(editing ? "/users/" + editing.id : "/users", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(body),
      });
      setEditing(undefined);
      setAccount(blankAccount());
      setNotice(
        editing
          ? "Access updated. Previous sessions have been signed out."
          : "Account created.",
      );
      loadAccounts();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function editAccount(item: User | null) {
    setError("");
    setNotice("");
    setEditing(item);
    setAccount(
      item
        ? {
            ...blankAccount(),
            ...item,
            role: item.role === "owner" ? "family" : item.role,
            side: item.side || "bride",
            password: "",
          }
        : blankAccount(),
    );
  }

  if (loading)
    return (
      <div className="loading">
        <Flower2 size={36} />
        <p>Opening your workspace…</p>
      </div>
    );
  if (!user)
    return (
      <main className="auth-layout">
        <header className="auth-topbar">
          <div className="brand">
            <span className="brand-mark"><Flower2 /></span>
            <strong>ROOM TO CELEBRATE</strong>
          </div>
          <div className="auth-top-actions">
            <span className="auth-event-pill"><CalendarDays size={16} /> 24–26 NOV 2026</span>
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </div>
        </header>
        <section className="auth-form-area">
          <form className="auth-card" onSubmit={authenticate}>
            <div className="auth-card-brand"><span className="brand-mark"><Flower2 /></span><strong>ROOM TO CELEBRATE</strong></div>
            <span className="eyebrow">PRIVATE WEDDING WORKSPACE</span>
            <h1>{setup ? "Create your workspace" : "Sign in to the room planner"}</h1>
            <p>
              {setup
                ? "Create the one owner account. Full-access editors can be added later from Users & access."
                : "Use your assigned planner username and password."}
            </p>
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
            {setup && (
              <>
                <label>
                  Your name
                  <input
                    name="display_name"
                    autoComplete="name"
                    maxLength={80}
                    required
                  />
                </label>
                <label>
                  Private setup key
                  <input
                    name="setup_key"
                    type="password"
                    autoComplete="off"
                    required
                  />
                  <small>
                    Use the one-time key supplied privately by your
                    administrator.
                  </small>
                </label>
              </>
            )}
            <label>
              Username
              <input
                name="username"
                autoComplete="username"
                minLength={3}
                maxLength={32}
                pattern="[A-Za-z0-9][A-Za-z0-9_.-]+"
                required
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={setup ? "new-password" : "current-password"}
                minLength={setup ? 14 : 1}
                maxLength={256}
                required
              />
              {setup && (
                <small>
                  Use at least 14 characters. A memorable phrase works well.
                </small>
              )}
            </label>
            <button className="primary" disabled={busy}>
              {busy
                ? "Please wait…"
                : setup
                  ? "Create my workspace"
                  : "Sign in"}
              <ArrowRight size={18} />
            </button>
            <div className="privacy-line">
              <ShieldCheck size={15} />
              Private access. No public guest list.
            </div>
          </form>
        </section>
        <footer className="auth-footer">Wedding accommodation planner · Private workspace</footer>
      </main>
    );

  const owner = user.role === "owner" || user.role === "editor",
    roleLabel = user.role === "owner"
      ? "Owner"
      : user.role === "editor"
        ? "Editor · Full control"
      : user.role === "reception"
        ? "Reception · View only"
        : `${user.side === "bride" ? "Bride" : "Groom"} side · View only`;
  const propertyRooms =
    inventory?.rooms.filter((r) => r.hotel_id === hotel) || [];
  const visibleRooms = propertyRooms.filter(
    (r) => floor === "all" || String(r.floor) === floor,
  );
  const blocks = hotel === "wyndham" ? [1, 2, 3, 4, 5, 6] : [null];
  return (
    <div className="workspace">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Flower2 />
          </span>
          <span>
            ROOM TO
            <br />
            <b>CELEBRATE</b>
          </span>
        </div>
        <span className="nav-caption">THE WEDDING WORKSPACE</span>
        <nav aria-label="Main navigation">
          {[
            {
              id: "planner",
              label: "Room planner",
              icon: <LayoutGrid size={18} />,
            },
            {
              id: "guests",
              label: "Guests & families",
              icon: <UsersRound size={18} />,
            },
            {
              id: "attendance",
              label: "Arrivals & functions",
              icon: <CalendarDays size={18} />,
            },
            ...(owner
              ? [
                  {
                    id: "billing",
                    label: "Attendance & billing",
                    icon: <CalendarDays size={18} />,
                  },
                  {
                    id: "rules",
                    label: "Rooms & rules",
                    icon: <ShieldCheck size={18} />,
                  },
                ]
              : []),
          ].map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "nav-item active" : "nav-item"}
              onClick={() => {
                setPage(item.id);
                setNotice("");
                setError("");
              }}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
          {owner && (
            <button
              className={page === "users" ? "nav-item active" : "nav-item"}
              onClick={() => {
                setPage("users");
                setNotice("");
                setError("");
              }}
            >
              <UsersRound size={18} />
              Users & access
            </button>
          )}
        </nav>
        <div className="sidebar-bottom">
          <span className="avatar">
            {user.display_name.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>{user.display_name}</strong>
            <small>{roleLabel}</small>
          </div>
          <button
            className="icon-button"
            title="Sign out"
            aria-label="Sign out"
            onClick={logout}
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span className="breadcrumb">
            Wedding workspace <ChevronRight size={13} />
            <b>
              {(
                {
                  planner: "Room planner",
                  guests: "Guests & families",
                  attendance: "Arrivals & functions",
                  billing: "Attendance & billing",
                  rules: "Rooms & rules",
                  users: "Users & access",
                } as Record<string, string>
              )[page] || "Rooms"}
            </b>
          </span>
          <span className="date-pill">
            <CalendarDays size={15} />
            24–26 Nov 2026
          </span>
          <span className="access-pill">
            <LockKeyhole size={13} />
            {owner ? "Editing access" : "View only"}
          </span>
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </header>
        <main className="main-content">
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
          {["planner", "guests", "billing", "rules", "attendance"].includes(
            page,
          ) ? (
            <PlanningWorkspace
              user={user}
              csrf={csrf}
              page={page}
              onExpired={() => {
                setUser(null);
                setCsrf("");
                setInventory(null);
              }}
            />
          ) : page === "rooms" ? (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">EVERY STAY, THOUGHT THROUGH</span>
                  <h1>
                    Room overview<span className="heading-dot">.</span>
                  </h1>
                  <p>One view of the spaces bringing everyone together.</p>
                </div>
                <button className="secondary" onClick={() => setRules(true)}>
                  <ShieldCheck size={16} />
                  Planning rules
                </button>
              </div>
              <div className="stat-grid">
                <Stat
                  icon={<Building2 />}
                  value="50"
                  label="Hotel rooms"
                  note="Across two properties"
                />
                <Stat
                  icon={<BedDouble />}
                  value="44"
                  label="Wyndham rooms"
                  note={`${inventory?.rooms.filter((r) => r.hotel_id === "wyndham" && r.category === "superior").length ?? 20} Superior · ${inventory?.rooms.filter((r) => r.hotel_id === "wyndham" && r.category === "premium").length ?? 24} Premium`}
                />
                <Stat
                  icon={<LockKeyhole />}
                  value="4"
                  label="Family rooms held"
                  note="Premium numbers to be chosen"
                />
                <Stat
                  icon={<UsersRound />}
                  value="12"
                  label="Staff beds"
                  note="Separate dormitory"
                />
              </div>
              <div className="planning-columns">
                <section className="inventory-panel">
                  <div
                    className="property-tabs"
                    role="tablist"
                    aria-label="Property"
                  >
                    {[
                      { id: "wyndham", label: "Wyndham Garden" },
                      { id: "second", label: "Second hotel" },
                      { id: "staff", label: "Staff dormitory" },
                    ].map((h) => (
                      <button
                        key={h.id}
                        role="tab"
                        aria-selected={hotel === h.id}
                        className={hotel === h.id ? "selected" : ""}
                        onClick={() => {
                          setHotel(h.id);
                          setFloor("all");
                        }}
                      >
                        {h.label}
                      </button>
                    ))}
                  </div>
                  <div className="inventory-toolbar">
                    <div>
                      <h2>
                        {hotel === "staff"
                          ? "A separate space for the team"
                          : hotel === "second"
                            ? "Six more rooms, close to the celebration"
                            : "The Wyndham room collection"}
                      </h2>
                      <p>
                        {hotel === "staff"
                          ? "12 beds · Drivers, staff and workers only"
                          : hotel === "second"
                            ? "Room numbers and bed arrangements are still to be entered."
                            : "Six blocks · Ground and first floors"}
                      </p>
                    </div>
                    {hotel !== "staff" && (
                      <label className="floor-select">
                        <span className="sr-only">Filter floor</span>
                        <select
                          value={floor}
                          onChange={(e) => setFloor(e.target.value)}
                        >
                          <option value="all">All floors</option>
                          <option value="0">Ground floor</option>
                          <option value="1">First floor</option>
                        </select>
                      </label>
                    )}
                  </div>
                  {hotel === "wyndham" && (
                    <div className="reserve-note">
                      <LockKeyhole size={16} />
                      <span>
                        <b>Four Premium rooms are held for family.</b> Room
                        numbers haven’t been selected yet; none are guessed.
                      </span>
                    </div>
                  )}
                  {!inventory ? (
                    <p className="empty">Loading rooms…</p>
                  ) : hotel === "staff" ? (
                    <div className="bed-grid">
                      {inventory.staff_beds.map((b) => (
                        <div className="staff-bed" key={b.id}>
                          <BedDouble size={22} />
                          <strong>Bed {b.id}</strong>
                          <span>Unassigned</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="blocks">
                      {blocks.map((block) => (
                        <div className="block" key={block ?? "second"}>
                          {block && (
                            <div className="block-title">
                              <span>
                                BLOCK {String(block).padStart(2, "0")}
                              </span>
                              <small>
                                {
                                  visibleRooms.filter((r) => r.block === block)
                                    .length
                                }{" "}
                                rooms
                              </small>
                            </div>
                          )}
                          {[0, 1]
                            .filter(
                              (f) => floor === "all" || floor === String(f),
                            )
                            .map((f) => (
                              <div className="floor-row" key={f}>
                                <div className="floor-label">
                                  {f === 0 ? "GROUND" : "FIRST"}
                                  <span>FLOOR</span>
                                </div>
                                <div className="room-grid">
                                  {visibleRooms
                                    .filter(
                                      (r) => r.block === block && r.floor === f,
                                    )
                                    .map((room, i) => (
                                      <button
                                        key={room.id}
                                        className={`room-card ${room.category === "premium" ? "premium" : ""}`}
                                        onClick={() => setSelected(room)}
                                      >
                                        <span className="room-number">
                                          {room.number || `Room ${i + 1}`}
                                          <BedDouble size={15} />
                                        </span>
                                        <span>
                                          {room.category === "pending"
                                            ? "Number pending"
                                            : room.category === "superior"
                                              ? "Superior"
                                              : "Premium"}
                                        </span>
                                        <small>
                                          {room.adult_capacity} adults ·{" "}
                                          {room.bed_type === "pending"
                                            ? "Beds pending"
                                            : room.bed_type === "twin"
                                              ? "Twin beds"
                                              : "King bed"}
                                        </small>
                                      </button>
                                    ))}
                                  {visibleRooms.filter(
                                    (r) => r.block === block && r.floor === f,
                                  ).length === 0 && (
                                    <span className="no-rooms">
                                      No guest rooms on this floor
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="inventory-footer">
                    <span>
                      <i className="legend superior" />
                      Superior
                    </span>
                    <span>
                      <i className="legend premium" />
                      Premium
                    </span>
                    <small>
                      Inventory view · Placement and guest assignment follow
                      next
                    </small>
                  </div>
                </section>
                <aside className="summary-panel">
                  <span className="eyebrow">AT A GLANCE</span>
                  <h2>
                    A little room
                    <br />
                    to plan ahead.
                  </h2>
                  <div className="summary-row">
                    <span>
                      {hotel === "staff"
                        ? "Dormitory beds"
                        : "Rooms in this property"}
                    </span>
                    <b>{hotel === "staff" ? 12 : propertyRooms.length}</b>
                  </div>
                  {hotel === "wyndham" && (
                    <>
                      <div className="summary-row">
                        <span>General guest inventory</span>
                        <b>40</b>
                      </div>
                      <div className="summary-row">
                        <span>Held for family</span>
                        <b>4</b>
                      </div>
                    </>
                  )}
                  <div className="summary-note">
                    <Eye size={18} />
                    <p>
                      Guest allocation hasn’t started. Occupancy and side totals
                      will appear when people are added.
                    </p>
                  </div>
                  {owner && inventory?.cost_policy && (
                    <div className="pricing">
                      <span className="tiny-label">YOUR PLANNING BASELINE</span>
                      <div>
                        <span>Wyndham included guests</span>
                        <b>{inventory.cost_policy.wyndham_allowance} / night</b>
                      </div>
                      <div>
                        <span>Additional resident</span>
                        <b>
                          {rupees(inventory.cost_policy.wyndham_excess_paise)} /
                          night
                        </b>
                      </div>
                      <div>
                        <span>Staff meal</span>
                        <b>
                          {rupees(inventory.cost_policy.staff_meal_paise)} /
                          person
                        </b>
                      </div>
                      <div>
                        <span>Second hotel · estimate</span>
                        <b>
                          {rupees(inventory.cost_policy.second_hotel_day_paise)}{" "}
                          / day
                        </b>
                      </div>
                      <small>
                        Second-hotel rate is provisional. Non-resident meal
                        rates are not entered. These are rates, not a calculated
                        bill.
                      </small>
                    </div>
                  )}
                  <div className="foundation-tag">
                    <span />
                    Foundation preview
                  </div>
                </aside>
              </div>
            </>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">A CLEAR PLACE FOR EVERYONE</span>
                  <h1>
                    Users & access<span className="heading-dot">.</span>
                  </h1>
                  <p>
                    Owners and editors make changes. Family and reception viewers follow along.
                  </p>
                </div>
                <button
                  className="primary compact"
                  onClick={() => editAccount(null)}
                >
                  <Plus size={17} />
                  Add account
                </button>
              </div>
              <div className="permission-banner">
                <ShieldCheck />
                <div>
                  <strong>One owner. Full-access editors.</strong>
                  <p>
                    Owners and editors can edit guests, rooms, rates and accounts.
                    Family viewers see their own side; reception cannot see costs.
                    Changing access signs out that account’s existing sessions.
                  </p>
                </div>
              </div>
              <section className="accounts-panel">
                <div className="section-heading">
                  <h2>People with access</h2>
                  <span>{accounts.length} accounts</span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Person</th>
                        <th>Access</th>
                        <th>Status</th>
                        <th>
                          <span className="sr-only">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {accounts.map((a) => (
                        <tr key={a.id}>
                          <td>
                            <strong>{a.display_name}</strong>
                            <small>{a.username}</small>
                          </td>
                          <td>
                            {a.role === "owner"
                              ? "Owner · Full control"
                              : a.role === "editor"
                                ? "Editor · Full control"
                              : a.role === "reception"
                                ? "Reception · View only"
                                : `${a.side === "bride" ? "Bride" : "Groom"} side · View only`}
                          </td>
                          <td>
                            <span
                              className={
                                a.active
                                  ? "status-badge"
                                  : "status-badge suspended"
                              }
                            >
                              {a.active ? "Active" : "Suspended"}
                            </span>
                          </td>
                          <td>
                            {a.role !== "owner" && (
                              <button
                                className="text-button"
                                onClick={() => editAccount(a)}
                              >
                                Manage
                                <ChevronRight size={14} />
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </main>
        <footer className="page-footer">
          <Flower2 size={13} />
          Room to Celebrate<span>A thoughtful stay starts here.</span>
        </footer>
      </div>
      {(selected || rules) && (
        <div
          className="modal-backdrop"
          onClick={() => {
            setSelected(null);
            setRules(false);
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={rules ? "Planning rules" : "Room details"}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close icon-button"
              aria-label="Close details"
              onClick={() => {
                setSelected(null);
                setRules(false);
              }}
            >
              <X />
            </button>
            {rules ? (
              <>
                <span className="eyebrow">THE AGREED GUIDELINES</span>
                <h2>Thoughtful by design.</h2>
                <ul className="rule-list">
                  <li>
                    Couples with children use Superior rooms with extra bedding.
                  </li>
                  <li>
                    Age 50+ and accessibility tags require ground-floor
                    placement.
                  </li>
                  <li>
                    Only explicitly eligible guests can be assigned to the
                    second hotel.
                  </li>
                  <li>Four Premium rooms remain held for family.</li>
                  <li>Staff and guests always have separate accommodation.</li>
                  <li>
                    Room placement and compatibility checks will be added in the
                    assignment stage.
                  </li>
                </ul>
              </>
            ) : (
              selected && (
                <>
                  <span className="eyebrow">ROOM INVENTORY</span>
                  <h2>
                    {selected.number
                      ? `Room ${selected.number}`
                      : "Room number pending"}
                  </h2>
                  <dl>
                    <dt>Category</dt>
                    <dd>
                      {selected.category === "pending"
                        ? "To be entered"
                        : selected.category}
                    </dd>
                    <dt>Floor</dt>
                    <dd>
                      {selected.floor === 0 ? "Ground floor" : "First floor"}
                    </dd>
                    <dt>Adult-counted capacity</dt>
                    <dd>{selected.adult_capacity}</dd>
                    <dt>Bed arrangement</dt>
                    <dd>
                      {selected.bed_type === "pending"
                        ? "Not supplied"
                        : selected.bed_type}
                    </dd>
                  </dl>
                  <p className="subtle">
                    Young-child sharing is a separate policy. This capacity does
                    not establish a total physical headcount limit. Guest
                    allocation is not available in this stage.
                  </p>
                  {owner && selected.hotel_id === "wyndham" && (
                    <>
                      <p className="subtle">
                        A room-type change applies to both nights. It will be
                        refused if a placement or the four-room Premium reserve
                        would become invalid. Confirm the actual change with the hotel separately.
                      </p>
                      <button
                        className="secondary compact"
                        disabled={busy}
                        onClick={() => updateSelectedRoom("category", selected.category === "superior" ? "premium" : "superior")}
                      >
                        {selected.category === "superior" ? "Upgrade to Premium" : "Downgrade to Superior"}
                      </button>
                    </>
                  )}
                  {owner && (
                    <form
                      className="room-number-action"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const form = new FormData(e.currentTarget);
                        updateSelectedRoom("number", String(form.get("room-number") || "").trim() || null);
                      }}
                    >
                      <label>
                        Room number
                        <input
                          key={selected.id + ":" + (selected.number || "")}
                          name="room-number"
                          maxLength={16}
                          required={selected.hotel_id === "wyndham"}
                          defaultValue={selected.number || ""}
                        />
                      </label>
                      <button className="secondary compact" disabled={busy}>
                        Change room number
                      </button>
                    </form>
                  )}
                  {error && <p className="alert error" role="alert">{error}</p>}
                </>
              )
            )}
          </section>
        </div>
      )}
      {editing !== undefined && (
        <div className="modal-backdrop">
          <form
            className="modal account-modal"
            role="dialog"
            aria-modal="true"
            aria-label={editing ? "Manage account" : "Add account"}
            onSubmit={saveAccount}
          >
            <button
              type="button"
              className="modal-close icon-button"
              aria-label="Close account form"
              onClick={() => {
                setEditing(undefined);
                setError("");
              }}
            >
              <X />
            </button>
            <span className="eyebrow">ACCOUNT ACCESS</span>
            <h2>{editing ? "Manage account" : "Welcome someone in."}</h2>
            {error && (
              <div className="alert error" role="alert">
                {error}
              </div>
            )}
            <label>
              Display name
              <input
                required
                maxLength={80}
                value={account.display_name}
                onChange={(e) =>
                  setAccount({ ...account, display_name: e.target.value })
                }
              />
            </label>
            {!editing && (
              <label>
                Username
                <input
                  required
                  minLength={3}
                  maxLength={32}
                  pattern="[A-Za-z0-9][A-Za-z0-9_.-]+"
                  autoComplete="off"
                  value={account.username}
                  onChange={(e) =>
                    setAccount({ ...account, username: e.target.value })
                  }
                />
              </label>
            )}
            <label>
              {editing ? "New password (optional)" : "Password"}
              <input
                type="password"
                autoComplete="new-password"
                required={!editing}
                minLength={14}
                maxLength={256}
                value={account.password}
                onChange={(e) =>
                  setAccount({ ...account, password: e.target.value })
                }
              />
              <small>
                At least 14 characters. Share privately with the viewer.
              </small>
            </label>
            <div className="form-row">
              <label>
                Access type
                <select
                  value={account.role}
                  onChange={(e) =>
                    setAccount({
                      ...account,
                      role: e.target.value as Account["role"],
                    })
                  }
                >
                  <option value="family">Family viewer</option>
                  <option value="reception">Reception viewer</option>
                  <option value="editor">Editor · full access</option>
                </select>
              </label>
              {account.role === "family" && (
                <label>
                  Side
                  <select
                    value={account.side}
                    onChange={(e) =>
                      setAccount({
                        ...account,
                        side: e.target.value as Account["side"],
                      })
                    }
                  >
                    <option value="bride">Bride side</option>
                    <option value="groom">Groom side</option>
                  </select>
                </label>
              )}
            </div>
            {editing && (
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={account.active}
                  onChange={(e) =>
                    setAccount({ ...account, active: e.target.checked })
                  }
                />
                Account is active
              </label>
            )}
            <button className="primary" disabled={busy}>
              {busy ? "Saving…" : editing ? "Save access" : "Create account"}
              <ArrowRight size={16} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
function Stat({
  icon,
  value,
  label,
  note,
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
  note: string;
}) {
  return (
    <div className="stat">
      <span className="stat-icon">{icon}</span>
      <strong>{value}</strong>
      <b>{label}</b>
      <small>{note}</small>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
