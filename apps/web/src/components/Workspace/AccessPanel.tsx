import {
  ArrowRight,
  Check,
  Eye,
  LockKeyhole,
  ShieldCheck,
  UserRoundCog,
  X,
} from "lucide-react";
import type { WorkspaceIdentity } from "../../api/client";
import { Dialog } from "./Shared";

import {
  roleLabels,
  roleDescriptions,
  capabilities,
} from "./accessDefinitions";

export function RoleSwitcher({
  current,
  identities,
  busy,
  error,
  onSwitch,
  onClose,
}: {
  current: WorkspaceIdentity | null;
  identities: WorkspaceIdentity[];
  busy: boolean;
  error: string;
  onSwitch: (id: string) => void;
  onClose: () => void;
}) {
  return (
    <Dialog title="Switch workspace role" onClose={onClose} wide>
      <div className="dialog-body">
        <div className="access-notice">
          <UserRoundCog size={19} />
          <div>
            <strong>Local sample testing</strong>
            <p>
              Switch between sample accounts to test real server permissions.
              This switcher is disabled outside the local preview server.
            </p>
          </div>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="role-options">
          {[...identities]
            .sort(
              (a, b) =>
                ["director", "supervisor", "auditor", "zonal_leader"].indexOf(
                  a.role,
                ) -
                ["director", "supervisor", "auditor", "zonal_leader"].indexOf(
                  b.role,
                ),
            )
            .map((identity) => (
              <button
                key={identity.id}
                className={`role-option ${current?.id === identity.id ? "selected" : ""}`}
                disabled={busy}
                onClick={() => onSwitch(identity.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="role-avatar">
                    {identity.role === "director" ? (
                      <Eye size={18} />
                    ) : identity.role === "zonal_leader" ? (
                      <UserRoundCog size={18} />
                    ) : (
                      <ShieldCheck size={18} />
                    )}
                  </span>
                  <div>
                    <strong>{roleLabels[identity.role]}</strong>
                    <span>{identity.name}</span>
                  </div>
                  {current?.id === identity.id ? (
                    <Check className="ml-auto text-primary" size={18} />
                  ) : (
                    <ArrowRight
                      className="ml-auto text-base-content/35"
                      size={17}
                    />
                  )}
                </div>
                <p>{identity.zone_name || roleDescriptions[identity.role]}</p>
              </button>
            ))}
        </div>
      </div>
    </Dialog>
  );
}
export function AccessPanel({
  identity,
  identities = [],
}: {
  identity: WorkspaceIdentity;
  identities?: WorkspaceIdentity[];
}) {
  return (
    <div className="space-y-5">
      <section className="surface">
        <div className="surface-head">
          <div>
            <h2>Your active access</h2>
          </div>
          <LockKeyhole size={20} className="text-primary" />
        </div>
        <div className="px-6 pb-6">
          <span className="badge badge-info badge-soft mb-3">
            {roleLabels[identity.role]}
          </span>
          <h2 className="text-xl font-semibold">{identity.name}</h2>
          <p className="mt-2 text-sm leading-relaxed text-base-content/65">
            {roleDescriptions[identity.role]}
          </p>
          <p className="mt-4 text-xs text-base-content/65">
            <strong>Scope:</strong>{" "}
            {identity.role === "zonal_leader"
              ? identity.zone_name ||
                "No zone assigned — no operational records available"
              : identity.role === "director"
                ? "Plants in the assigned organization"
                : "Assigned plant"}
          </p>
          <p className="mt-2 text-xs text-base-content/65">
            <strong>Rules:</strong> you cannot approve your own work.
          </p>
        </div>
      </section>
      <section className="surface">
        <div className="surface-head">
          <div>
            <h2>What I can do</h2>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="table mobile-records">
            <thead>
              <tr>
                <th>Capability</th>
                <th>My access</th>
                <th>Boundary</th>
              </tr>
            </thead>
            <tbody>
              {capabilities.map((c) => (
                <tr key={c.key}>
                  <td data-label="Capability" className="font-medium">
                    {c.name}
                  </td>
                  <td data-label="My access">
                    {identity.permissions.includes(c.key) ? (
                      <span className="permission-yes">
                        <Check size={14} />
                        Allowed
                      </span>
                    ) : (
                      <span className="permission-no">
                        <X size={14} />
                        Not allowed
                      </span>
                    )}
                  </td>
                  <td data-label="Boundary" className="text-base-content/60">
                    {c.note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {identities.length > 0 && (
        <section className="surface">
          <div className="surface-head">
            <div>
              <h2>Compare workspace roles</h2>
              <p>
                Director oversight and zonal execution have different
                responsibilities.
              </p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Capability</th>
                  {["director", "supervisor", "auditor", "zonal_leader"].map(
                    (role) => (
                      <th key={role}>{roleLabels[role]}</th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {capabilities.map((capability) => (
                  <tr key={capability.key}>
                    <td className="font-medium">{capability.name}</td>
                    {["director", "supervisor", "auditor", "zonal_leader"].map(
                      (role) => (
                        <td key={role}>
                          {identities
                            .find((person) => person.role === role)
                            ?.permissions.includes(capability.key) ? (
                            <span className="permission-yes">
                              <Check size={14} />
                              Allowed
                            </span>
                          ) : (
                            <span className="permission-no">
                              <X size={14} />
                              Not allowed
                            </span>
                          )}
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
