import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity as ActivityIcon,
  ArrowDownToLine,
  ArrowRight,
  Bell,
  Box,
  Building2,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  ClipboardList,
  Factory,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  MapPin,
  Menu,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Tag,
  Users,
  X,
  CalendarDays,
  BookOpen,
  UserRoundCog,
  LockKeyhole,
} from "lucide-react";
import type { Activity, AuditRun, Plant, RedTag, ZonalLeader } from "./types";
import {
  fetchActivities,
  fetchAudits,
  fetchPlants,
  fetchRedTags,
  fetchZonalLeaders,
  fetchLocalIdentities,
  fetchIdentity,
  switchIdentity,
  logout,
  type WorkspaceIdentity,
} from "./api/client";
import { Overview } from "./components/Workspace/Overview";
import {
  NewWork,
  WorkDetail,
  WorkOrders,
} from "./components/Workspace/WorkOrders";
import { Assets } from "./components/Workspace/Assets";
import { Dialog, Empty } from "./components/Workspace/Shared";
import { isComplete, pillars } from "./components/Workspace/utils";
import { LeaderWorkspace } from "./components/Workspace/LeaderWorkspace";
import { AccessPanel, RoleSwitcher } from "./components/Workspace/AccessPanel";
import { roleLabels } from "./components/Workspace/accessDefinitions";
import {
  AuditWorkspace,
  RedTagsWorkspace,
  LocationsWorkspace,
  PeopleWorkspace,
} from "./components/Workspace/Operations";

const navigation = [
  {
    id: "overview",
    name: "Overview",
    icon: LayoutDashboard,
    permission: "overview.read",
  },
  {
    id: "work_orders",
    name: "Work orders",
    icon: ClipboardList,
    permission: "work.read",
  },
  {
    id: "audits",
    name: "Audits & inspections",
    icon: ClipboardCheck,
    permission: "audit.read",
  },
  { id: "redtags", name: "Red tags", icon: Tag, permission: "redtag.read" },
  {
    id: "locations",
    name: "Locations & zones",
    icon: MapPin,
    permission: "location.read",
  },
  { id: "assets", name: "Assets", icon: Box, permission: "asset.read" },
  {
    id: "standards",
    name: "5S standards",
    icon: BookOpen,
    permission: "standard.read",
  },
  {
    id: "reporting",
    name: "Reports & insights",
    icon: ActivityIcon,
    permission: "report.export",
  },
  {
    id: "settings",
    name: "People & teams",
    icon: Users,
    permission: "people.read",
  },
  {
    id: "access",
    name: "My access & roles",
    icon: LockKeyhole,
    permission: "access.read",
  },
];
const descriptions: Record<string, string> = {
  overview:
    "Performance, ownership, and verified improvement across your plant.",
  work_orders:
    "Clear ownership, practical actions, and a complete improvement history.",
  audits: "Measure observed conditions and make progress visible.",
  redtags: "Identify unnecessary items and track each disposition.",
  locations: "Departments, zones, and accountable workplace ownership.",
  assets: "Equipment, assigned locations, and recorded operating status.",
  standards: "A shared understanding of what good looks like.",
  reporting: "Measured results and reports within your assigned scope.",
  settings: "Operational profiles and the people responsible for each zone.",
  access: "Understand your permissions, scope, and approval boundaries.",
};
function initialTab() {
  const key = location.hash.slice(1);
  return navigation.some((n) => n.id === key) ? key : "overview";
}

