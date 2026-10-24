# Deploy the complete EnerTech 5S workspace on Render

The root `Dockerfile` builds the React frontend with pnpm and serves its compiled assets from FastAPI. One Render Web Service hosts both at the same HTTPS origin. A separate managed PostgreSQL database stores records, session hashes, password hashes and local-increment photo evidence. No VITE_API_URL or separate frontend service is needed for this deployment.

## Deploy the Blueprint

1. In Render, choose **New → Blueprint**.
2. Connect `enertechupsgit/enertechups-5s`, branch `main`.
3. Use Blueprint path `render.yaml` from the repository root.
4. Review the Docker web service and PostgreSQL database. Both request the free evaluation plan. If Render says you already have a free database, use the existing compatible database connection or upgrade through the dashboard; do not delete existing data.
5. Deploy the Blueprint. Wait for the database and web service to become healthy.
6. Open the web service's actual HTTPS URL. The same URL serves the mobile/web frontend and `/api/v1` API. `/health` checks database connectivity; `/docs` documents the API.

**Existing failed Python service:** creating this Blueprint may create a suffixed service instead of updating the existing resource. Use the newly provisioned Docker service URL. Do not keep retrying the former `pip install` deployment. Do not delete the older service until the new deployment has been checked. Docker builds from the whole repository: leave Root Directory empty. The Dockerfile supplies its start command.

## First administrator — complete privately

The Blueprint generates `BOOTSTRAP_TOKEN` in Render's environment settings and configures `BOOTSTRAP_ADMIN_EMAIL=marketing@enertechups.com`.

1. Privately copy BOOTSTRAP_TOKEN from the Docker service's environment settings. Never paste it into chat, source code, issue comments or a URL.
2. On the application's setup screen enter that token, the configured email, and your own password of at least 12 characters.
3. Confirm the password and submit. This creates an administrator with supervisor permissions and signs you in. Setup is disabled once a password account exists, including after redeploys. The retained token cannot create additional administrators.
4. Sign out and sign back in to verify the stored password. Check Locations & zones and create the real department/zone hierarchy before assigning work.

Passwords use salted scrypt hashes. Sessions use random tokens with only their SHA-256 hashes stored in the database; browser cookies are Secure, HttpOnly and SameSite=Strict online. Invalid login attempts lock an existing account after five failures for 15 minutes. The sample role switcher remains loopback-only and is disabled in the Docker image and Blueprint.

This increment provisions the initial administrator only. People records do not automatically receive login credentials. Organization-wide account enrollment, password recovery/MFA/SSO and production identity lifecycle remain follow-up work. Do not share the administrator password between employees to simulate separate roles.

## Data and operational limits

- Free Render databases expire after 30 days and free web services sleep when idle. Use paid persistent services and an appropriate backup/recovery plan for business operation. See https://render.com/docs/free.
- A fresh database creates the initial schema and organization/plant baseline. Existing local SQLite databases are excluded from the container. Existing local data is not silently migrated. Future schema changes need reviewed migrations; `create_all` does not alter existing columns.
- Evidence remains database-backed data URLs in this increment. Private object storage, server-side image validation and storage quotas still require work before high-volume or sensitive production use.
- Deployments keep database-backed records and logins. Protect DATABASE_URL and BOOTSTRAP_TOKEN in Render environment settings.
- Online production mode refuses to start on SQLite or with local sample switching enabled. The initial administrator is scoped to the baseline plant. Operational people/location/work permissions remain enforced by the API.

## Verification before this push

Nine integration tests passed, including hosted setup, one-time setup closure, password login, cookie flags, lockout, role restrictions and workflow persistence. TypeScript, the Vite production build and targeted lint passed. The Docker image could not be built locally because Docker is not installed; the first Render build and live PostgreSQL deployment must still be checked.
