import { useEffect, useState, type FormEvent } from "react";
import { request, type WorkspaceIdentity } from "../../api/client";

export function SignIn({
  onSignedIn,
}: {
  onSignedIn: (identity: WorkspaceIdentity) => void;
}) {
  const [setup, setSetup] = useState(false);
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    request<{ setup_required: boolean }>("/auth/status")
      .then((status) => {
        if (!active) return;
        setSetup(status.setup_required);
        if (status.setup_required) setEmail("marketing@enertechups.com");
        setReady(true);
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (setup && password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const identity = await request<WorkspaceIdentity>(
        setup ? "/auth/setup" : "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            email,
            password,
            ...(setup ? { setup_token: token } : {}),
          }),
        },
      );
      setPassword("");
      setConfirmation("");
      setToken("");
      onSignedIn(identity);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={(event) => void submit(event)} className="grid gap-4 mt-5">
      {setup && (
        <div className="access-notice">
          <div>
            <strong>Set up the first administrator</strong>
            <p>
              Use the BOOTSTRAP_TOKEN from your private Render environment
              settings. Setup closes after the first account is created.
            </p>
          </div>
        </div>
      )}
      {error && (
        <div role="alert" className="form-error">
          {error}
        </div>
      )}
      <label className="grid gap-2 text-sm">
        Work email
        <input
          className="input w-full"
          type="email"
          autoComplete="username"
          required
          maxLength={255}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </label>
      {setup && (
        <label className="grid gap-2 text-sm">
          Setup token
          <input
            className="input w-full"
            type="password"
            autoComplete="off"
            required
            minLength={16}
            maxLength={256}
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
        </label>
      )}
      <label className="grid gap-2 text-sm">
        {setup ? "Create password (12+ characters)" : "Password"}
        <input
          className="input w-full"
          type="password"
          autoComplete={setup ? "new-password" : "current-password"}
          required
          minLength={setup ? 12 : 1}
          maxLength={256}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      {setup && (
        <label className="grid gap-2 text-sm">
          Confirm password
          <input
            className="input w-full"
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={256}
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </label>
      )}
      <button
        className="btn btn-primary w-full"
        disabled={busy || !ready}
        type="submit"
      >
        {busy
          ? "Please wait…"
          : setup
            ? "Create administrator & sign in"
            : "Sign in"}
      </button>
      {!setup && (
        <p className="text-xs text-base-content/65">
          Contact your workspace administrator if you need an account or
          password recovery.
        </p>
      )}
    </form>
  );
}
