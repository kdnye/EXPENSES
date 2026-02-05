# Deployment Guide (Employee Expense Reporting App)

This document explains how to deploy the employee expense reporting app safely
and consistently.

## 1. Runtime requirements

- Python 3.8+
- A production database reachable by the app
- Environment variable management for secrets/config
- Process manager or container runtime (Gunicorn/Hypercorn, Docker, or Cloud Run)

## 2. Required configuration

Set these values through environment variables or your secret manager:

- `SECRET_KEY`: required for secure session signing
- `DATABASE_URL` (or equivalent SQLAlchemy URI): required database connection
- Mail/settings values used by your environment (if enabled)
- Any app-specific authentication or integration settings in your deployment profile

## 3. Build and install

### Option A: standard host/VM deploy

```bash
pip install -r requirements.txt
```

Run migrations/schema setup required by your environment before first traffic.

### Option B: Docker image

```bash
docker build -t expense-reporting-app:latest .
```

Run with environment variables:

```bash
docker run --rm -p 8080:8080 --env-file .env expense-reporting-app:latest
```

## 4. Start command

Use a production WSGI/ASGI runner instead of the development server.
Example Gunicorn-style startup:

```bash
./scripts/start_gunicorn.sh
```

or an equivalent command that invokes the Flask app factory/module used in your
infrastructure.

## 5. Pre-release checklist

Before promoting a release:

1. Run automated tests:
   ```bash
   pytest
   ```
2. Confirm login and password reset pages load
3. Confirm employee expense creation/submission works end-to-end
4. Confirm supervisor review actions (approve/reject) work
5. Confirm admin dashboard access/permissions are correct

## 6. Post-deploy smoke tests

After deployment:

- Verify health endpoint/home page loads
- Submit a test expense report as an employee user
- Review and approve/reject it as a supervisor user
- Confirm report status updates are visible to the employee

## 7. Security and operations notes

- Store secrets in a secret manager; do not commit secrets to git
- Enforce HTTPS/TLS at the load balancer or ingress layer
- Restrict admin and supervisor access using least-privilege accounts
- Enable application logging/monitoring for workflow and auth failures
- Back up the production database and define a tested restore process

## 8. Rollback strategy

If deployment fails:

1. Roll traffic back to the previous stable image/revision
2. Revert only the failing application change
3. Re-run smoke tests on the restored version
4. Investigate root cause before retrying deployment
