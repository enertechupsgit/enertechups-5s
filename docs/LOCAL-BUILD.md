# Local development build

This build introduces the new Enertech desktop/mobile web workspace: overview, work list/cards, photo evidence, persisted report submission/review, asset registry/status history, audit navigation, CSV/PDF reports, search, review inbox and a focused zonal-leader preview.

## Run

From the project root in PowerShell:

```powershell
.\scripts\start-local.ps1
```

Open http://127.0.0.1:5173. API docs are at http://127.0.0.1:8000/docs. The script binds both services to loopback, checks for occupied ports and starts hidden background processes. Logs and process IDs are saved under ignored `artifacts/`. Stop only those recorded processes when finished.

The default is an explicitly labelled sample workspace backed by `backend/local-preview.db`. Fixtures are inserted only when the sample database has no departments. Browser reloads preserve saved records. Neither existing `digi5s.db` is selected by the default launcher. `-UseExistingData` explicitly selects `backend/digi5s.db`; inventory/back it up before using that option.

The launcher uses the bundled Python runtime when available and the existing `.venv/Lib/site-packages` as a package source because the original virtual environment's base interpreter is missing. On another computer, install a working Python 3.12+ environment and `backend/requirements.txt`. Web dependencies use `pnpm install` in `apps/web`; the authoritative new lockfile is `pnpm-lock.yaml`.

## Roles

Use **Switch role** in the top bar to choose a sample Director, Supervisor, Auditor, or Zonal leader. This creates an eight-hour HttpOnly session with server-enforced permissions. The director has read-only plant oversight; supervisors assign/review work and manage operational records; auditors conduct assessments; leaders execute their own work in their assigned zone. **My access & roles** explains permissions and compares the roles. API checks include scope, active membership, self-review prevention, session expiry, and write-origin/header validation.

Sample account switching is intentionally available only in `LOCAL_DEMO=1` on loopback, restricted to sample identities. It is a development evaluation feature. It is not a production impersonation feature. Outside this mode, local switching is disabled. Hosted deployments use protected administrator setup and password/session sign-in; see RENDER-DEPLOYMENT.md. `-UseExistingData` does not enable sample authentication against existing plant records.

Managed PostgreSQL is configured for Render. Reviewed schema migrations, SSO, private object storage, question-level audit templates, and native mobile/offline sync remain roadmap work. Do not publicly expose this development server. The browser UI is responsive; native Android/iOS packaging and offline guarantees are not included in this increment.

## Mobile behaviour

Phone work lists automatically use cards. Search stays visible; additional filters expand on demand. Page headings are compact, touch controls are at least 44 CSS pixels, form text is 16 pixels to avoid iOS input zoom, and dialogs use the available viewport with a sticky close header. Audit, red-tag, people and personal-access tables become labeled records. The role comparison remains a horizontally scrollable matrix. The navigation drawer traps focus, hides background content from interaction, and restores focus on close. Safe-area insets and dynamic viewport height are supported.

Brand assets come from the official EnerTech UPS website: https://enertechups.com/. The logo is saved at `apps/web/public/brand/enertech-logo.png`; the primary blue (#1d359d) was observed on the official site's call-to-action. Supporting neutrals are application choices, not a published corporate brand specification.

New photos accept JPEG/PNG/WebP up to 3 MB and 20 megapixels, with decoded image validation on both the client and server. Evidence remains stored as data URLs; private object storage and media pagination remain scaling work. Work comments and assessments support persisted photo attachments. See FUNCTIONAL-AUDIT.md for the tested upload fields and limitations.

## Checks

```powershell
# Within apps/web:
pnpm run build
pnpm run lint
pnpm run test

# From backend, using a working Python with dependencies:
python -m unittest discover -s tests -p 'test_*.py' -v
```

The backend suite runs 20 isolated tests covering workflows, comments, photo validation/persistence, audit records, red-tag disposition, assignment eligibility, independent review, public health, authentication and role/organization boundaries. It uses isolated SQLite databases and does not mutate plant data. Three Node tests cover timestamp parsing. See FUNCTIONAL-AUDIT.md for browser verification and remaining release work.
