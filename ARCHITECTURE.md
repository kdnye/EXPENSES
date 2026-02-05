# Architecture Overview (Employee Expense Reporting App)

This document describes the architecture of the employee expense reporting
system in this repository.

## 1. Purpose

The application supports a role-based expense lifecycle:

- **Employees** create and submit expense reports
- **Supervisors** review, approve, or reject reports
- **Administrators** manage users, configuration, and operational settings

## 2. High-level architecture

The app follows a layered Flask architecture:

1. **Web/UI layer**
   - Flask routes and Jinja templates render employee/supervisor/admin pages
2. **Workflow/service layer**
   - Encapsulates business rules for expense submission and review transitions
3. **Data layer**
   - SQLAlchemy models persist users, reports, and related workflow data

## 3. Main components

### Application entrypoints

- `flask_app.py` and `app.py` initialize Flask app behavior and route wiring

### Expense module

- `expenses.py` provides route handlers for expense reporting pages and actions
- `services/expense_workflow.py` contains business logic for report state changes

### Authentication and authorization

- `auth.py` and `services/auth_utils.py` support registration, login, and password reset
- Role checks control access to employee, supervisor, and admin capabilities

### Persistence

- `models.py` defines database models used by auth and expense workflows
- `database.py` and configuration modules provide DB initialization and connectivity

### Templates

- `templates/expenses/new_expense.html`: employee report creation form
- `templates/expenses/my_reports.html`: employee status/history view
- `templates/expenses/supervisor_dashboard.html`: supervisor queue and actions
- `templates/expenses/review_report.html`: detailed review page

## 4. Request flow (expense report)

1. Employee opens the new expense page
2. Employee submits report data
3. Route validates input and calls workflow services
4. Workflow layer persists report and sets initial state
5. Supervisor dashboard loads pending reports
6. Supervisor approves/rejects and workflow service updates state/history
7. Employee sees updated status in their report list

## 5. Cross-cutting concerns

- **Validation:** Form and workflow validation prevent invalid transitions
- **Security:** Session-based auth, password hashing, role-based access checks
- **Observability:** Server logs and error handling support operational monitoring
- **Maintainability:** Business logic separated from route handlers for easier testing

## 6. Testing strategy

The repository uses `pytest` for automated coverage.

Key focus areas:

- Expense workflow behavior (`tests/test_expense_workflow.py`)
- Expense form validation (`tests/test_expenses_form_validation.py`)
- Environment/server configuration behavior (`tests/test_server_config.py`,
  `tests/test_config_secret_env_mapping.py`)

## 7. Notes on legacy modules

The repository includes legacy freight-related quoting code. Those modules are
not the primary architecture target in this document. This architecture summary
focuses on the employee expense reporting product surface and workflow.
