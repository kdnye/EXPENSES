# Employee Expense Reporting App

This repository contains a Flask-based **employee expense reporting application**.
It helps employees submit expense reports, supervisors review and approve them,
and administrators manage access and policy settings.

## What the app does

- Employee authentication (register, sign in, reset password)
- Expense report creation and submission
- Supervisor line-by-line review and approval workflow
- Admin dashboards for user and settings management
- Audit-friendly persistence of submitted reports and status changes

## Architecture overview

### Application modules

- `app/flask_app.py`: Flask app wiring and blueprint registration
- `app/auth.py`: authentication, registration, and password reset flows
- `app/expenses.py`: employee and supervisor expense-report routes
- `app/admin.py`: administrator-only user/settings pages
- `app/help.py`: help-center routes and expense workflow documentation
- `app/services/expense_workflow.py`: business logic for report submission and approval lifecycle
- `app/models.py`: SQLAlchemy models for users and expense reporting records

### UI templates

- `templates/expenses/`: employee report creation/list and supervisor review screens
- `templates/help/`: onboarding, password reset, and expense-process guidance
- `templates/auth/`: account administration and permission management UI

## Route map and permissions

### Public routes

- `/` - landing page
- `/register` - account request form
- `/login` - sign-in page

### Authenticated employee routes

- `/expenses/my-reports` - list personal expense reports and statuses
- `/expenses/new` - create and submit expense reports

### Authenticated supervisor routes

- `/expenses/supervisor-dashboard` - queue of reports awaiting review
- `/expenses/review/<report_id>` - approve or reject with feedback

### Administrator routes

- `/admin/` - admin dashboard
- `/admin/users` and related user-management routes
- `/settings` - application settings and policy-related configuration

### Help routes

- `/help/` - help center home
- `/help/expense-workflow` - end-to-end expense reporting quick reference
- `/help/password-reset` - password reset walkthrough
- `/help/register` - account setup guide

## Runtime dependency: expense workbook template

The expense submission routes depend on a runtime workbook file named
`expense_report_template.xlsx`.

- Expected location: repository/runtime root next to the `app/` package
  (for this codebase, that resolves to `<deploy_root>/expense_report_template.xlsx`).
- Required sheets: `GL Accounts` and `Data List`.

If this file is missing, inaccessible, or malformed, `/expenses/new` and
`/expenses/gl-accounts` will return controlled `503 Service Unavailable`
responses so operators can correct deployment configuration.

## Onboarding checklist

1. Register a new account from `/register`.
2. Wait for administrator approval and role assignment.
3. Sign in at `/login`.
4. Open `/expenses/my-reports` and create your first report.
5. Attach receipts and submit for supervisor review.
6. Track status updates until approved or revise if rejected.

## Local development

1. Use **Python 3.8+**.
2. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Configure environment variables (`.env`) for database, secret key, and app settings.
4. Run database setup/migrations as needed.
5. Start the app locally:
   ```bash
   python flask_app.py
   ```
6. Open the app in your browser and navigate to the expense reporting pages.

## Testing

Run the full test suite before committing:

```bash
pytest
```

## Additional docs

- [ARCHITECTURE.md](ARCHITECTURE.md): technical architecture focused on expense reporting
- [DEPLOYMENT.md](DEPLOYMENT.md): deployment guide for production environments
