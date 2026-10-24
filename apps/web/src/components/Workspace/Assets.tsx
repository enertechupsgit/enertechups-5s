import { useEffect, useState } from "react";
import {
  Box,
  Search,
  Plus,
  MapPin,
  History,
  Layers,
  ArrowRight,
} from "lucide-react";
import {
  fetchAssets,
  saveAsset,
  setAssetStatus,
  type AssetRecord,
} from "../../api/client";
import type { Plant } from "../../types";
import { Dialog, Empty, Status } from "./Shared";
import { dateLabel } from "./utils";

export function Assets({
  plant,
  notify,
  canManage = false,
}: {
  plant: Plant;
  canManage?: boolean;
  notify: (message: string) => void;
}) {
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState(false);
  const [parentId, setParentId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [change, setChange] = useState(false);
  useEffect(() => {
    let active = true;
    fetchAssets(plant.id)
      .then((data) => {
        if (active) {
          setAssets(data);
          setSelectedId(data[0]?.id || "");
        }
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [plant.id]);
  const filtered = assets.filter((a) =>
    `${a.name} ${a.code}`.toLowerCase().includes(search.toLowerCase()),
  );
  const selected = filtered.find((a) => a.id === selectedId) || filtered[0];
  const zones = plant.departments.flatMap((d) => d.zones);
  return (
    <>
      <section className="surface">
        <div className="filterbar">
          <label className="input">
            <Search size={15} />
            <input
              aria-label="Search assets"
              placeholder="Search assets or equipment ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <span className="ml-auto text-[11px] text-base-content/55">
            {assets.length} assets ·{" "}
            {assets.filter((a) => a.status === "online").length} online
          </span>
          <button
            className="btn"
            disabled={!canManage}
            onClick={() => {
              setParentId("");
              setAdding(true);
            }}
          >
            <Plus />
            New asset
          </button>
        </div>
        {error && (
          <div className="form-error mx-5" role="alert">
            {error}
          </div>
        )}
        {!assets.length ? (
          <Empty
            title="An organized home for every asset"
            text="Register equipment, connect it to a zone, and keep its status history in one place."
            action={
              <button
                className="btn"
                disabled={!canManage}
                onClick={() => {
                  setParentId("");
                  setAdding(true);
                }}
              >
                <Plus />
                Register an asset
              </button>
            }
          />
        ) : (
          <div className="asset-layout">
            <div className="asset-list">
              {filtered.map((asset) => (
                <button
                  className={`asset-row ${selected?.id === asset.id ? "selected" : ""}`}
                  key={asset.id}
                  onClick={() => setSelectedId(asset.id)}
                >
                  <span className="asset-glyph">
                    <Box size={21} strokeWidth={1.4} />
                  </span>
                  <span>
                    <strong>{asset.name}</strong>
                    <small>{asset.code}</small>
                    <span className="mt-2 block">
                      <Status value={asset.status} />
                    </span>
                  </span>
                </button>
              ))}
              {!filtered.length && (
                <Empty
                  title="No assets found"
                  text="Try another name or code."
                />
              )}
            </div>
            {selected && (
              <div className="asset-detail">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="eyebrow">EQUIPMENT / {selected.code}</div>
                    <h2>{selected.name}</h2>
                  </div>
                  <Status value={selected.status} />
                </div>
                <p className="mt-4 text-xs leading-relaxed text-base-content/65">
                  {selected.description || "No description added."}
                </p>
                <div className="detail-grid">
                  <div>
                    <dt>Location</dt>
                    <dd className="flex items-center gap-1.5">
                      <MapPin size={14} />
                      {zones.find((z) => z.id === selected.zone_id)?.name ||
                        "Not assigned"}
                    </dd>
                  </div>
                  <div>
                    <dt>Manufacturer</dt>
                    <dd>{selected.manufacturer || "—"}</dd>
                  </div>
                  <div>
                    <dt>Model</dt>
                    <dd>{selected.model || "—"}</dd>
                  </div>
                  <div>
                    <dt>Parent asset</dt>
                    <dd>
                      {assets.find((a) => a.id === selected.parent_id)?.name ||
                        "Top-level asset"}
                    </dd>
                  </div>
                </div>
                <div className="mb-7 flex items-center justify-between rounded-lg border border-base-300 p-4">
                  <div>
                    <p className="text-xs font-medium">Operating status</p>
                    <p className="mt-1 text-[10px] text-base-content/55">
                      Changes are recorded in the asset history.
                    </p>
                  </div>
                  <button
                    disabled={!canManage}
                    className="btn"
                    onClick={() => {
                      setError("");
                      setChange(true);
                    }}
                  >
                    Update status
                  </button>
                </div>
                <h3 className="mb-4 flex items-center gap-2 text-xs font-semibold">
                  <Layers size={15} />
                  Sub-assets{" "}
                  <span className="text-base-content/40">
                    ({assets.filter((a) => a.parent_id === selected.id).length})
                  </span>
                </h3>
                {assets
                  .filter((a) => a.parent_id === selected.id)
                  .map((asset) => (
                    <button
                      className="mb-2 flex w-full items-center justify-between rounded-lg border border-base-300 p-3 text-xs"
                      key={asset.id}
                      onClick={() => setSelectedId(asset.id)}
                    >
                      {asset.name}
                      <ArrowRight size={13} />
                    </button>
                  ))}
                <button
                  className="text-link mb-6"
                  disabled={!canManage}
                  onClick={() => {
                    setParentId(selected.id);
                    setAdding(true);
                  }}
                >
                  <Plus />
                  Create sub-asset
                </button>
                <h3 className="mb-5 flex items-center gap-2 border-t border-base-300 pt-5 text-xs font-semibold">
                  <History size={15} />
                  Status history
                </h3>
                {selected.events.map((event) => (
                  <div className="timeline-row" key={event.id}>
                    <span className="mt-1.5 status-dot positive" />
                    <div>
                      <div className="flex items-center gap-3">
                        <Status value={event.status} />
                        <span className="text-[10px] text-base-content/45">
                          {dateLabel(event.created_at)}
                        </span>
                      </div>
                      <p>{event.note}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
      {adding && canManage && (
        <Dialog title="Register an asset" onClose={() => setAdding(false)}>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                const asset = await saveAsset({
                  plant_id: plant.id,
                  name: String(form.get("name")),
                  code: String(form.get("code")),
                  zone_id: String(form.get("zone")) || null,
                  parent_id: String(form.get("parent")) || null,
                  description: String(form.get("description")),
                  manufacturer: String(form.get("manufacturer")),
                  model: String(form.get("model")),
                });
                setAssets((previous) => [...previous, asset]);
                setSelectedId(asset.id);
                setAdding(false);
                notify("Asset registered and saved to the database");
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
              <label>
                Asset name
                <input
                  className="input"
                  name="name"
                  required
                  placeholder="e.g. Assembly workbench 01"
                />
              </label>
              <div className="dialog-fields">
                <label>
                  Asset code
                  <input
                    className="input"
                    name="code"
                    required
                    placeholder="ET-AS-001"
                  />
                </label>
                <label>
                  Zone
                  <select name="zone" className="select">
                    <option value="">Not assigned</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.id}>
                        {z.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Manufacturer
                  <input className="input" name="manufacturer" />
                </label>
                <label>
                  Model
                  <input className="input" name="model" />
                </label>
              </div>
              <label>
                Parent asset
                <select
                  name="parent"
                  className="select"
                  defaultValue={parentId}
                >
                  <option value="">None · top-level asset</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Description
                <textarea className="textarea" name="description" rows={3} />
              </label>
            </div>
            <div className="dialog-foot">
              <button
                className="btn"
                type="button"
                onClick={() => setAdding(false)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" disabled={busy}>
                {busy ? "Saving…" : "Register asset"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {change && canManage && selected && (
        <Dialog
          title="Update operating status"
          onClose={() => setChange(false)}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                const updated = await setAssetStatus(
                  selected.id,
                  String(form.get("status")),
                  String(form.get("note")),
                );
                setAssets((previous) =>
                  previous.map((a) => (a.id === updated.id ? updated : a)),
                );
                setChange(false);
                notify("Status updated with a recorded reason");
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
              <label>
                Status
                <select
                  name="status"
                  className="select"
                  defaultValue={selected.status}
                >
                  <option value="online">Online</option>
                  <option value="offline">Offline</option>
                  <option value="maintenance">Planned maintenance</option>
                </select>
              </label>
              <label>
                Reason
                <textarea
                  className="textarea"
                  name="note"
                  required
                  rows={3}
                  placeholder="Record why this status changed."
                />
              </label>
            </div>
            <div className="dialog-foot">
              <button
                className="btn"
                type="button"
                onClick={() => setChange(false)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" disabled={busy}>
                Save status
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}
