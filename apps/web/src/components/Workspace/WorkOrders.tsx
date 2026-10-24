import { useEffect, useState } from "react";
import {
  Search,
  ArrowUpRight,
  LayoutList,
  LayoutGrid,
  Clock3,
  MapPin,
  Play,
  Check,
  Send,
  MessageSquare,
  ArrowDownToLine,
  History,
  X,
  SlidersHorizontal,
} from "lucide-react";
import type { Activity, Plant, ZonalLeader } from "../../types";
import {
  addActivityComment,
  fetchActivity,
  createActivity,
  getActivityPdfDownloadUrl,
  reviewActivityReport,
  startActivity,
  submitActivityReport,
} from "../../api/client";
import { Dialog, Empty, EvidenceInput, Status } from "./Shared";
import {
  dateTimeLabel,
  timestamp,
  dateLabel,
  isComplete,
  pillars,
  useNow,
} from "./utils";

export function WorkOrders({
  activities,
  plant,
  onOpen,
  onCreate,
}: {
  activities: Activity[];
  plant: Plant;
  onOpen: (activity: Activity) => void;
  onCreate?: () => void;
}) {
  const now = useNow();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [zone, setZone] = useState("all");
  const [grid, setGrid] = useState(false);
  const [phone, setPhone] = useState(
    () => window.matchMedia("(max-width: 760px)").matches,
  );
  const [filtersOpen, setFiltersOpen] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const update = () => setPhone(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const zones = plant.departments.flatMap((d) => d.zones);
  const filtered = activities.filter(
    (a) =>
      `${a.title} ${a.activity_number} ${a.assignee_name || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (zone === "all" || a.zone_id === zone) &&
      (status === "all" ||
        (status === "open"
          ? !isComplete(a.status)
          : status === "completed"
            ? isComplete(a.status)
            : a.status === status)),
  );
  return (
    <section className="surface work-register">
      <div className={`filterbar ${filtersOpen ? "filters-open" : ""}`}>
        <label className="input">
          <Search size={15} />
          <input
            aria-label="Search work orders"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={
              phone ? "Search work…" : "Search title, ID or assignee…"
            }
          />
        </label>
        <button
          className="btn btn-square mobile-filter-toggle"
          aria-label="Show work filters"
          aria-expanded={filtersOpen}
          aria-controls="work-status-filter work-zone-filter"
          onClick={() => setFiltersOpen(!filtersOpen)}
        >
          <SlidersHorizontal size={18} />
          {(status !== "all" || zone !== "all") && (
            <span className="filter-active-dot" />
          )}
        </button>
        <select
          id="work-status-filter"
          className="select work-filter"
          aria-label="Filter work order status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="open">Open work</option>
          <option value="in_progress">In progress</option>
          <option value="submitted_for_review">Needs review</option>
          <option value="completed">Completed</option>
        </select>
        <select
          id="work-zone-filter"
          className="select work-filter"
          aria-label="Filter by zone"
          value={zone}
          onChange={(e) => setZone(e.target.value)}
        >
          <option value="all">All zones</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </select>
        <span
          className="work-count ml-auto text-[10px] text-base-content/50"
          aria-live="polite"
        >
          {filtered.length} work orders
        </span>
        <div className="work-view-toggle flex gap-1">
          <button
            className={`btn btn-square ${!grid ? "" : "btn-ghost"}`}
            aria-label="List view"
            aria-pressed={!grid}
            onClick={() => setGrid(false)}
          >
            <LayoutList />
          </button>
          <button
            className={`btn btn-square ${grid ? "" : "btn-ghost"}`}
            aria-label="Card view"
            aria-pressed={grid}
            onClick={() => setGrid(true)}
          >
            <LayoutGrid />
          </button>
        </div>
      </div>
      {!filtered.length ? (
        <Empty
          title={
            search ? "No matching work orders" : "Make room for improvement"
          }
          text={
            search
              ? "Try another search or change your filters."
              : "Create a work order to turn an observation into an owned action."
          }
          action={
            onCreate ? (
              <button className="btn" onClick={onCreate}>
                Create work order
              </button>
            ) : undefined
          }
        />
      ) : grid || phone ? (
        <div className="work-grid">
          {filtered.map((a) => (
            <button
              className="card surface work-card"
              key={a.id}
              onClick={() => onOpen(a)}
            >
              <div className="flex w-full items-center justify-between">
                <span className="work-id">{a.activity_number}</span>
                <ArrowUpRight size={14} />
              </div>
              <h3>{a.title}</h3>
              <Status value={a.status} />
              <div className="work-card-location">
                <MapPin size={13} />
                {zones.find((z) => z.id === a.zone_id)?.name || "Assigned zone"}
                <span>{a.priority}</span>
              </div>
              <div className="flex w-full items-center justify-between border-t border-base-300 pt-3 text-[10px] text-base-content/60">
                <span>{a.assignee_name || "Unassigned"}</span>
                <span>{dateLabel(a.due_date)}</span>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Work order</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Zone</th>
                <th>Assignee</th>
                <th>Due date</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => (
                <tr key={a.id}>
                  <td className="min-w-[240px]">
                    <div className="work-id">{a.activity_number}</div>
                    <button className="work-title" onClick={() => onOpen(a)}>
                      {a.title}
                    </button>
                    <div className="mt-1 text-[9px] text-base-content/50">
                      {pillars.find((p) => p.key === a.category)?.label}
                    </div>
                  </td>
                  <td>
                    <Status value={a.status} />
                  </td>
                  <td>
                    <span
                      className={`flex items-center gap-1.5 capitalize ${["high", "critical"].includes(a.priority) ? "text-error" : "text-base-content/60"}`}
                    >
                      <i className="status-dot" />
                      {a.priority}
                    </span>
                  </td>
                  <td className="text-base-content/65">
                    {zones.find((z) => z.id === a.zone_id)?.name ||
                      "Unassigned"}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <span className="initials h-6! w-6! text-[9px]!">
                        {(a.assignee_name || "?")
                          .split(" ")
                          .map((x) => x[0])
                          .slice(0, 2)
                          .join("")}
                      </span>
                      <span className="whitespace-nowrap">
                        {a.assignee_name || "Unassigned"}
                      </span>
                    </div>
                  </td>
                  <td
                    className={`whitespace-nowrap ${a.due_date && timestamp(a.due_date) < now && !isComplete(a.status) ? "text-error" : "text-base-content/60"}`}
                  >
                    {dateLabel(a.due_date)}
                  </td>
                  <td>
                    <button
                      className="btn btn-ghost btn-square"
                      aria-label={`Open ${a.title}`}
                      onClick={() => onOpen(a)}
                    >
                      <ArrowUpRight />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function NewWork({
  plant,
  leaders,
  onClose,
  onSaved,
}: {
  plant: Plant;
  leaders: ZonalLeader[];
  onClose: () => void;
  onSaved: (work: Activity) => void;
}) {
  const zones = plant.departments.flatMap((d) => d.zones);
  const [photo, setPhoto] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedZone, setSelectedZone] = useState(zones[0]?.id || "");
  const [assignee, setAssignee] = useState(
    leaders.length === 1 ? leaders[0].id : "",
  );
  const [error, setError] = useState("");
  return (
    <Dialog title="Create work order" onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const form = new FormData(e.currentTarget);
          setSaving(true);
          setError("");
          try {
            const work = await createActivity({
              plant_id: plant.id,
              zone_id: String(form.get("zone")),
              title: String(form.get("title")).trim(),
              problem_description: String(form.get("description")).trim(),
              category: String(form.get("pillar")) as Activity["category"],
              priority: String(form.get("priority")) as Activity["priority"],
              assigned_to: String(form.get("assignee")) || null,
              due_date: form.get("due")
                ? new Date(`${form.get("due")}T17:00:00`).toISOString()
                : null,
              initial_before_photo_url: photo || undefined,
            });
            onSaved(work);
            onClose();
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setSaving(false);
          }
        }}
      >
        <div className="dialog-body">
          {error && (
            <div role="alert" className="form-error">
              {error}
            </div>
          )}
          <label>
            Work order title
            <input
              className="input"
              name="title"
              required
              maxLength={255}
              placeholder="What needs to improve?"
            />
          </label>
          <label>
            Observation / problem
            <textarea
              className="textarea"
              name="description"
              required
              rows={3}
              placeholder="Describe the current condition and the expected standard."
            />
          </label>
          <div className="dialog-fields">
            <label>
              Location
              <select
                className="select"
                name="zone"
                required
                value={selectedZone}
                onChange={(event) => {
                  setSelectedZone(event.target.value);
                  setAssignee("");
                }}
              >
                <option value="" disabled>
                  Select a zone
                </option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              5S pillar
              <select className="select" name="pillar">
                {pillars.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Assignee
              <select
                className="select"
                name="assignee"
                value={assignee}
                onChange={(event) => setAssignee(event.target.value)}
              >
                <option value="">Unassigned</option>
                {leaders
                  .filter(
                    (l) =>
                      l.is_active &&
                      ([
                        "supervisor",
                        "admin",
                        "plant_manager",
                        "super_admin",
                      ].includes(l.role) ||
                        (["zonal_leader", "operator"].includes(l.role) &&
                          l.assigned_zone_id === selectedZone)),
                  )
                  .map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.first_name} {l.last_name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Priority
              <select className="select" name="priority" defaultValue="medium">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
            <label>
              Due date
              <input className="input" type="date" name="due" />
            </label>
          </div>
          <EvidenceInput
            value={photo}
            onChange={setPhoto}
            label="Before photo (optional)"
            onPendingChange={setUploading}
          />
          {!zones.length && (
            <p className="form-error">
              Add a zone under Locations before creating a work order.
            </p>
          )}
        </div>
        <div className="dialog-foot">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            disabled={saving || uploading || !zones.length}
          >
            {saving ? "Saving…" : "Create work order"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export function WorkDetail({
  activity,
  plant,
  onClose,
  onUpdate,
  canReview = false,
  canExecute = false,
  canComment = false,
}: {
  canReview?: boolean;
  canExecute?: boolean;
  canComment?: boolean;
  activity: Activity;
  plant: Plant;
  onClose: () => void;
  onUpdate: (a: Activity) => void;
}) {
  const [tab, setTab] = useState("details");
  const [action, setAction] = useState<"submit" | "reject" | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [photo, setPhoto] = useState("");
  const [comment, setComment] = useState("");
  const [commentPhoto, setCommentPhoto] = useState("");
  const [beforePhoto, setBeforePhoto] = useState("");
  const [uploads, setUploads] = useState<Record<string, boolean>>({});
  const uploading = Object.values(uploads).some(Boolean);
  const zone = plant.departments
    .flatMap((d) => d.zones)
    .find((z) => z.id === activity.zone_id);
  const run = async (fn: () => Promise<Activity>) => {
    setBusy(true);
    setError("");
    try {
      onUpdate(await fn());
      setAction(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog title={activity.activity_number} onClose={onClose} wide>
      <div className="dialog-body">
        <div className="mb-4 flex items-center gap-2">
          <Status value={activity.status} />
          <span className="text-[10px] text-base-content/50">
            {pillars.find((p) => p.key === activity.category)?.label}
          </span>
        </div>
        <h2>{activity.title}</h2>
        <div className="mt-4 flex flex-wrap gap-5 text-[11px] text-base-content/60">
          <span className="flex items-center gap-1.5">
            <MapPin size={13} />
            {zone?.name || "No zone"}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock3 size={13} />
            {activity.due_date
              ? `Due ${dateLabel(activity.due_date)}`
              : "No due date"}
          </span>
          <span>{activity.assignee_name || "Unassigned"}</span>
        </div>
        <div className="subnav mt-7">
          {["details", "comments", "history"].map((t) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => {
                setTab(t);
                setAction(null);
                setError("");
              }}
            >
              {t === "details"
                ? "Overview & evidence"
                : t === "comments"
                  ? `Comments (${activity.comments.length})`
                  : "Activity history"}
            </button>
          ))}
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        {tab === "details" && (
          <>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-base-content/55">
              Observation
            </p>
            <p className="text-[13px] leading-relaxed whitespace-pre-wrap break-words">
              {activity.problem_description}
            </p>
            {activity.corrective_action && (
              <>
                <p className="mb-2 mt-6 text-[10px] font-semibold uppercase tracking-wider text-base-content/55">
                  Corrective action
                </p>
                <p className="text-[13px] leading-relaxed whitespace-pre-wrap break-words">
                  {activity.corrective_action}
                </p>
              </>
            )}
            {activity.outcome_description && (
              <>
                <p className="mb-2 mt-6 text-[10px] font-semibold uppercase tracking-wider text-base-content/55">
                  Outcome
                </p>
                <p className="text-[13px] leading-relaxed whitespace-pre-wrap break-words">
                  {activity.outcome_description}
                </p>
              </>
            )}
            {activity.rejection_reason && (
              <div className="form-error">
                Changes requested: {activity.rejection_reason}
              </div>
            )}
            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {["before_photo", "after_photo"].map((kind) => {
                const evidence = activity.evidence
                  .filter((e) => e.media_type === kind)
                  .at(-1);
                return (
                  <div
                    className="overflow-hidden rounded-lg border border-base-300"
                    key={kind}
                  >
                    <div className="border-b border-base-300 bg-base-200 px-3 py-2 text-[10px] font-medium">
                      {kind === "before_photo" ? "BEFORE" : "AFTER"}
                    </div>
                    {evidence ? (
                      <img
                        className="h-56 w-full object-contain bg-base-200"
                        src={evidence.file_url}
                        alt={`${kind === "before_photo" ? "Before" : "After"} evidence for ${activity.title}`}
                      />
                    ) : (
                      <div className="flex h-32 items-center justify-center text-[11px] text-base-content/40">
                        No photo attached
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
        {tab === "history" && (
          <div>
            {activity.history.map((h) => (
              <div key={h.id} className="timeline-row">
                <History size={16} className="mt-1 shrink-0 text-success" />
                <div>
                  <strong className="font-medium">
                    {h.action_note || h.to_status.replaceAll("_", " ")}
                  </strong>
                  <p>
                    {h.actor_name || "System"} · {dateTimeLabel(h.created_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
        {tab === "comments" && (
          <div>
            {!activity.comments.length && (
              <p className="text-sm text-base-content/60">No comments yet.</p>
            )}
            {activity.comments.map((c) => (
              <div
                key={c.id}
                className="mb-4 rounded-lg border border-base-300 p-4"
              >
                <p className="text-[11px] font-medium">
                  {c.author_name}
                  <span className="ml-3 font-normal text-base-content/45">
                    {dateLabel(c.created_at)}
                  </span>
                </p>
                <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {c.comment}
                </p>
                {c.attachments?.map((image, index) => (
                  <img
                    key={index}
                    src={image}
                    className="mt-3 max-h-64 w-full object-contain rounded-lg"
                    alt={`Comment photo ${index + 1}`}
                  />
                ))}
              </div>
            ))}
            {canComment && (
              <form
                className="mt-4 space-y-3"
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!comment.trim() || busy || uploading) return;
                  setBusy(true);
                  setError("");
                  try {
                    await addActivityComment(
                      activity.id,
                      comment.trim(),
                      commentPhoto ? [commentPhoto] : [],
                    );
                    onUpdate(await fetchActivity(activity.id));
                    setComment("");
                    setCommentPhoto("");
                  } catch (err) {
                    setError((err as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <label
                  htmlFor="work-comment"
                  className="block text-sm font-medium"
                >
                  Comment
                </label>
                <textarea
                  id="work-comment"
                  className="textarea w-full"
                  aria-label="Comment"
                  rows={3}
                  maxLength={5000}
                  disabled={busy}
                  placeholder="Add a comment for your team…"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  required
                />
                <EvidenceInput
                  value={commentPhoto}
                  onChange={setCommentPhoto}
                  label="Comment photo (optional)"
                  onPendingChange={(pending) =>
                    setUploads((old) => ({ ...old, comment: pending }))
                  }
                />
                <button
                  className="btn"
                  disabled={busy || uploading || !comment.trim()}
                >
                  <MessageSquare />
                  {busy ? "Posting…" : "Post comment"}
                </button>
              </form>
            )}
          </div>
        )}
        {action === "submit" && (
          <form
            className="mt-6 border-t border-base-300 pt-6"
            onSubmit={(e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              if (!photo) {
                setError("Attach an after photo before submitting.");
                return;
              }
              void run(() =>
                submitActivityReport({
                  activity_id: activity.id,
                  corrective_action: String(form.get("correction")),
                  outcome_description: String(form.get("outcome")),
                  after_photo_url: photo,
                  before_photo_url: beforePhoto || undefined,
                }),
              );
            }}
          >
            <label>
              What did you change?
              <textarea
                className="textarea"
                name="correction"
                required
                rows={3}
                defaultValue={activity.corrective_action || ""}
              />
            </label>
            <label>
              Outcome
              <input
                className="input"
                name="outcome"
                placeholder="Describe the result"
              />
            </label>
            <EvidenceInput
              value={beforePhoto}
              onChange={setBeforePhoto}
              label="Before photo (optional)"
              onPendingChange={(pending) =>
                setUploads((old) => ({ ...old, before: pending }))
              }
            />
            <EvidenceInput
              value={photo}
              onChange={setPhoto}
              label="After photo"
              onPendingChange={(pending) =>
                setUploads((old) => ({ ...old, after: pending }))
              }
            />
            <div className="mt-4 flex gap-2">
              <button
                className="btn btn-primary"
                disabled={busy || uploading || !photo}
              >
                Submit for review
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => setAction(null)}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
        {action === "reject" && (
          <form
            className="mt-6 border-t border-base-300 pt-6"
            onSubmit={(e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              void run(() =>
                reviewActivityReport(activity.id, {
                  decision: "reject",
                  rejection_reason: String(form.get("reason")),
                }),
              );
            }}
          >
            <label>
              What needs to change?
              <textarea className="textarea" name="reason" required rows={3} />
            </label>
            <div className="flex gap-2">
              <button className="btn" disabled={busy}>
                Request changes
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setAction(null)}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
      <div className="dialog-foot flex-wrap">
        <a
          className="btn mr-auto"
          href={getActivityPdfDownloadUrl(activity.id)}
          target="_blank"
          rel="noreferrer"
        >
          <ArrowDownToLine />
          PDF
        </a>
        {!action && (
          <>
            {canExecute &&
              ["draft", "assigned", "rejected"].includes(activity.status) && (
                <button
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => void run(() => startActivity(activity.id))}
                >
                  <Play />
                  Start work
                </button>
              )}
            {canExecute && activity.status === "in_progress" && (
              <button
                className="btn btn-primary"
                onClick={() => setAction("submit")}
              >
                <Send />
                Submit report
              </button>
            )}
            {canReview && activity.status === "submitted_for_review" && (
              <>
                <button className="btn" onClick={() => setAction("reject")}>
                  <X />
                  Request changes
                </button>
                <button
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() =>
                    void run(() =>
                      reviewActivityReport(activity.id, {
                        decision: "approve",
                      }),
                    )
                  }
                >
                  <Check />
                  Approve & close
                </button>
              </>
            )}
          </>
        )}
        <button className="btn" onClick={onClose}>
          Close
        </button>
      </div>
    </Dialog>
  );
}
