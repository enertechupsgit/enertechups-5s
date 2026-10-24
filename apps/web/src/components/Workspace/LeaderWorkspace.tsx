import {
  ArrowRight,
  ArrowUpRight,
  CheckCheck,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  Target,
  Tag,
} from "lucide-react";
import type {
  Activity,
  AuditRun,
  Plant,
  RedTag,
  ZonalLeader,
} from "../../types";
import { Empty, Status } from "./Shared";
import { dateLabel, isComplete, useNow } from "./utils";

export function LeaderWorkspace({
  leader,
  plant,
  activities,
  audits,
  redTags,
  onOpen,
  onNavigate,
}: {
  leader: ZonalLeader;
  plant: Plant;
  activities: Activity[];
  audits: AuditRun[];
  redTags: RedTag[];
  onOpen: (activity: Activity) => void;
  onNavigate: (tab: string) => void;
}) {
  const now = useNow();
  const zone = plant.departments
    .flatMap((d) => d.zones)
    .find((z) => z.id === leader.assigned_zone_id);
  const assigned = activities.filter((a) => a.assigned_to === leader.id);
  const open = assigned.filter(
    (a) => !isComplete(a.status) && a.status !== "submitted_for_review",
  );
  const waiting = assigned.filter((a) => a.status === "submitted_for_review");
  const completed = assigned.filter((a) => isComplete(a.status));
  const latest = audits
    .filter((a) => a.zone_id === zone?.id)
    .sort((a, b) => Date.parse(b.conducted_at) - Date.parse(a.conducted_at))[0];
  const zoneTags = redTags.filter(
    (t) => t.zone_id === zone?.id && !t.is_closed,
  );
  const prioritized = [...open].sort(
    (a, b) =>
      (a.due_date ? Date.parse(a.due_date) : Infinity) -
      (b.due_date ? Date.parse(b.due_date) : Infinity),
  );
  return (
    <>
      <div className="metric-grid">
        {[
          {
            name: "My open actions",
            number: String(open.length).padStart(2, "0"),
            suffix: "",
            icon: ClipboardList,
            note: `${open.filter((a) => a.due_date && Date.parse(a.due_date) < now).length} overdue · ordered by due date`,
            tone: "caution",
          },
          {
            name: "Awaiting review",
            number: String(waiting.length).padStart(2, "0"),
            suffix: "",
            icon: Clock3,
            note: "Submitted to your supervisor",
            tone: "",
          },
          {
            name: "Verified & completed",
            number: String(completed.length).padStart(2, "0"),
            suffix: "",
            icon: CheckCheck,
            note: "Improvements approved and closed",
            tone: "positive",
          },
          {
            name: "My zone’s 5S score",
            number: latest ? String(latest.score_percentage) : "—",
            suffix: latest ? "%" : "",
            icon: Target,
            note: latest
              ? `Last assessed ${dateLabel(latest.conducted_at)}`
              : "No assessment recorded yet",
            tone: "positive",
          },
        ].map((m) => (
          <div className="surface metric" key={m.name}>
            <div className="metric-top">
              <span>{m.name}</span>
              <span className="metric-icon">
                <m.icon size={15} />
              </span>
            </div>
            <div className="metric-value">
              {m.number}
              <small>{m.suffix}</small>
            </div>
            <div className={`metric-note ${m.tone}`}>
              <i className="status-dot" />
              {m.note}
            </div>
          </div>
        ))}
      </div>
      <div className="dashboard-grid">
        <div className="stack">
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>My next actions</h2>
              </div>
              <button
                className="text-link"
                onClick={() => onNavigate("work_orders")}
              >
                All my work <ArrowUpRight />
              </button>
            </div>
            {prioritized.map((a) => (
              <div key={a.id} className="leader-task">
                <div className="leader-task-number">
                  <ClipboardList size={17} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span className="work-id mb-0!">{a.activity_number}</span>
                    <span
                      className={`text-[9px] capitalize ${a.priority === "high" || a.priority === "critical" ? "text-error" : "text-base-content/50"}`}
                    >
                      {a.priority} priority
                    </span>
                  </div>
                  <button className="work-title" onClick={() => onOpen(a)}>
                    {a.title}
                  </button>
                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <Status value={a.status} />
                    <span className="text-[10px] text-base-content/55">
                      Due {dateLabel(a.due_date)}
                    </span>
                  </div>
                  {a.rejection_reason && (
                    <p className="mt-3 rounded-md bg-error/5 px-3 py-2 text-[11px] text-error">
                      Supervisor feedback: {a.rejection_reason}
                    </p>
                  )}
                </div>
                <button className="btn shrink-0" onClick={() => onOpen(a)}>
                  {a.status === "in_progress"
                    ? "Continue"
                    : a.status === "rejected"
                      ? "Update report"
                      : "View task"}
                  <ArrowRight />
                </button>
              </div>
            ))}
            {!prioritized.length && (
              <Empty
                title="A clear list. A good start."
                text="Your assigned actions will appear here as your team plans the next improvements."
              />
            )}
          </section>
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>My submitted reports</h2>
              </div>
              <span className="badge badge-ghost">{waiting.length}</span>
            </div>
            {waiting.length ? (
              waiting.map((a) => (
                <button
                  className="queue-item"
                  key={a.id}
                  onClick={() => onOpen(a)}
                >
                  <span className="queue-icon">
                    <ClipboardCheck size={16} />
                  </span>
                  <div className="flex-1">
                    <strong>{a.title}</strong>
                    <p>
                      Submitted {dateLabel(a.submitted_at)} · supervisor review
                      pending
                    </p>
                  </div>
                  <ArrowUpRight size={15} />
                </button>
              ))
            ) : (
              <div className="px-5 pb-6 pt-2 text-xs text-base-content/55">
                No reports awaiting review.
              </div>
            )}
          </section>
        </div>
        <div className="stack">
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>My zone’s red tags</h2>
              </div>
              <Tag size={17} className="text-warning" />
            </div>
            <div className="px-5 pb-5">
              <span className="text-3xl font-semibold tracking-tight">
                {zoneTags.length}
              </span>
              <span className="ml-2 text-[11px] text-base-content/55">
                items awaiting disposition
              </span>
              {zoneTags.slice(0, 3).map((tag) => (
                <div
                  className="mt-4 flex items-center justify-between text-xs"
                  key={tag.id}
                >
                  <span>{tag.item_name}</span>
                  <span className="text-[10px] text-base-content/45">
                    {tag.aging_days} days
                  </span>
                </div>
              ))}
              <button
                className="text-link mt-5"
                onClick={() => onNavigate("redtags")}
              >
                Open my zone register <ArrowRight />
              </button>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
