# Maintenance and upgrade guide

## Before deploying this revision

1. Back up PostgreSQL and verify restoration before changing a live installation.
2. Create a random `SECRET_KEY` of at least 50 characters and a new database
   password. The previous preproduction values were committed to source control;
   replace any installations that used them. Set `DEBUG=0`, explicit
   `ALLOWED_HOSTS`, and HTTPS `CSRF_TRUSTED_ORIGINS`.
3. Run `python manage.py migrate`. This includes allauth upgrades and
   `iam.0002_oidcidentity`. Django is now on the supported 5.2 LTS branch.
4. **Bind existing SSO accounts before their next login.** As a superuser, use
   the Django admin OIDC Identity screen to associate the exact provider issuer
   and stable subject (`sub`) with the existing Django user. Obtain the subject
   from the trusted provider's administration console, not a user-supplied email.
   Without a binding, first login provisions a separate account; existing data
   remain with the old user. Email-based automatic linking has been removed.
   Federation with multiple external issuers requires a separate reviewed flow;
   the primary OIDC backend accepts only its configured issuer.
5. Existing signed-cookie sessions become invalid: users must sign in again.
   Sessions now live in PostgreSQL and logout invalidates them on the server.
   Run `python manage.py clearsessions` regularly through your scheduler.
6. Configure `N8N_WEBHOOK_SECRET` to accept inbound webhooks. Without it, the
   endpoint is intentionally unavailable (503); an incorrect secret returns 403.
7. Approve integration origins explicitly:
   - `ICAL_ALLOWED_ORIGINS=https://calendar.example.com` (HTTPS origins only).
   - `ADAPTER_ALLOWED_ORIGINS=https://plane.example.com,http://mealie:9000`
     for administrator-trusted integration endpoints.
   - `ADAPTER_ALLOWED_FILES=/exports/superproductivity.json` for exact,
     administrator-managed local export files.
   Lists are comma-separated, without wildcard, path or trailing slash. Empty
   lists deny custom remote/local sources. Redirecting providers need their
   final URL configured. Approve only trusted domains and services, and apply
   network egress controls as defense in depth. Existing configurations outside
   these lists need operator approval before synchronization resumes.
8. Build the frontend (`npm ci && npm run build`) or rebuild the Docker image.
   Node 24 replaces the unsupported Node 20 build image. Uvicorn replaces Daphne,
   removing the vulnerable Twisted dependency from the runtime.

## Proxy and runtime

The provided Compose setup terminates TLS at Caddy. Django trusts
`X-Forwarded-Proto` only when `TRUST_PROXY_HEADERS=1`; set it only behind a trusted
proxy that overwrites this header. Do not expose the ASGI port to untrusted
clients in that configuration. Uvicorn does not independently trust proxy headers.
Only the credential-free `/api/v1/health/` endpoint is exempt from HTTPS redirect.
HSTS applies to the application host; preload and all-subdomain coverage are
intentionally not imposed on domains the application does not control.

The web entrypoint migrates and collects static assets, failing on errors.
Worker commands bypass those web startup steps. For rolling deployments, run
migrations as a separate release step before starting workers. OIDC identity
bindings and new sessions must be considered when planning a rollback.

CalDAV supports local and application passwords. Create application passwords
through IAM for SSO users; expired, revoked and inactive-user credentials are
rejected. Legacy bcrypt application passwords created by older code should be
reissued using the current password API.

## Dependencies

`requirements.txt` records direct dependencies. `requirements.lock` pins the
complete runtime resolution for Python 3.12 on Linux. Regenerate deliberately:

```bash
python scripts/lock-requirements.py
pip install -r requirements.lock
pip check
pip-audit -r requirements.lock
```

Run backend tests and frontend checks after each update. `npm ci` uses the
committed npm lockfile. GitHub Actions are pinned to reviewed commit hashes;
refresh those hashes when updating CI actions. Audit results reflect the advisory
catalog at execution time and do not certify application security.
