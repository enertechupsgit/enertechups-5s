import { useState } from "react";
import { TestAccounts } from "./TestAccounts";
import { Plus, Search, MapPin, ArrowRight } from "lucide-react";
import type { AuditRun, Plant, RedTag, ZonalLeader } from "../../types";
import {
  createRedTag,
  createZone,
  createZonalLeader,
  submitAudit,
  updateRedTagDisposition,
} from "../../api/client";
import { Dialog, Empty, EvidenceInput } from "./Shared";
import { dateLabel, pillars } from "./utils";

export function AuditWorkspace({
  plant,
  audits,
  canExecute,
  onSaved,
}: {
  plant: Plant;
  audits: AuditRun[];
  canExecute: boolean;
  onSaved: (audit: AuditRun) => void;
}) {
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const zones = plant.departments.flatMap((d) => d.zones);
  return (
    <>
      <section className="surface">
        <div className="surface-head">
          <div>
            <h2>Assessment history</h2>
            <p>
              Saved 5S pillar assessments with traceable location and auditor.
            </p>
          </div>
          {canExecute && (
            <button className="btn" onClick={() => setCreating(true)}>
              <Plus />
              New assessment
            </button>
          )}
        </div>
        {audits.length ? (
          <div className="overflow-x-auto">
            <table className="table mobile-records">
              <thead>
                <tr>
                  <th>Zone</th>
                  <th>Date</th>
                  <th>Auditor</th>
                  {pillars.map((p) => (
                    <th key={p.key}>{p.name}</th>
                  ))}
                  <th>Overall</th>
                </tr>
              </thead>
              <tbody>
                {audits.map((a) => (
                  <tr key={a.id}>
                    <td
                      data-label="Zone"
                      className="font-medium whitespace-nowrap"
                    >
                      {a.zone_name}
                    </td>
                    <td data-label="Date" className="whitespace-nowrap">
                      {dateLabel(a.conducted_at)}
                    </td>
                    <td data-label="Auditor">{a.auditor_name}</td>
                    {pillars.map((p) => (
                      <td data-label={p.name} key={p.key}>
                        {a[p.score]}%
                      </td>
                    ))}
                    <td data-label="Overall">
                      <span
                        className={`badge badge-soft ${a.score_percentage >= 90 ? "badge-success" : "badge-info"}`}
                      >
                        {a.score_percentage}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="No assessments yet"
            text={
              canExecute
                ? "Record the first assessment to establish a measured baseline."
                : "Recorded assessments in your scope will appear here."
            }
          />
        )}
      </section>
      {creating && (
        <Dialog
          title="Record a 5S assessment"
          onClose={() => setCreating(false)}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                const zone = zones.find((z) => z.id === form.get("zone"))!;
                const scores = Object.fromEntries(
                  pillars.map((p) => [p.score, Number(form.get(p.score))]),
                );
                const audit = await submitAudit({
                  plant_id: plant.id,
                  zone_id: zone.id,
                  zone_name: zone.name,
                  auditor_name: "",
                  sort_score: Number(scores.sort_score),
                  set_in_order_score: Number(scores.set_in_order_score),
                  shine_score: Number(scores.shine_score),
                  standardize_score: Number(scores.standardize_score),
                  sustain_score: Number(scores.sustain_score),
                  notes: String(form.get("notes")),
                });
                onSaved(audit);
                setCreating(false);
              } catch (err) {
                setError((err as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="dialog-body">
              <p className="mb-5 text-xs leading-relaxed text-base-content/65">
                Enter observed pillar scores from your plant’s assessment
                rubric. The server calculates the overall mean and records your
                signed-in identity.
              </p>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <label>
                Zone
                <select name="zone" className="select" required>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="dialog-fields">
                {pillars.map((p) => (
                  <label key={p.key}>
                    {p.label} · score %
                    <input
                      name={p.score}
                      className="input"
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      placeholder="0–100"
                      required
                    />
                  </label>
                ))}
              </div>
              <label>
                Assessment notes
                <textarea
                  className="textarea"
                  rows={3}
                  name="notes"
                  required
                  placeholder="Record observed conditions, findings, and evidence references."
                />
              </label>
            </div>
            <div className="dialog-foot">
              <button
                type="button"
                className="btn"
                onClick={() => setCreating(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                disabled={busy || !zones.length}
              >
                {busy ? "Saving…" : "Save assessment"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}

export function RedTagsWorkspace({
  plant,
  tags,
  canCreate,
  canDispose,
  onSaved,
}: {
  plant: Plant;
  tags: RedTag[];
  canCreate: boolean;
  canDispose: boolean;
  onSaved: () => void;
}) {
  const [search, setSearch] = useState("");
  const [modal, setModal] = useState<"create" | RedTag | null>(null);
  const [photo, setPhoto] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const zones = plant.departments.flatMap((d) => d.zones);
  const filtered = tags.filter((t) =>
    `${t.item_name} ${t.tag_number}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <section className="surface">
        <div className="filterbar">
          <label className="input">
            <Search size={15} />
            <input
              aria-label="Search red tags"
              placeholder="Search an item or tag number…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <span className="ml-auto text-xs text-base-content/60">
            {tags.filter((t) => !t.is_closed).length} open items
          </span>
          {canCreate && (
            <button
              className="btn"
              onClick={() => {
                setError("");
                setPhoto("");
                setModal("create");
              }}
            >
              <Plus />
              Log red tag
            </button>
          )}
        </div>
        {filtered.length ? (
          <div className="overflow-x-auto">
            <table className="table mobile-records">
              <thead>
                <tr>
                  <th>Tagged item</th>
                  <th>Zone</th>
                  <th>Reason</th>
                  <th>Age</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr key={t.id}>
                    <td data-label="Tagged item">
                      <span className="work-id">{t.tag_number}</span>
                      <strong className="block text-xs">{t.item_name}</strong>
                      <span className="text-[10px] text-base-content/55">
                        Qty {t.quantity} · {t.item_category}
                      </span>
                    </td>
                    <td data-label="Zone">
                      {zones.find((z) => z.id === t.zone_id)?.name || "—"}
                    </td>
                    <td
                      data-label="Reason"
                      className="max-w-xs leading-relaxed"
                    >
                      {t.reason}
                    </td>
                    <td data-label="Age" className="whitespace-nowrap">
                      {t.aging_days} days
                    </td>
                    <td data-label="Status">
                      <span
                        className={`badge badge-soft ${t.is_closed ? "badge-success" : "badge-warning"}`}
                      >
                        {t.is_closed
                          ? "Closed"
                          : t.disposition === "pending"
                            ? "Awaiting disposition"
                            : t.disposition.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td data-label="Action">
                      {canDispose && !t.is_closed ? (
                        <button
                          className="btn"
                          onClick={() => {
                            setError("");
                            setModal(t);
                          }}
                        >
                          Disposition
                          <ArrowRight />
                        </button>
                      ) : (
                        <span className="text-[10px] text-base-content/50">
                          {t.is_closed
                            ? "Verified record"
                            : "Supervisor decision"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="A place for everything that doesn’t belong"
            text="Log unnecessary items with their location and a clear reason."
          />
        )}
      </section>
      {modal && (
        <Dialog
          title={
            modal === "create" ? "Log a red-tag item" : "Record disposition"
          }
          onClose={() => setModal(null)}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                if (modal === "create") {
                  await createRedTag({
                    plant_id: plant.id,
                    zone_id: String(form.get("zone")),
                    item_name: String(form.get("item")),
                    item_category: String(form.get("category")),
                    quantity: Number(form.get("quantity")),
                    reason: String(form.get("reason")),
                    photo_url: photo || undefined,
                  });
                } else {
                  const disposition = String(form.get("disposition")) as
                    | "relocate"
                    | "scrap"
                    | "return_to_vendor"
                    | "hold_for_evaluation";
                  await updateRedTagDisposition(modal.id, {
                    disposition,
                    disposition_notes: String(form.get("notes")),
                    is_closed:
                      disposition !== "hold_for_evaluation" &&
                      form.get("executed") === "on",
                  });
                }
                setModal(null);
                onSaved();
              } catch (err) {
                setError((err as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="dialog-body">
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              {modal === "create" ? (
                <>
                  <label>
                    Item name
                    <input className="input" name="item" required />
                  </label>
                  <div className="dialog-fields">
                    <label>
                      Zone
                      <select className="select" name="zone" required>
                        {zones.map((z) => (
                          <option key={z.id} value={z.id}>
                            {z.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Quantity
                      <input
                        className="input"
                        name="quantity"
                        type="number"
                        min="1"
                        max="100000"
                        defaultValue="1"
                        required
                      />
                    </label>
                    <label>
                      Category
                      <select className="select" name="category">
                        <option>Equipment/Tool</option>
                        <option>Material</option>
                        <option>Furniture</option>
                        <option>Document</option>
                        <option>Other</option>
                      </select>
                    </label>
                  </div>
                  <label>
                    Why is this item tagged?
                    <textarea
                      className="textarea"
                      name="reason"
                      required
                      rows={3}
                    />
                  </label>
                  <EvidenceInput value={photo} onChange={setPhoto} />
                </>
              ) : (
                <>
                  <p className="mb-5 text-sm font-medium">{modal.item_name}</p>
                  <label>
                    Disposition
                    <select className="select" name="disposition">
                      <option value="hold_for_evaluation">
                        Hold for evaluation
                      </option>
                      <option value="relocate">Relocate</option>
                      <option value="scrap">Scrap</option>
                      <option value="return_to_vendor">Return to vendor</option>
                    </select>
                  </label>
                  <label>
                    Reason and execution details
                    <textarea
                      className="textarea"
                      name="notes"
                      required
                      rows={3}
                    />
                  </label>
                  <label className="flex-row! items-start gap-3!">
                    <input className="mt-1" type="checkbox" name="executed" />I
                    confirm the physical disposition has been carried out and
                    this item can be closed.
                  </label>
                </>
              )}
            </div>
            <div className="dialog-foot">
              <button
                type="button"
                className="btn"
                onClick={() => setModal(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                disabled={busy || !zones.length}
              >
                {busy ? "Saving…" : "Save record"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}

export function LocationsWorkspace({
  plant,
  canManage,
  onSaved,
}: {
  plant: Plant;
  canManage: boolean;
  onSaved: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
      <div className="flex justify-end mb-4">
        {canManage && (
          <button className="btn" onClick={() => setAdding(true)}>
            <Plus />
            Add zone
          </button>
        )}
      </div>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {plant.departments.map((dept) => (
          <section className="surface" key={dept.id}>
            <div className="surface-head">
              <div>
                <h2>{dept.name}</h2>
                <p>
                  {dept.code} · {dept.zones.length} zones
                </p>
              </div>
              <MapPin className="text-primary" size={20} />
            </div>
            {dept.zones.map((z) => (
              <div className="location-zone" key={z.id}>
                <span className="zone-code">{z.code.slice(0, 2)}</span>
                <div>
                  <strong>{z.name}</strong>
                  <p>
                    {z.code} · {z.leader_name || "Leader not assigned"}
                  </p>
                </div>
              </div>
            ))}
          </section>
        ))}
      </div>
      {!plant.departments.length && (
        <section className="surface">
          <Empty
            title="Organize your plant"
            text="Add your first zone and its department to establish clear ownership."
          />
        </section>
      )}
      {adding && (
        <Dialog title="Add a plant zone" onClose={() => setAdding(false)}>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                await createZone({
                  plant_id: plant.id,
                  name: String(form.get("name")),
                  code: String(form.get("code")),
                  dept_id: String(form.get("dept")) || undefined,
                  dept_name: String(form.get("dept_name")) || undefined,
                  target_score: 90,
                });
                setAdding(false);
                onSaved();
              } catch (err) {
                setError((err as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="dialog-body">
              {error && (
                <p role="alert" className="form-error">
                  {error}
                </p>
              )}
              <label>
                Zone name
                <input className="input" name="name" required />
              </label>
              <label>
                Zone code
                <input className="input" name="code" required />
              </label>
              <label>
                Existing department
                <select className="select" name="dept">
                  <option value="">Create a new department below</option>
                  {plant.departments.map((d) => (
                    <option value={d.id} key={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                New department name
                <input
                  name="dept_name"
                  className="input"
                  placeholder="Required only when creating a new department"
                />
              </label>
            </div>
            <div className="dialog-foot">
              <button
                type="button"
                className="btn"
                onClick={() => setAdding(false)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" disabled={busy}>
                Save zone
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}

export function PeopleWorkspace({
  plant,
  people,
  canManage,
  onSaved,
}: {
  plant: Plant;
  people: ZonalLeader[];
  canManage: boolean;
  onSaved: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const zones = plant.departments.flatMap((d) => d.zones);
  return (
    <>
      <section className="surface">
        <div className="surface-head">
          <div>
            <h2>Plant people and assignments</h2>
            <p>
              {canManage
                ? "Manage operational profiles and assign zone responsibility."
                : "Read-only visibility into plant responsibility."}
            </p>
          </div>
          {canManage && (
            <button className="btn" onClick={() => setAdding(true)}>
              <Plus />
              Add team member
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="table mobile-records">
            <thead>
              <tr>
                <th>Team member</th>
                <th>Role</th>
                <th>Assigned zone</th>
                <th>Active work</th>
                <th>Completed</th>
              </tr>
            </thead>
            <tbody>
              {people.map((p) => (
                <tr key={p.id}>
                  <td data-label="Team member">
                    <div className="flex items-center gap-3">
                      <span className="initials">
                        {p.first_name[0]}
                        {p.last_name[0]}
                      </span>
                      <div>
                        <strong>
                          {p.first_name} {p.last_name}
                        </strong>
                        <p className="mt-1 text-[10px] text-base-content/55">
                          {p.email}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td
                    data-label="Role"
                    className="capitalize whitespace-nowrap"
                  >
                    {p.role.replaceAll("_", " ")}
                  </td>
                  <td data-label="Assigned zone">
                    {p.assigned_zone_name || "Plant scope"}
                  </td>
                  <td data-label="Active work">{p.active_tasks_count}</td>
                  <td data-label="Completed">{p.completed_tasks_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <TestAccounts />
      {adding && (
        <Dialog
          title="Add an operational team member"
          onClose={() => setAdding(false)}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                await createZonalLeader({
                  plant_id: plant.id,
                  first_name: String(form.get("first")),
                  last_name: String(form.get("last")),
                  email: String(form.get("email")),
                  role: String(form.get("role")),
                  assigned_zone_id: String(form.get("zone")) || undefined,
                });
                setAdding(false);
                onSaved();
              } catch (err) {
                setError((err as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="dialog-body">
              <p className="mb-5 text-xs leading-relaxed text-base-content/60">
                Adds a team profile. Login access is set up separately.
              </p>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <div className="dialog-fields">
                <label>
                  First name
                  <input className="input" name="first" required />
                </label>
                <label>
                  Last name
                  <input className="input" name="last" required />
                </label>
              </div>
              <label>
                Email
                <input className="input" name="email" type="email" required />
              </label>
              <label>
                Operational role
                <select className="select" name="role">
                  <option value="zonal_leader">Zonal leader</option>
                  <option value="operator">Operator</option>
                  <option value="auditor">Auditor</option>
                  <option value="supervisor">Supervisor</option>
                </select>
              </label>
              <label>
                Assigned zone
                <select className="select" name="zone">
                  <option value="">No zone assigned</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="dialog-foot">
              <button
                type="button"
                className="btn"
                onClick={() => setAdding(false)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" disabled={busy}>
                Save team member
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}
