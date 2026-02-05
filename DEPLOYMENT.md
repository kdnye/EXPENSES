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

## 3. Cloud Build trigger flow (current production path)

The Cloud Build trigger defined in `cloudbuild.yaml` deploys Cloud Run in this
exact order:

1. **Build image** using Docker:
   ```bash
   docker build -f Dockerfile -t ${_IMAGE_URI} .
   ```
2. **Push image** to Artifact Registry:
   ```bash
   docker push ${_IMAGE_URI}
   ```
3. **Resolve digest and deploy the same image by digest** to service
   `${_SERVICE}` (currently `expenses`):
   - Resolve digest from `${_IMAGE_URI}`
   - Build immutable deploy reference `${_IMAGE_REPO}@${DIGEST}`
   - Deploy with:
     ```bash
     gcloud run deploy ${_SERVICE} --image=${_IMAGE_REPO}@${DIGEST}
     ```

This ensures the image that was built and pushed is exactly the image revision
deployed to Cloud Run.

## 4. Build and install (local/manual alternatives)

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

## 5. Start command

Use a production WSGI/ASGI runner instead of the development server.
Example Gunicorn-style startup:

```bash
./scripts/start_gunicorn.sh
```

or an equivalent command that invokes the Flask app factory/module used in your
infrastructure.

## 6. Pre-release checklist

Before promoting a release:

1. Run automated tests:
   ```bash
   pytest
   ```
2. Confirm login and password reset pages load
3. Confirm employee expense creation/submission works end-to-end
4. Confirm supervisor review actions (approve/reject) work
5. Confirm admin dashboard access/permissions are correct

## 7. Mandatory post-deploy validation checks

Run these checks after each deploy to `${_SERVICE}` in `${_REGION}` for
`${_PROJECT_ID}`:

1. **Active revision image URI**
   - Verify the deployed image is digest-pinned and not a placeholder image:
     ```bash
     gcloud run services describe "${_SERVICE}" \
       --region="${_REGION}" \
       --project="${_PROJECT_ID}" \
       --format='value(spec.template.spec.containers[0].image)'
     ```
   - Expected format: `${_IMAGE_REPO}@sha256:...`

2. **Environment variable and secret presence**
   - Validate required runtime env vars exist (`ENVIRONMENT`, `FLASK_DEBUG`,
     `STARTUP_DB_CHECKS`, `HEALTHCHECK_REQUIRE_DB`).
   - Validate required secrets are attached (`SECRET_KEY`,
     `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ISSUER`,
     `OIDC_AUDIENCE`, `NETSUITE_SFTP_PASSWORD`,
     `NETSUITE_SFTP_PRIVATE_KEY`, `NETSUITE_SFTP_PRIVATE_KEY_PASSPHRASE`,
     `DATABASE_URL`).

3. **Cloud SQL connection status**
   - Confirm Cloud Run service includes
     `${_CLOUD_SQL_CONNECTION_NAME}` in its Cloud SQL instance connections.

4. **Health endpoint response**
   - Confirm service responds successfully on the health endpoint (and, if
     configured, DB-backed health checks pass):
     ```bash
     curl -fsS "https://<service-url>/health"
     ```

## 8. Post-deploy smoke tests

After deployment:

- Verify health endpoint/home page loads
- Submit a test expense report as an employee user
- Review and approve/reject it as a supervisor user
- Confirm report status updates are visible to the employee

## 9. Troubleshooting placeholder image symptoms

### Symptom

- `verify-deployed-image` fails.
- Deployed image is `gcr.io/cloudrun/placeholder...` or not
  `${_IMAGE_REPO}@sha256:...`.

### Most likely root causes

1. **Missing or incorrect `Dockerfile`**
   - The build step (`docker build -f Dockerfile ...`) failed or built an
     unexpected image.
2. **Wrong `${_IMAGE_URI}`**
   - Build/push target does not match the expected Artifact Registry path.
3. **Wrong `${_SERVICE}`**
   - Deployment updated a different Cloud Run service than intended.
4. **Push/deploy permission failure**
   - Cloud Build service account lacks required permissions to push the image
     or deploy Cloud Run.

When diagnosing, confirm build logs, push logs, digest resolution output, and
`gcloud run services describe "${_SERVICE}"` all reference the same values for
`${_PROJECT_ID}`, `${_REGION}`, `${_IMAGE_URI}`, and `${_IMAGE_REPO}`.

## 10. Security and operations notes

- Store secrets in a secret manager; do not commit secrets to git
- Enforce HTTPS/TLS at the load balancer or ingress layer
- Restrict admin and supervisor access using least-privilege accounts
- Enable application logging/monitoring for workflow and auth failures
- Back up the production database and define a tested restore process

## 11. Rollback strategy

If deployment fails:

1. Roll traffic back to the previous stable image/revision
2. Revert only the failing application change
3. Re-run smoke tests on the restored version
4. Investigate root cause before retrying deployment
