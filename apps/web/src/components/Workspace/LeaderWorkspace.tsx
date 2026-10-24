import {
  ArrowRight,
  ArrowUpRight,
  Camera,
  CheckCheck,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  MapPin,
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
  onCreate,
}: {
  leader: ZonalLeader;
  plant: Plant;
  activities: Activity[];
  audits: AuditRun[];
  redTags: RedTag[];
  onOpen: (activity: Activity) => void;
  onNavigate: (tab: string) => void;
  onCreate: () => void;
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
  const department = plant.departments.find((d) =>
    d.zones.some((z) => z.id === zone?.id),
  );
  return (
    <>
      <section className="leader-welcome">
        <div>
          <div className="eyebrow">YOUR ZONE. YOUR IMPACT.</div>
          <h2>
            Good{" "}
            {new Date(now).getHours() < 12
              ? "morning"
              : new Date(now).getHours() < 17
                ? "afternoon"
                : "evening"}
            , {leader.first_name}.
          </h2>
          <p>
            You have{" "}
            <strong>
              {open.length} open {open.length === 1 ? "action" : "actions"}
            </strong>{" "}
            to move forward. Let’s make your zone a little better today.
          </p>
          <div className="leader-location">
            <MapPin size={14} />
            <span>{zone?.name || "No zone assigned"}</span>
            <span className="opacity-40">/</span>
            <span>{department?.name || plant.code}</span>
          </div>
        </div>
        <div className="leader-identity">
          <span className="initials">
            {leader.first_name[0]}
            {leader.last_name[0]}
          </span>
          <div>
            <strong>
              {leader.first_name} {leader.last_name}
            </strong>
            <small>Zonal leader · {zone?.code || "Unassigned"}</small>
          </div>
        </div>
      </section>
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
                <p>Start work, capture the change, and send it for review.</p>
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
                <p>Follow the review without chasing an update.</p>
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
                No reports waiting for review. Submit a completed action with
                after evidence to start the review.
              </div>
            )}
          </section>
        </div>
        <div className="stack">
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>From task to verified improvement</h2>
                <p>Your everyday 5S workflow.</p>
              </div>
            </div>
            <div className="px-5 pb-6">
              {[
                {
                  icon: ClipboardList,
                  title: "Understand the action",
                  text: "Check the observation, location, and expected result.",
                },
                {
                  icon: Camera,
                  title: "Show the improvement",
                  text: "Capture before and after photos. Explain what changed.",
                },
                {
                  icon: ClipboardCheck,
                  title: "Submit for verification",
                  text: "Your supervisor approves or requests changes.",
                },
              ].map((step, i) => (
                <div key={step.title} className="mb-5 flex gap-3 last:mb-0">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-success/8 text-success">
                    <step.icon size={16} />
                  </span>
                  <div>
                    <strong className="text-[11px] font-medium">
                      <span className="mr-1 text-base-content/40">
                        0{i + 1}
                      </span>{" "}
                      {step.title}
                    </strong>
                    <p className="mt-1 text-[10px] leading-relaxed text-base-content/55">
                      {step.text}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>My zone’s red tags</h2>
                <p>Keep the unnecessary from becoming permanent.</p>
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
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>Spot an opportunity?</h2>
                <p>A better workplace begins with an observation.</p>
              </div>
            </div>
            <div className="px-5 pb-5">
              <button className="btn w-full" onClick={onCreate}>
                Raise a 5S action <ArrowRight />
              </button>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
