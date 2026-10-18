import React, { useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  BedDouble,
  Building2,
  CalendarDays,
  Check,
  ChevronRight,
  Eye,
  Flower2,
  KeyRound,
  LayoutGrid,
  LockKeyhole,
  LogOut,
  Plus,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";
import "./style.css";

type User = {
  id: string;
  username: string;
  display_name: string;
  role: "owner" | "family" | "reception";
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
  role: "family" | "reception";
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
  const [user, setUser] = useState<User | null>(null),
    [csrf, setCsrf] = useState(""),
    [loading, setLoading] = useState(true),
    [setup, setSetup] = useState(false);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [page, setPage] = useState("rooms"),
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
      throw new Error(body.detail || "Something went wrong. Please try again.");
    }
    return body;
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
    if (user) {
      api("/inventory")
        .then(setInventory)
        .catch((e) => setError(e.message));
    }
  }, [user?.id]);
  useEffect(() => {
    if (user?.role === "owner" && page === "users") loadAccounts();
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
      setPage("rooms");
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
          : "Viewer account created.",
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
            role: item.role === "reception" ? "reception" : "family",
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
        <section className="auth-story">
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
          <div className="story-copy">
            <span className="eyebrow">ONE CELEBRATION. EVERYONE TOGETHER.</span>
            <h1>
              A place
              <br />
              for everyone.
            </h1>
            <p>
              A little less juggling.
              <br />A little more celebrating.
            </p>
            <div className="invitation-date">
              <CalendarDays size={18} />
              24–26 November 2026
            </div>
          </div>
          <div className="map-art" aria-hidden="true">
            <div className="arch">
              <Flower2 size={46} />
            </div>
            <div className="art-room">
              <BedDouble />
              Family together<span>Ground floor</span>
            </div>
            <div className="art-room art-room-two">
              <Check />A thoughtful stay<span>Everyone considered</span>
            </div>
            <div className="art-dots" />
          </div>
          <footer>Thoughtful planning. A warm welcome.</footer>
        </section>
        <section className="auth-form-area">
          <form className="auth-card" onSubmit={authenticate}>
            <span className="round-icon">
              <KeyRound />
            </span>
            <span className="eyebrow">YOUR PRIVATE PLANNING SPACE</span>
            <h2>{setup ? "Make it yours." : "Welcome back."}</h2>
            <p>
              {setup
                ? "Create the one owner account. You choose your login; everyone else will have view-only access."
                : "Sign in to bring the accommodation plan together."}
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
          <span className="auth-caption">
            Wedding accommodation planner · Foundation preview
          </span>
        </section>
      </main>
    );

  const owner = user.role === "owner",
    roleLabel = owner
      ? "Owner"
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
          <button
            className={page === "rooms" ? "nav-item active" : "nav-item"}
            onClick={() => {
              setPage("rooms");
              setNotice("");
              setError("");
            }}
          >
            <LayoutGrid size={18} />
            Room overview
            <ChevronRight size={15} />
          </button>
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
        <div className="coming-card">
          <span className="tiny-label">COMING NEXT</span>
          <b>People make the plan.</b>
          <p>Guest entry and room assignments are the next stage.</p>
        </div>
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
            <b>{page === "users" ? "Users & access" : "Rooms"}</b>
          </span>
          <span className="date-pill">
            <CalendarDays size={15} />
            24–26 Nov 2026
          </span>
          <span className="access-pill">
            <LockKeyhole size={13} />
            {owner ? "Only you can edit" : "View only"}
          </span>
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
          {page === "rooms" ? (
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
                  note="20 Superior · 24 Premium"
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
                    You make the changes. Your family and reception follow
                    along.
                  </p>
                </div>
                <button
                  className="primary compact"
                  onClick={() => editAccount(null)}
                >
                  <Plus size={17} />
                  Add viewer
                </button>
              </div>
              <div className="permission-banner">
                <ShieldCheck />
                <div>
                  <strong>One owner. Thoughtful access.</strong>
                  <p>
                    Only your login can edit. Family viewers see their own side;
                    reception cannot see costs. Changes to access sign out that
                    viewer’s existing sessions.
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
            aria-label={editing ? "Manage viewer" : "Add viewer"}
            onSubmit={saveAccount}
          >
            <button
              type="button"
              className="modal-close icon-button"
              aria-label="Close viewer form"
              onClick={() => {
                setEditing(undefined);
                setError("");
              }}
            >
              <X />
            </button>
            <span className="eyebrow">VIEW-ONLY ACCESS</span>
            <h2>{editing ? "Manage viewer" : "Welcome someone in."}</h2>
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
              {busy ? "Saving…" : editing ? "Save access" : "Create viewer"}
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
