export const roleLabels: Record<string, string> = {
  director: "Director",
  supervisor: "Supervisor",
  auditor: "Auditor",
  zonal_leader: "Zonal leader",
  hr: "HR",
  admin: "Admin",
};
export const roleDescriptions: Record<string, string> = {
  hr: "Manage people and zone assignments. Operational records are read-only.",
  admin:
    "Manage the assigned plant, people, locations, assets and operational workflows.",
  director:
    "Plant-wide oversight, trends, people visibility, and reporting. Operational records are read-only.",
  supervisor:
    "Assign work, review evidence, manage locations and people, and verify improvements.",
  auditor:
    "Conduct assessments, record findings, and compare standards across the assigned plant.",
  zonal_leader:
    "Work on assigned actions, capture before/after evidence, and track the assigned zone.",
};
export const capabilities = [
  {
    key: "overview.read",
    name: "View performance",
    note: "Within your assigned scope",
  },
  {
    key: "work.create",
    name: "Create work orders",
    note: "Self and assigned zone for zonal leaders",
  },
  {
    key: "work.execute",
    name: "Execute and submit work",
    note: "Assigned work for zonal leaders",
  },
  {
    key: "work.review",
    name: "Approve / request changes",
    note: "Own-work review is blocked",
  },
  {
    key: "audit.execute",
    name: "Conduct audits",
    note: "Published scores saved to the plant",
  },
  {
    key: "redtag.create",
    name: "Log red tags",
    note: "Within your assigned zone or plant",
  },
  {
    key: "redtag.dispose",
    name: "Approve tag disposition",
    note: "Supervisor authority",
  },
  {
    key: "asset.manage",
    name: "Manage assets and status",
    note: "Within the assigned plant",
  },
  {
    key: "people.manage",
    name: "Manage people and assignments",
    note: "No elevated administrator grants",
  },
  {
    key: "location.manage",
    name: "Manage plant locations",
    note: "Within the assigned plant",
  },
  {
    key: "report.export",
    name: "Export reports",
    note: "Scope remains enforced on downloads",
  },
];
