"""Integration tests for expense endpoints that depend on the workbook template."""

from pathlib import Path

import openpyxl

from app import create_app
from app.models import User, db
import app.services.expense_workflow as expense_workflow


class TestConfig:
    """Minimal Flask configuration for expense endpoint integration tests.

    Inputs:
        None. Flask reads class attributes when ``app.create_app`` calls
        ``Flask.config.from_object``.

    Outputs:
        Configuration values that keep tests isolated with an in-memory SQLite
        database and disable startup checks that depend on external services.

    External dependencies:
        Used by :func:`app.create_app` as the configuration object.
    """

    TESTING = True
    SECRET_KEY = "test-secret"
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STARTUP_DB_CHECKS = False


def _build_runtime_workbook(workbook_path: Path) -> None:
    """Create a minimal workbook with required worksheets for expense routes.

    Inputs:
        workbook_path: Filesystem location where the template workbook will be
            written.

    Outputs:
        None. Writes an XLSX file to ``workbook_path`` containing ``GL Accounts``
        and ``Data List`` sheets consumed by the expense workflow loaders.

    External dependencies:
        Calls :func:`openpyxl.Workbook` and ``Workbook.save``.
    """

    workbook = openpyxl.Workbook()

    gl_accounts_sheet = workbook.active
    gl_accounts_sheet.title = "GL Accounts"
    gl_accounts_sheet.append(["Account", "Label"])
    gl_accounts_sheet.append(["6100", "Travel Expense"])

    data_list_sheet = workbook.create_sheet("Data List")
    data_list_sheet.append(["Expense Type"])
    data_list_sheet.append(["Meals"])

    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(workbook_path)
    workbook.close()


def test_expense_endpoints_load_template_from_runtime_location(tmp_path) -> None:
    """Verify workbook-dependent endpoints succeed for approved employees.

    Inputs:
        tmp_path: Pytest-provided temporary directory used as the simulated
            runtime root.

    Outputs:
        None. Asserts that ``/expenses/new`` and ``/expenses/gl-accounts`` both
        return HTTP 200 when a workbook exists at the expected runtime path.

    External dependencies:
        * Calls :func:`app.create_app`.
        * Uses :mod:`app.models.db` to create and seed users.
        * Calls expense workflow helpers via route handlers in
          :mod:`app.expenses`.
    """

    runtime_root = tmp_path / "app"
    workbook_path = runtime_root / "expense_report_template.xlsx"
    _build_runtime_workbook(workbook_path)

    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()

        # Remove maintenance-mode guard injected during app startup so this
        # test can exercise endpoints after creating database tables.
        app.before_request_funcs[None] = [
            func
            for func in app.before_request_funcs.get(None, [])
            if getattr(func, "__name__", "") != "_setup_failed"
        ]

        employee = User(
            email="employee@example.com",
            first_name="Test",
            last_name="Employee",
            password_hash="hashed",
            role="employee",
            employee_approved=True,
        )
        supervisor = User(
            email="supervisor@example.com",
            first_name="Test",
            last_name="Supervisor",
            password_hash="hashed",
            role="employee",
            employee_approved=True,
        )
        db.session.add_all([employee, supervisor])
        db.session.commit()

        expense_workflow._workbook_path.cache_clear()
        expense_workflow.load_gl_accounts.cache_clear()
        expense_workflow.load_expense_types.cache_clear()

        original_workbook_path_loader = expense_workflow._workbook_path

        def _runtime_workbook_path() -> Path:
            """Return the temporary runtime workbook path for this test.

            Inputs:
                None.

            Outputs:
                The path to the workbook created by
                :func:`_build_runtime_workbook`.

            External dependencies:
                None.
            """

            return workbook_path

        expense_workflow._workbook_path = _runtime_workbook_path

        try:
            client = app.test_client()
            with client.session_transaction() as session:
                session["_user_id"] = str(employee.id)
                session["_fresh"] = True

            new_expense_response = client.get("/expenses/new")
            gl_accounts_response = client.get("/expenses/gl-accounts")

            assert new_expense_response.status_code == 200
            assert gl_accounts_response.status_code == 200
            assert gl_accounts_response.json == {
                "accounts": [{"account": "6100", "label": "6100 - Travel Expense"}]
            }
        finally:
            expense_workflow._workbook_path = original_workbook_path_loader
            expense_workflow.load_gl_accounts.cache_clear()
            expense_workflow.load_expense_types.cache_clear()