export default function App() {
  const [tab, setTab] = useState(initialTab);
  const [identity, setIdentity] = useState<WorkspaceIdentity | null>(null);
  const [identities, setIdentities] = useState<WorkspaceIdentity[]>([]);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [plantId, setPlantId] = useState("");
  const [activities, setActivities] = useState<Activity[]>([]);
  const [audits, setAudits] = useState<AuditRun[]>([]);
  const [tags, setTags] = useState<RedTag[]>([]);
  const [people, setPeople] = useState<ZonalLeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [switchError, setSwitchError] = useState("");
  const [switching, setSwitching] = useState(false);
  const [roleDialog, setRoleDialog] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [newWork, setNewWork] = useState(false);
  const [selected, setSelected] = useState<Activity | null>(null);
  const [panel, setPanel] = useState<"search" | "inbox" | "help" | null>(null);
  const [search, setSearch] = useState("");
  const [days, setDays] = useState(30);
  const [toast, setToast] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sequence = useRef(0);
  const identityRef = useRef<WorkspaceIdentity | null>(null);
  const plant = plants.find((p) => p.id === plantId) || plants[0];
  const can = (permission: string) =>
    !!identity?.permissions.includes(permission);
  const limited = identity?.role === "zonal_leader";
  const current = navigation.find((n) => n.id === tab)!;
  const visibleNav = navigation.filter((n) => can(n.permission));
  const allowed = !!current && can(current.permission);
  const navigate = useCallback((next: string) => {
    setTab(next);
    location.hash = next;
    setMobileNav(false);
    window.scrollTo({ top: 0 });
  }, []);
  const notify = useCallback((text: string) => {
    setToast(text);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(""), 4500);
  }, []);
  const clearData = useCallback(() => {
    setActivities([]);
    setAudits([]);
    setTags([]);
    setPeople([]);
    setPlants([]);
    setSelected(null);
    setNewWork(false);
    setPanel(null);
  }, []);
  const loadData = useCallback(
    async (actor: WorkspaceIdentity, preferredPlant?: string) => {
      const ticket = ++sequence.current;
      setLoading(true);
      setError("");
      try {
        const list = await fetchPlants();
        if (ticket !== sequence.current) return;
        const id = list.some((p) => p.id === preferredPlant)
          ? preferredPlant!
          : list[0]?.id;
        setPlants(list);
        setPlantId(id || "");
        if (!id) return;
        const [work, assessments, redtags, members] = await Promise.all([
          fetchActivities({ plant_id: id }),
          fetchAudits(id),
          fetchRedTags({ plant_id: id }),
          actor.permissions.includes("people.read")
            ? fetchZonalLeaders(id)
            : Promise.resolve([]),
        ]);
        if (ticket !== sequence.current) return;
        setActivities(work);
        setAudits(assessments);
        setTags(redtags);
        setPeople(members);
      } catch (err) {
        if (ticket === sequence.current) setError((err as Error).message);
      } finally {
        if (ticket === sequence.current) setLoading(false);
      }
    },
    [],
  );
  useEffect(() => {
    let active = true;
    async function boot() {
      let choices: WorkspaceIdentity[] = [];
      try {
        choices = await fetchLocalIdentities();
      } catch {
        /* Non-demo servers do not expose sample identities. */
      }
      if (!active) return;
      setIdentities(choices);
      try {
        let actor: WorkspaceIdentity;
        try {
          actor = await fetchIdentity();
        } catch {
          const previous = sessionStorage.getItem("enertech.sample.identity");
          const initial =
            choices.find((p) => p.id === previous) ||
            choices.find((p) => p.role === "director");
          if (!initial)
            throw new Error(
              "Sign-in is required. Configure an identity provider for this non-preview server.",
            );
          actor = await switchIdentity(initial.id);
        }
        if (!active) return;
        identityRef.current = actor;
        setIdentity(actor);
        await loadData(actor);
      } catch (err) {
        if (active) {
          setError((err as Error).message);
          setLoading(false);
        }
      }
    }
    void boot();
    return () => {
      active = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [loadData]);
  useEffect(() => {
    if (!mobileNav) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.querySelector<HTMLButtonElement>(".mobile-close")?.focus();
    const onResize = () => {
      if (innerWidth > 1024) setMobileNav(false);
    };
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = overflow;
      window.removeEventListener("resize", onResize);
      previous?.focus();
    };
  }, [mobileNav]);
  useEffect(() => {
    const hash = () => {
      setTab(initialTab());
      setMobileNav(false);
    };
    const key = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPanel("search");
      }
      if (e.key === "Escape") setMobileNav(false);
    };
    window.addEventListener("hashchange", hash);
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("hashchange", hash);
      window.removeEventListener("keydown", key);
    };
  }, []);
  useEffect(() => {
    const focus = async () => {
      if (!identityRef.current) return;
      try {
        const actor = await fetchIdentity();
        if (
          actor.id !== identityRef.current.id ||
          JSON.stringify(actor.permissions) !==
            JSON.stringify(identityRef.current.permissions) ||
          actor.zone_id !== identityRef.current.zone_id
        ) {
          clearData();
          identityRef.current = actor;
          setIdentity(actor);
          await loadData(actor);
        }
      } catch {
        ++sequence.current;
        identityRef.current = null;
        setIdentity(null);
        clearData();
        setLoading(false);
        setError("Your session ended. Choose a sample account to continue.");
      }
    };
    window.addEventListener("focus", focus);
    return () => window.removeEventListener("focus", focus);
  }, [clearData, loadData]);
  const changeRole = async (id: string) => {
    setSwitching(true);
    setSwitchError("");
    ++sequence.current;
    clearData();
    setLoading(true);
    try {
      const actor = await switchIdentity(id);
      identityRef.current = actor;
      setIdentity(actor);
      sessionStorage.setItem("enertech.sample.identity", actor.id);
      setRoleDialog(false);
      navigate("overview");
      await loadData(actor);
      notify(
        `Switched to ${roleLabels[actor.role]} · permissions applied by the server`,
      );
    } catch (err) {
      setSwitchError((err as Error).message);
      setError("Role switch failed. Retry or return to the current account.");
      setLoading(false);
    } finally {
      setSwitching(false);
    }
  };
  const refresh = () => identity && void loadData(identity, plantId);
  const updateWork = (work: Activity) => {
    setActivities((old) => old.map((a) => (a.id === work.id ? work : a)));
    setSelected(work);
    notify("Work order saved");
  };
  const exportCsv = () => {
    const quote = (v: unknown) => {
      let text = String(v ?? "");
      if (/^[=+@\-\t\r]/.test(text)) text = "'" + text;
      return '"' + text.replaceAll('"', '""') + '"';
    };
    const rows = [
      ["Work order", "Title", "Status", "Priority", "Assignee", "Due date"],
      ...activities.map((a) => [
        a.activity_number,
        a.title,
        a.status,
        a.priority,
        a.assignee_name,
        a.due_date,
      ]),
    ];
    const url = URL.createObjectURL(
      new Blob(
        ["\uFEFF" + rows.map((r) => r.map(quote).join(",")).join("\r\n")],
        { type: "text/csv;charset=utf-8" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `enertech-${identity?.role}-work-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    notify("Scoped work-order report exported");
  };
  const review = activities.filter((a) => a.status === "submitted_for_review");
  const open = activities.filter((a) => !isComplete(a.status));
  const leader: ZonalLeader | null =
    identity && limited
      ? {
          id: identity.id,
          first_name: identity.first_name,
          last_name: identity.last_name,
          email: identity.email,
          role: identity.role,
          plant_id: identity.plant_id,
          assigned_zone_id: identity.zone_id,
          assigned_zone_name: identity.zone_name,
          is_active: true,
          active_tasks_count: open.length,
          completed_tasks_count: activities.length - open.length,
          created_at: "",
        }
      : null;
  if (!identity && !loading)
    return (
      <div className="session-screen">
        <div className="surface session-card">
          <img
            src="/brand/enertech-logo.png"
            alt="EnerTech — Answering All Power Needs"
          />
          <span className="eyebrow">5S OPERATIONS WORKSPACE</span>
          <h1>Choose your workspace</h1>
          <p>
            {error ||
              "Sign in to access the permissions and records assigned to your role."}
          </p>
          {identities.length > 0 && (
            <button
              className="btn btn-primary"
              onClick={() => setRoleDialog(true)}
            >
              <UserRoundCog />
              Choose sample account
            </button>
          )}
        </div>
        {roleDialog && (
          <RoleSwitcher
            current={null}
            identities={identities}
            busy={switching}
            error={switchError}
            onSwitch={(id) => void changeRole(id)}
            onClose={() => setRoleDialog(false)}
          />
        )}
      </div>
    );
  const title =
    tab === "overview"
      ? limited
        ? "My zone"
        : identity?.role === "director"
          ? "Director overview"
          : "Plant overview"
      : tab === "work_orders" && limited
        ? "My work"
        : current?.name;
  return (
    <div className="app-shell">
      <a
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
        className="skip-link"
      >
        Skip to main content
      </a>
      <button
        className={`mobile-scrim ${mobileNav ? "open" : ""}`}
        aria-label="Close navigation"
        onClick={() => setMobileNav(false)}
        tabIndex={-1}
      />
      <aside
        className={`side-rail ${mobileNav ? "open" : ""}`}
        aria-label="Main navigation"
        onKeyDown={(event) => {
          if (!mobileNav || event.key !== "Tab") return;
          const controls = Array.from(
            event.currentTarget.querySelectorAll<HTMLElement>(
              "button:not(:disabled), select, a[href]",
            ),
          ).filter((element) => element.offsetWidth > 0);
          const first = controls[0],
            last = controls.at(-1);
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
          }
        }}
      >
        <button
          className="mobile-close btn btn-ghost btn-square"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        >
          <X />
        </button>
        <div className="brand official-brand">
          <img src="/brand/enertech-logo.png" alt="EnerTech" />
          <span>5S OPERATIONS</span>
        </div>
        <div className="workspace-select">
          <span className="workspace-icon">
            <Factory size={17} />
          </span>
          <div className="min-w-0 flex-1">
            <strong>EnerTech UPS Pvt. Ltd.</strong>
            <select
              aria-label="Select plant"
              value={plantId}
              onChange={(e) =>
                identity && void loadData(identity, e.target.value)
              }
            >
              {plants.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} ·{" "}
                  {p.name.replace("Enertech Manufacturing Facility - ", "")}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {visibleNav
            .filter((n) => !["reporting", "settings", "access"].includes(n.id))
            .map((n) => (
              <button
                className={`nav-item ${n.id === tab ? "active" : ""}`}
                aria-current={n.id === tab ? "page" : undefined}
                key={n.id}
                onClick={() => navigate(n.id)}
              >
                <n.icon />
                <span>
                  {limited && n.id === "overview"
                    ? "My zone"
                    : limited && n.id === "work_orders"
                      ? "My work"
                      : n.name}
                </span>
                {n.id === "work_orders" && open.length > 0 && (
                  <span className="nav-count">{open.length}</span>
                )}
                {n.id === "redtags" && tags.some((t) => !t.is_closed) && (
                  <span className="nav-count">
                    {tags.filter((t) => !t.is_closed).length}
                  </span>
                )}
              </button>
            ))}
        </nav>
        <div className="nav-label mt-6!">INSIGHTS & ACCESS</div>
        <nav>
          {visibleNav
            .filter((n) => ["reporting", "settings", "access"].includes(n.id))
            .map((n) => (
              <button
                className={`nav-item ${n.id === tab ? "active" : ""}`}
                key={n.id}
                aria-current={n.id === tab ? "page" : undefined}
                onClick={() => navigate(n.id)}
              >
                <n.icon />
                {n.name}
              </button>
            ))}
        </nav>
        <div className="rail-bottom">
          <button className="nav-item" onClick={() => setPanel("help")}>
            <CircleHelp />
            Workspace help
            <ArrowRight className="ml-auto" />
          </button>
          <div className="profile">
            <span className="initials">
              {identity?.first_name[0]}
              {identity?.last_name[0]}
            </span>
            <div className="flex-1">
              <strong>{identity?.name || "Connecting"}</strong>
              <small>
                {identity ? roleLabels[identity.role] : "Loading role"} ·{" "}
                {limited ? identity?.zone_name || "Unassigned" : "Plant scope"}
              </small>
            </div>
            <button
              className="signout-button"
              aria-label="Sign out"
              onClick={async () => {
                try {
                  await logout();
                  ++sequence.current;
                  identityRef.current = null;
                  setIdentity(null);
                  clearData();
                  setLoading(false);
                } catch (err) {
                  notify((err as Error).message);
                }
              }}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-column" inert={mobileNav}>
        <header className="topbar">
          <div className="flex min-w-0 items-center gap-3">
            <button
              className="btn btn-ghost btn-square mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobileNav(true)}
              aria-expanded={mobileNav}
            >
              <Menu />
            </button>
            <div className="breadcrumbs-text">
              <Building2 size={14} />
              <span>EnerTech 5S</span>
              <ChevronRight size={12} />
              <strong>{title}</strong>
            </div>
          </div>
          <div className="header-actions">
            <button
              className="header-search"
              onClick={() => setPanel("search")}
            >
              <Search size={15} />
              <span>Search workspace…</span>
              <kbd>Ctrl K</kbd>
            </button>
            {identities.length > 0 && (
              <button
                className="role-switch-button"
                aria-label="Switch workspace role"
                onClick={() => {
                  setSwitchError("");
                  setRoleDialog(true);
                }}
              >
                <UserRoundCog size={16} />
                <span>
                  {identity ? roleLabels[identity.role] : "Choose role"}
                </span>
                <span className="role-switch-hint">Switch role</span>
              </button>
            )}
            <button
              className="btn btn-ghost btn-square relative"
              aria-label="Open report inbox"
              onClick={() => setPanel("inbox")}
            >
              <Bell />
              {review.length > 0 && <i className="notification-dot" />}
            </button>
          </div>
        </header>
        {identities.length > 0 && (
          <div className="sample-strip">
            <span>
              <ShieldCheck size={12} /> LOCAL SAMPLE · Server-enforced role
              permissions
            </span>
            <button onClick={() => navigate("access")}>
              View my access <ArrowRight size={12} />
            </button>
          </div>
        )}
        <main id="main-content" tabIndex={-1} className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                {limited
                  ? "MY RESPONSIBILITY"
                  : identity?.role === "director"
                    ? "EXECUTIVE VISIBILITY"
                    : "5S OPERATIONS"}
              </div>
              <h1>{title}</h1>
              <p className="page-subtitle">
                {tab === "overview" && limited
                  ? "Your work, evidence, and zone progress — without the administrative clutter."
                  : descriptions[tab]}
              </p>
            </div>
            <div className="page-tools">
              {["overview", "reporting"].includes(tab) && !limited && (
                <label className="period-control">
                  <CalendarDays size={15} />
                  <select
                    aria-label="Dashboard reporting period"
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                  >
                    <option value="7">Last 7 days</option>
                    <option value="30">Last 30 days</option>
                    <option value="90">Last 90 days</option>
                  </select>
                </label>
              )}
              {can("report.export") &&
                ["reporting", "work_orders"].includes(tab) && (
                  <button
                    className="btn"
                    onClick={exportCsv}
                    disabled={!activities.length}
                  >
                    <ArrowDownToLine />
                    Export CSV
                  </button>
                )}
              {can("work.create") &&
                ["overview", "work_orders"].includes(tab) && (
                  <button
                    className="btn btn-primary"
                    disabled={loading || !plant}
                    onClick={() => setNewWork(true)}
                  >
                    <Plus />
                    {limited ? "Raise an action" : "Create work order"}
                  </button>
                )}
              {identity?.role === "director" && tab === "overview" && (
                <button className="btn" onClick={() => navigate("reporting")}>
                  Open reports
                  <ArrowRight />
                </button>
              )}
            </div>
          </div>
          {identity && (
            <div className="access-context">
              <span>
                <ShieldCheck size={14} />
                <strong>{roleLabels[identity.role]}</strong>
                <span className="context-divider">/</span>
                {limited
                  ? identity.zone_name || "No zone assigned"
                  : "Authorized plant data"}
                {identity.role === "director" && (
                  <span className="read-only-label">Read-only oversight</span>
                )}
              </span>
              <button className="text-link" onClick={() => navigate("access")}>
                What can I do?
                <ArrowRight />
              </button>
            </div>
          )}
          {error && (
            <div
              className="form-error flex items-center justify-between gap-3"
              role="alert"
            >
              <span>{error}</span>
              <button className="btn" onClick={refresh}>
                Retry
              </button>
            </div>
          )}
          {loading ? (
            <div className="surface loading-workspace">
              <LoaderCircle className="animate-spin" size={26} />
              <p>Loading authorized workspace…</p>
            </div>
          ) : !allowed ? (
            <section className="surface">
              <Empty
                title="This view isn’t available to your role"
                text="Your role permissions are enforced by the server. Return to your workspace or inspect your access."
                action={
                  <button className="btn" onClick={() => navigate("overview")}>
                    Back to my workspace
                    <ArrowRight />
                  </button>
                }
              />
            </section>
          ) : !plant ? (
            <section className="surface">
              <Empty
                title="No assigned plant available"
                text="Ask a supervisor to check your active plant and zone assignment."
              />
            </section>
          ) : (
            <>
              {tab === "overview" &&
                (leader ? (
                  <LeaderWorkspace
                    leader={leader}
                    plant={plant}
                    activities={activities}
                    audits={audits}
                    redTags={tags}
                    onOpen={setSelected}
                    onNavigate={navigate}
                    onCreate={() => setNewWork(true)}
                  />
                ) : (
                  <Overview
                    plant={plant}
                    activities={activities}
                    audits={audits}
                    redTags={tags}
                    days={days}
                    onNavigate={navigate}
                    onOpenWork={setSelected}
                  />
                ))}
              {tab === "work_orders" && (
                <WorkOrders
                  activities={activities}
                  plant={plant}
                  onOpen={setSelected}
                  onCreate={
                    can("work.create") ? () => setNewWork(true) : undefined
                  }
                />
              )}
              {tab === "audits" && (
                <AuditWorkspace
                  plant={plant}
                  audits={audits}
                  canExecute={can("audit.execute")}
                  onSaved={() => {
                    notify("Assessment saved");
                    refresh();
                  }}
                />
              )}
              {tab === "redtags" && (
                <RedTagsWorkspace
                  plant={plant}
                  tags={tags}
                  canCreate={can("redtag.create")}
                  canDispose={can("redtag.dispose")}
                  onSaved={() => {
                    notify("Red-tag record saved");
                    refresh();
                  }}
                />
              )}
              {tab === "locations" && (
                <LocationsWorkspace
                  plant={plant}
                  canManage={can("location.manage")}
                  onSaved={() => {
                    notify("Zone saved");
                    refresh();
                  }}
                />
              )}
              {tab === "assets" && (
                <Assets
                  key={identity?.id + plant.id}
                  plant={plant}
                  notify={notify}
                  canManage={can("asset.manage")}
                />
              )}
              {tab === "settings" && (
                <PeopleWorkspace
                  plant={plant}
                  people={people}
                  canManage={can("people.manage")}
                  onSaved={() => {
                    notify("Team member saved");
                    refresh();
                  }}
                />
              )}
              {tab === "access" && identity && (
                <AccessPanel identity={identity} identities={identities} />
              )}
              {tab === "reporting" && (
                <>
                  <section className="surface report-summary">
                    <div>
                      <h2>Authorized improvement report</h2>
                      <p>
                        Exports include only records returned for your current
                        role and scope. Individual work orders include a PDF
                        record.
                      </p>
                    </div>
                    <button
                      className="btn"
                      onClick={exportCsv}
                      disabled={!activities.length}
                    >
                      <ArrowDownToLine />
                      Download CSV
                    </button>
                  </section>
                  <Overview
                    plant={plant}
                    activities={activities}
                    audits={audits}
                    redTags={tags}
                    days={days}
                    onNavigate={navigate}
                    onOpenWork={setSelected}
                  />
                </>
              )}
              {tab === "standards" && (
                <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                  {pillars.map((p, i) => (
                    <section className="surface standard-card" key={p.key}>
                      <span className="standard-index">0{i + 1}</span>
                      <h2>{p.name}</h2>
                      <p>
                        {
                          [
                            "Keep only what is needed. Identify unnecessary items and route them through an accountable red-tag process.",
                            "Give everything a designated place. Make identification and return paths clear to every team member.",
                            "Clean to inspect. Detect leaks, wear, and abnormal conditions during daily routines.",
                            "Define what good looks like. Use agreed visual references and consistent work methods.",
                            "Make improvement a habit. Verify actions, audit regularly, and learn from repeated findings.",
                          ][i]
                        }
                      </p>
                      <button
                        className="text-link"
                        onClick={() => navigate("audits")}
                      >
                        View assessment history
                        <ArrowRight />
                      </button>
                    </section>
                  ))}
                </div>
              )}
            </>
          )}
          <footer className="footer">
            <span>EnerTech UPS Pvt. Ltd. · 5S Operations</span>
            <span>
              <ShieldCheck size={12} />
              Role and record scope enforced by API
            </span>
            <button className="text-link" disabled={loading} onClick={refresh}>
              <RefreshCw size={12} />
              Refresh
            </button>
          </footer>
        </main>
      </div>
      {newWork && plant && (
        <NewWork
          plant={plant}
          leaders={leader ? [leader] : people}
          onClose={() => setNewWork(false)}
          onSaved={(work) => {
            setActivities((old) => [work, ...old]);
            notify("Work order created");
          }}
        />
      )}
      {selected && plant && (
        <WorkDetail
          key={identity?.id + selected.id}
          activity={selected}
          plant={plant}
          canReview={
            can("work.review") && selected.assigned_to !== identity?.id
          }
          canExecute={can("work.execute")}
          canComment={can("work.comment")}
          onClose={() => setSelected(null)}
          onUpdate={updateWork}
        />
      )}
      {roleDialog && (
        <RoleSwitcher
          current={identity}
          identities={identities}
          busy={switching}
          error={switchError}
          onSwitch={(id) => void changeRole(id)}
          onClose={() => setRoleDialog(false)}
        />
      )}
      {panel && (
        <Dialog
          title={
            panel === "search"
              ? "Search authorized work"
              : panel === "inbox"
                ? can("work.review")
                  ? "Review inbox"
                  : "My submitted reports"
                : "Workspace information"
          }
          onClose={() => setPanel(null)}
        >
          <div className="dialog-body">
            {panel === "search" ? (
              <>
                <label className="input mb-5">
                  <Search size={16} />
                  <input
                    autoFocus
                    aria-label="Search workspace records"
                    placeholder="Search work-order title or ID…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
                {activities
                  .filter((a) =>
                    `${a.title} ${a.activity_number}`
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  )
                  .slice(0, 10)
                  .map((a) => (
                    <button
                      className="queue-item px-0!"
                      key={a.id}
                      onClick={() => {
                        setPanel(null);
                        setSelected(a);
                      }}
                    >
                      <ClipboardList size={17} />
                      <div>
                        <strong>{a.title}</strong>
                        <p>{a.activity_number}</p>
                      </div>
                      <ArrowRight className="ml-auto" size={15} />
                    </button>
                  ))}
              </>
            ) : panel === "inbox" ? (
              <>
                {review.map((a) => (
                  <button
                    className="queue-item px-0!"
                    key={a.id}
                    onClick={() => {
                      setPanel(null);
                      setSelected(a);
                    }}
                  >
                    <ClipboardCheck size={18} />
                    <div>
                      <strong>{a.title}</strong>
                      <p>{a.assignee_name} · submitted for review</p>
                    </div>
                    <ArrowRight className="ml-auto" size={15} />
                  </button>
                ))}
                {!review.length && (
                  <Empty
                    title="No reports awaiting review"
                    text="Submitted work within your scope appears here."
                  />
                )}
              </>
            ) : (
              <>
                <h3 className="text-lg font-semibold">
                  EnerTech 5S · local evaluation
                </h3>
                <p className="mt-4 text-sm leading-7 text-base-content/65">
                  Your selected account has a server session. Permissions, plant
                  scope, zone scope, ownership, and independent review are
                  checked by the API.
                </p>
                <div className="access-notice mt-5">
                  <ShieldCheck size={20} />
                  <p>
                    Sample role switching is available only in local-preview
                    mode. Production identity-provider onboarding, managed
                    PostgreSQL, private media storage, and native offline
                    applications remain separate release work.
                  </p>
                </div>
                <button
                  className="btn mt-5"
                  onClick={() => {
                    setPanel(null);
                    navigate("access");
                  }}
                >
                  Inspect my access
                  <ArrowRight />
                </button>
              </>
            )}
          </div>
        </Dialog>
      )}
      {toast && (
        <div className="toast-message" role="status">
          <ShieldCheck size={17} />
          {toast}
        </div>
      )}
    </div>
  );
}
