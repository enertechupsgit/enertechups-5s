import {
  ArrowUpRight,
  ArrowRight,
  ClipboardList,
  ClipboardCheck,
  Tag,
  MapPin,
  CircleCheck,
  Clock3,
  Target,
  ShieldCheck,
  TrendingUp,
  ChevronRight,
} from "lucide-react";
import type { Activity, AuditRun, Plant, RedTag } from "../../types";
import { Empty } from "./Shared";
import { timestamp, dateLabel, isComplete, pillars, useNow } from "./utils";

interface Props {
  plant: Plant;
  activities: Activity[];
  audits: AuditRun[];
  redTags: RedTag[];
  days: number;
  onNavigate: (tab: string) => void;
  onOpenWork: (activity: Activity) => void;
}
export function Overview({
  plant,
  activities,
  audits,
  redTags,
  days,
  onNavigate,
  onOpenWork,
}: Props) {
  const now = useNow();
  const cutoff = now - days * 86400000;
  const periodAudits = audits
    .filter((a) => new Date(a.conducted_at).getTime() >= cutoff)
    .sort((a, b) => timestamp(a.conducted_at) - timestamp(b.conducted_at));
  const average = periodAudits.length
    ? periodAudits.reduce((sum, a) => sum + a.score_percentage, 0) /
      periodAudits.length
    : null;
  const open = activities.filter((a) => !isComplete(a.status));
  const overdue = open.filter((a) => a.due_date && timestamp(a.due_date) < now);
  const review = activities.filter((a) => a.status === "submitted_for_review");
  const zones = plant.departments.flatMap((d) =>
    d.zones.map((z) => ({ ...z, department: d.name })),
  );
  const queue = [
    ...review,
    ...overdue.filter((a) => !review.some((r) => r.id === a.id)),
  ].slice(0, 3);
  const metrics = [
    {
      title: "Average 5S score",
      value: average === null ? "—" : average.toFixed(1),
      suffix: average === null ? "" : "%",
      note: `${periodAudits.length} audits in selected period`,
      icon: Target,
      tone: "positive",
    },
    {
      title: "Open work orders",
      value: String(open.length).padStart(2, "0"),
      note: `${overdue.length} overdue · ${review.length} awaiting review`,
      icon: ClipboardList,
      tone: overdue.length ? "caution" : "",
    },
    {
      title: "Open red tags",
      value: String(redTags.filter((t) => !t.is_closed).length).padStart(
        2,
        "0",
      ),
      note: `${redTags.filter((t) => t.is_closed).length} dispositions completed`,
      icon: Tag,
      tone: "",
    },
    {
      title: "Zones assessed",
      value: String(new Set(periodAudits.map((a) => a.zone_id)).size).padStart(
        2,
        "0",
      ),
      suffix: `/ ${zones.length}`,
      note: `Across ${plant.departments.length} departments`,
      icon: MapPin,
      tone: "",
    },
  ];
  const grouped = new Map<string, { total: number; count: number }>();
  for (const audit of periodAudits) {
    const day = new Date(
      audit.conducted_at.endsWith("Z") ||
        /[+-]\d{2}:\d{2}$/.test(audit.conducted_at)
        ? audit.conducted_at
        : audit.conducted_at + "Z",
    ).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
    const bucket = grouped.get(day) || { total: 0, count: 0 };
    bucket.total += audit.score_percentage;
    bucket.count += 1;
    grouped.set(day, bucket);
  }
  const recent = [...grouped.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-8)
    .map(([day, bucket]) => ({
      id: day,
      conducted_at: day + "T12:00:00Z",
      score_percentage: Math.round((bucket.total / bucket.count) * 10) / 10,
      zone_name: `Daily mean · ${bucket.count} assessments`,
    }));
  const firstTime = recent.length ? timestamp(recent[0].conducted_at) : 0;
  const span =
    recent.length > 1
      ? timestamp(recent[recent.length - 1].conducted_at) - firstTime
      : 1;
  const points = recent.map((a) => [
    45 + ((timestamp(a.conducted_at) - firstTime) / span) * 505,
    165 - (a.score_percentage / 100) * 140,
  ]);
  const path = points.map(([x, y], i) => `${i ? "L" : "M"}${x},${y}`).join(" ");
  return (
    <>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <div key={metric.title} className="surface metric">
            <div className="metric-top">
              <span>{metric.title}</span>
              <span className="metric-icon">
                <metric.icon size={15} />
              </span>
            </div>
            <div className="metric-value">
              {metric.value}
              <small>{metric.suffix}</small>
            </div>
            <div className={`metric-note ${metric.tone}`}>
              <span className="status-dot" />
              {metric.note}
            </div>
          </div>
        ))}
      </div>
      <div className="dashboard-grid">
        <div className="stack">
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>5S performance over time</h2>
              </div>
              <span className="chart-legend">
                <i className="status-dot positive" />
                Daily mean
              </span>
            </div>
            {recent.length ? (
              <div className="chart-area">
                <svg
                  viewBox="0 0 580 205"
                  role="img"
                  aria-label={`Last ${recent.length} audit scores: ${recent.map((a) => a.score_percentage + "%").join(", ")}`}
                >
                  <defs>
                    <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#637bd4" stopOpacity=".2" />
                      <stop offset="100%" stopColor="#637bd4" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  {[0, 25, 50, 75, 100].map((n) => (
                    <g key={n}>
                      <line
                        className="chart-grid"
                        x1="35"
                        x2="560"
                        y1={165 - n * 1.4}
                        y2={165 - n * 1.4}
                      />
                      <text x="0" y={169 - n * 1.4}>
                        {n}%
                      </text>
                    </g>
                  ))}
                  <path
                    d={`${path} L${points.at(-1)?.[0]},165 L45,165 Z`}
                    fill="url(#chart-fill)"
                  />
                  <path
                    d={path}
                    fill="none"
                    stroke="#1d359d"
                    strokeWidth="2.5"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                  {points.map(([x, y], i) => (
                    <g key={recent[i].id}>
                      <circle
                        cx={x}
                        cy={y}
                        r="3.5"
                        fill="white"
                        stroke="#1d359d"
                        strokeWidth="2"
                      />
                      <text x={x} y="191" textAnchor="middle">
                        {dateLabel(recent[i].conducted_at)}
                      </text>
                      <title>
                        {recent[i].zone_name}: {recent[i].score_percentage}%
                      </title>
                    </g>
                  ))}
                </svg>
              </div>
            ) : (
              <Empty
                title="Your progress starts here"
                text="Run your first audit to start building a real performance history."
                action={
                  <button className="btn" onClick={() => onNavigate("audits")}>
                    Run an audit <ArrowRight />
                  </button>
                }
              />
            )}
            <div className="chart-summary">
              <TrendingUp size={13} />
              <span>
                {recent.length > 1
                  ? `${recent.length} recorded days · daily average across assessed zones (IST)`
                  : "No assessments yet."}
              </span>
            </div>
          </section>
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>Zone performance</h2>
              </div>
              <button
                className="text-link"
                onClick={() => onNavigate("locations")}
              >
                All locations <ArrowUpRight />
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="table mobile-records">
                <thead>
                  <tr>
                    <th>Zone / workstation</th>
                    <th>Latest score</th>
                    <th>Open work</th>
                    <th>Last audit</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {zones.slice(0, 5).map((zone) => {
                    const audit = audits
                      .filter((a) => a.zone_id === zone.id)
                      .sort(
                        (a, b) =>
                          timestamp(b.conducted_at) - timestamp(a.conducted_at),
                      )[0];
                    return (
                      <tr key={zone.id}>
                        <td data-label="Zone / workstation">
                          <div className="zone-name">
                            <span className="zone-code">
                              {zone.code.slice(0, 2)}
                            </span>
                            <div>
                              {zone.name}
                              <p className="mt-1 text-[9px] font-normal text-base-content/50">
                                {zone.department}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td data-label="Latest score">
                          {audit ? (
                            <div className="score-cell">
                              <span>{audit.score_percentage}%</span>
                              <span className="mini-track">
                                <div
                                  style={{
                                    width: `${Math.min(100, audit.score_percentage)}%`,
                                  }}
                                />
                              </span>
                            </div>
                          ) : (
                            <span className="text-base-content/40">
                              Unassessed
                            </span>
                          )}
                        </td>
                        <td data-label="Open work">
                          {open.filter((a) => a.zone_id === zone.id).length}
                        </td>
                        <td
                          data-label="Last audit"
                          className="text-base-content/60"
                        >
                          {audit ? dateLabel(audit.conducted_at) : "—"}
                        </td>
                        <td data-label="Open zone">
                          <button
                            className="btn btn-ghost btn-square"
                            aria-label={`View ${zone.name}`}
                            onClick={() => onNavigate("locations")}
                          >
                            <ChevronRight />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!zones.length && (
              <Empty
                title="Give every area an owner"
                text="Add your first department and zone to organize work across your plant."
              />
            )}
          </section>
        </div>
        <div className="stack">
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>Performance by pillar</h2>
              </div>
              <span className="metric-icon">
                <ClipboardCheck size={15} />
              </span>
            </div>
            <div className="pillars">
              {pillars.map((pillar, i) => {
                const score = periodAudits.length
                  ? Math.round(
                      periodAudits.reduce(
                        (sum, a) => sum + a[pillar.score],
                        0,
                      ) / periodAudits.length,
                    )
                  : null;
                return (
                  <div className="pillar-row" key={pillar.key}>
                    <div className="pillar-label">
                      <span>
                        <b className="pillar-num">0{i + 1}</b>
                        {pillar.name}
                      </span>
                      <strong className="font-medium">
                        {score === null ? "—" : `${score}%`}
                      </strong>
                    </div>
                    <div className="pillar-track">
                      <div
                        style={{
                          width: `${score || 0}%`,
                          opacity: 1 - i * 0.08,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
              <div className="mt-6 flex items-center gap-2 border-t border-base-300 pt-4 text-[10px] text-base-content/55">
                <ShieldCheck size={13} />
                Based on {periodAudits.length} saved assessments
              </div>
            </div>
          </section>
          <section className="surface">
            <div className="surface-head">
              <div>
                <h2>Needs your attention</h2>
              </div>
              <span className="badge badge-ghost">
                {review.length +
                  overdue.filter((a) => a.status !== "submitted_for_review")
                    .length}
              </span>
            </div>
            {queue.map((activity) => (
              <button
                key={activity.id}
                className="queue-item"
                onClick={() => onOpenWork(activity)}
              >
                <span className="queue-icon">
                  {activity.status === "submitted_for_review" ? (
                    <ClipboardCheck size={16} />
                  ) : (
                    <Clock3 size={16} />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <strong>{activity.title}</strong>
                  <p>
                    {activity.status === "submitted_for_review"
                      ? "Waiting for review"
                      : `Overdue · ${dateLabel(activity.due_date)}`}
                  </p>
                </div>
                <ArrowUpRight size={14} className="mt-1 text-base-content/40" />
              </button>
            ))}
            {!queue.length && (
              <div className="px-5 pb-6 pt-3 text-xs text-base-content/60">
                <CircleCheck className="mb-3 text-success" size={24} />
                Your review queue is clear.
              </div>
            )}
            <div className="border-t border-base-300 px-5 py-3">
              <button
                className="text-link"
                onClick={() => onNavigate("work_orders")}
              >
                Open work orders <ArrowRight />
              </button>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
