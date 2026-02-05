# Employee Expense Reporting App

This repository contains a Flask-based **employee expense reporting application**.
It helps employees submit expense reports, supervisors review and approve them,
and administrators manage policy, users, and system settings.

> Note: The codebase also contains legacy freight-quote modules. The primary
> product direction documented here is the employee expense workflow.

## What the app does

- Employee authentication (register, sign in, reset password)
- Expense report creation and submission
- Supervisor review and approval workflow
- Admin dashboards for user and settings management
- Audit-friendly persistence of submitted reports and status changes

## Core user flows

1. **Employee submits a report**
   - Create a new expense report
   - Add expense details and submit for review
2. **Supervisor reviews**
   - View pending reports
   - Approve or reject with feedback
3. **Employee tracks status**
   - Monitor report status and review outcomes

## Project structure

- `flask_app.py`, `app.py`, `expenses.py`: application entrypoints and expense routes
- `services/expense_workflow.py`: workflow logic for report lifecycle actions
- `templates/expenses/`: employee and supervisor expense UI templates
- `models.py`: persistence models used by authentication and expense workflows
- `tests/`: automated tests, including expense workflow and form validation coverage

## Local development

1. Use **Python 3.8+**
2. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Configure environment variables (`.env`) for database, secret key, and app settings
4. Run database setup/migrations as needed
5. Start the app locally:
   ```bash
   python flask_app.py
   ```
6. Open the app in your browser and navigate to the expense reporting pages

## Testing

Run the full test suite before committing:

```bash
pytest
```

## Additional docs

- [ARCHITECTURE.md](ARCHITECTURE.md): technical architecture focused on expense reporting
- [DEPLOYMENT.md](DEPLOYMENT.md): deployment guide for running this app in production
