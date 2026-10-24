import { useEffect, useState } from "react";
import { request } from "../../api/client";

interface TestAccount {
  name: string;
  role: string;
  email: string;
  password: string;
  zone: string;
  expires_at: string;
}
export function TestAccounts() {
  const [status, setStatus] = useState<{
    can_create: boolean;
    existing_count: number;
  } | null>(null);
  const [accounts, setAccounts] = useState<TestAccount[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    request<{ can_create: boolean; existing_count: number }>(
      "/auth/test-accounts/status",
    )
      .then((value) => {
        if (active) setStatus(value);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  if (!status) return null;
  return (
    <section className="surface mt-6">
      <div className="surface-head">
        <div>
          <h2>Isolated testing accounts</h2>
          <p>
            Management, HR, three zone leaders and Admin. Separate test
            organization; seven-day access.
          </p>
        </div>
        <button
          className="btn btn-primary"
          disabled={busy || !status.can_create}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              const result = await request<{ accounts: TestAccount[] }>(
                "/auth/test-accounts",
                { method: "POST", body: "{}" },
              );
              setAccounts(result.accounts);
              setStatus({ can_create: false, existing_count: 6 });
            } catch (err) {
              setError((err as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy
            ? "Creating accounts…"
            : status.can_create
              ? "Create six test accounts"
              : "Test accounts created"}
        </button>
      </div>
      {error && (
        <p className="form-error m-4" role="alert">
          {error}
        </p>
      )}
      {accounts.length > 0 ? (
        <div className="p-4">
          <p className="text-sm mb-4">
            Save these credentials now. Passwords are shown only once. Access
            expires {new Date(accounts[0].expires_at).toLocaleString()}.
          </p>
          <div className="overflow-x-auto">
            <table className="table mobile-records">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Login ID</th>
                  <th>Password</th>
                  <th>Scope</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.email}>
                    <td data-label="Role">{account.name}</td>
                    <td data-label="Login ID">
                      <code>{account.email}</code>
                    </td>
                    <td data-label="Password">
                      <code>{account.password}</code>
                    </td>
                    <td data-label="Scope">{account.zone}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            className="btn mt-4"
            onClick={() => {
              const csv = [
                "Role,Login ID,Password,Scope,Expires",
                ...accounts.map((account) =>
                  [
                    account.name,
                    account.email,
                    account.password,
                    account.zone,
                    account.expires_at,
                  ].join(","),
                ),
              ].join("\r\n");
              const url = URL.createObjectURL(
                new Blob([csv], { type: "text/csv" }),
              );
              const link = document.createElement("a");
              link.href = url;
              link.download = "enertech-test-logins.csv";
              link.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            }}
          >
            Download test logins
          </button>
        </div>
      ) : (
        !status.can_create && (
          <p className="p-4 text-sm">
            Testing accounts already exist. Saved passwords cannot be displayed
            again.
          </p>
        )
      )}
    </section>
  );
}
