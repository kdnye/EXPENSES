"""Administrative interface for managing users and rate tables.

This module defines the Flask blueprint that powers the web-based admin
dashboard. Views allow administrators to manage user accounts, settings,
and cost-zone rate data used by the expense platform.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence, Union

import pandas as pd
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    FloatField,
    IntegerField,
    RadioField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional

from .scripts.import_air_rates import save_unique
from .models import (
    AppSetting,
    CostZone,
    ExpenseReport,
    User,
    db,
)
from . import csrf
from .policies import employee_required, super_admin_required
from app.services.expense_workflow import apply_line_item_review_actions
from app.services.rate_sets import (
    DEFAULT_RATE_SET,
    get_available_rate_sets,
    normalize_rate_set,
)
from app.services.settings import get_settings_cache, reload_overrides, set_setting

admin_bp = Blueprint("admin", __name__, template_folder="templates")


def _pending_review_reports() -> List[ExpenseReport]:
    """Return expense reports that are awaiting supervisor review.

    Inputs:
        None.

    Outputs:
        A list of :class:`app.models.ExpenseReport` records ordered by oldest
        submission first so the admin dashboard can surface priority reviews.

    External dependencies:
        * Queries :class:`app.models.ExpenseReport` via SQLAlchemy to filter on
          ``status="Pending Review"``.
    """

    return (
        ExpenseReport.query.filter_by(status="Pending Review")
        .order_by(ExpenseReport.created_at.asc())
        .all()
    )


def _sync_admin_role(
    user: User,
    is_admin: bool,
    previous_role: str | None = None,
    previous_employee_approved: bool | None = None,
) -> None:
    """Ensure :class:`~app.models.User` role flags stay in sync with the UI.

    Args:
        user: Persisted account modified by the admin dashboard.
        is_admin: Checkbox value submitted from the form or action handler.
        previous_role: Stored non-admin role to restore when ``is_admin`` is
            ``False``. When omitted the helper falls back to
            :attr:`user.admin_previous_role` or ``"customer"``.
        previous_employee_approved: Stored ``employee_approved`` flag that
            should be reinstated when demoting an administrator. Defaults to the
            cached value on :class:`~app.models.User` when not provided.

    Returns:
        None. The helper mutates ``user.role`` and ``user.employee_approved`` so
        that super administrators always carry the correct privileges and users
        revert to their prior roles when demoted.

    External dependencies:
        * Relies on :class:`~app.models.User` for persisted state, including the
          ``admin_previous_role`` and ``admin_previous_employee_approved``
          columns introduced to remember the user's last non-admin role.
    """

    stored_role = previous_role
    if stored_role is None:
        if user.role != "super_admin":
            stored_role = user.role
        else:
            stored_role = user.admin_previous_role

    stored_employee_flag = previous_employee_approved
    if stored_employee_flag is None:
        if user.role != "super_admin":
            stored_employee_flag = user.employee_approved
        else:
            stored_employee_flag = user.admin_previous_employee_approved

    if is_admin:
        fallback_role = stored_role or user.admin_previous_role or "customer"
        if user.role != "super_admin":
            user.admin_previous_role = (
                fallback_role if fallback_role != "super_admin" else "customer"
            )
            user.admin_previous_employee_approved = stored_employee_flag
        elif user.admin_previous_role is None:
            user.admin_previous_role = (
                fallback_role if fallback_role != "super_admin" else "customer"
            )
        if user.admin_previous_employee_approved is None:
            user.admin_previous_employee_approved = stored_employee_flag
        user.role = "super_admin"
        user.employee_approved = True
        return

    if user.role != "super_admin":
        user.admin_previous_role = None
        user.admin_previous_employee_approved = None
        return

    restored_role = user.admin_previous_role or stored_role or "customer"
    if restored_role not in {"customer", "employee"}:
        restored_role = "customer"

    user.role = restored_role

    if restored_role == "employee":
        if user.admin_previous_employee_approved is not None:
            user.employee_approved = user.admin_previous_employee_approved
        elif stored_employee_flag is not None:
            user.employee_approved = stored_employee_flag
        else:
            user.employee_approved = True
    else:
        user.employee_approved = False

    user.admin_previous_role = None
    user.admin_previous_employee_approved = None


class CostZoneForm(FlaskForm):
    """Form for managing :class:`~app.models.CostZone` records."""

    concat = StringField("Concat", validators=[DataRequired()])
    cost_zone = StringField("Cost Zone", validators=[DataRequired()])


class AppSettingForm(FlaskForm):
    """Form for creating and editing :class:`AppSetting` overrides."""

    key = StringField("Key", validators=[DataRequired()])
    value = TextAreaField("Value", validators=[Optional()])
    is_secret = BooleanField("Mark value as secret")


class CSVUploadForm(FlaskForm):
    """Form for uploading CSV files to populate rate tables."""

    file = FileField(
        "CSV File",
        validators=[FileRequired(), FileAllowed(["csv"], "CSV files only!")],
    )
    action = RadioField(
        "Upload Mode",
        choices=[
            ("add", "Add rows to existing data"),
            ("replace", "Replace existing data"),
        ],
        default="add",
        validators=[DataRequired()],
    )


def _parse_rate_set(
    raw_value: Any,
    *,
    available_sets: Iterable[str] | None = None,
    allow_new_rate_sets: bool = False,
) -> str:
    """Normalize and validate a ``rate_set`` identifier.

    Args:
        raw_value: User-supplied value, often from a form field or CSV cell.
        available_sets: Optional collection of allowed values. When omitted the
            available sets are fetched from :func:`services.rate_sets.get_available_rate_sets`.
        allow_new_rate_sets: When ``True`` accepts identifiers that are not yet
            present in ``available_sets`` after normalization.

    Returns:
        Normalized rate set string.

    Raises:
        ValueError: If ``raw_value`` is missing or not in ``available_sets``
            when ``allow_new_rate_sets`` is ``False``.
    """

    normalized = normalize_rate_set(str(raw_value) if raw_value is not None else None)
    known_sets = set(available_sets or get_available_rate_sets())
    if allow_new_rate_sets or normalized in known_sets:
        return normalized
    raise ValueError(f"Unknown rate set '{normalized}'.")


@dataclass(frozen=True)
class ColumnSpec:
    """Describe how a CSV column maps to a model attribute."""

    header: str
    attr: str
    parser: Callable[[Any], Any]
    required: bool = True
    formatter: Callable[[Any], Any] | None = None

    def export(self, obj: Any) -> Any:
        """Return the formatted value for ``obj`` during CSV downloads."""

        value = getattr(obj, self.attr, None)
        if value is None:
            return ""
        return self.formatter(value) if self.formatter else value


@dataclass(frozen=True)
class TableSpec:
    """Configuration describing an admin-managed rate table."""

    name: str
    label: str
    model: type[db.Model]
    columns: Sequence[ColumnSpec]
    list_endpoint: str
    unique_attr: Sequence[str] | str | None = None
    order_by: Any | None = None


def _is_missing(value: Any) -> bool:
    """Return ``True`` when ``value`` represents an empty CSV cell."""

    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _clean_numeric(value: Any) -> float:
    """Normalize numeric strings (``$``/`,``,``/``%``) to ``float`` values."""

    if _is_missing(value):
        raise ValueError("enter a number")
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
        if cleaned == "":
            raise ValueError("enter a number")
        try:
            return float(cleaned)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError("enter a number") from exc
    raise ValueError("enter a number")


def _parse_required_string(value: Any) -> str:
    """Parse a required string value from a CSV cell."""

    if _is_missing(value):
        raise ValueError("enter a value")
    return str(value).strip()


def _parse_required_float(value: Any) -> float:
    """Parse a float-like value, raising ``ValueError`` when missing."""

    return _clean_numeric(value)


def _populate_rate_set_choices(form: FlaskForm) -> List[str]:
    """Attach available rate sets to a form with a ``rate_set`` field.

    Args:
        form: A Flask-WTF form instance that defines a ``rate_set`` attribute.

    Returns:
        The list of available rate set identifiers applied to the form choices.
    """

    available = get_available_rate_sets()
    if hasattr(form, "rate_set"):
        form.rate_set.choices = [(code, code) for code in available]
    return available


def _parse_required_int(value: Any) -> int:
    """Parse a whole number from the CSV cell."""

    number = _clean_numeric(value)
    if not float(number).is_integer():
        raise ValueError("enter a whole number")
    return int(round(number))


def _parse_optional_int(value: Any) -> int | None:
    """Parse an optional integer, returning ``None`` when blank."""

    if _is_missing(value):
        return None
    return _parse_required_int(value)


TABLE_SPECS: Dict[str, TableSpec] = {
    "cost_zones": TableSpec(
        name="cost_zones",
        label="Cost Zones",
        model=CostZone,
        columns=(
            ColumnSpec("Concat", "concat", _parse_required_string),
            ColumnSpec("Cost Zone", "cost_zone", _parse_required_string),
        ),
        list_endpoint="admin.list_cost_zones",
        unique_attr="concat",
        order_by=CostZone.concat,
    ),
}


def _get_table_spec(table: str) -> TableSpec:
    """Look up ``TableSpec`` configuration for ``table`` or abort with 404."""

    spec = TABLE_SPECS.get(table)
    if not spec:
        abort(404)
    return spec


def _parse_csv_rows(file_storage: Any, spec: TableSpec) -> List[db.Model]:
    """Convert uploaded CSV data into model instances for ``spec``."""

    file_storage.stream.seek(0)
    df = pd.read_csv(file_storage)
    df.columns = [str(col).lstrip("\ufeff").strip() for col in df.columns]
    expected_headers = [col.header for col in spec.columns]
    if list(df.columns) != expected_headers:
        expected = ", ".join(expected_headers)
        raise ValueError(f"CSV headers must exactly match: {expected}.")

    df = df.replace({pd.NA: None})
    rows: List[db.Model] = []
    errors: List[str] = []
    for row_index, row in enumerate(df.to_dict(orient="records"), start=2):
        if all(_is_missing(row.get(col.header)) for col in spec.columns):
            continue
        data: Dict[str, Any] = {}
        row_errors: List[str] = []
        for column in spec.columns:
            raw_value = row.get(column.header)
            try:
                parsed = column.parser(raw_value)
            except ValueError as exc:
                row_errors.append(f"{column.header}: {exc}")
                continue
            if column.required and _is_missing(parsed):
                row_errors.append(f"{column.header}: enter a value")
                continue
            data[column.attr] = parsed
        if row_errors:
            errors.append(f"Row {row_index}: {'; '.join(row_errors)}")
            continue
        rows.append(spec.model(**data))

    if errors:
        raise ValueError(" ".join(errors))
    if not rows:
        raise ValueError("No data rows found in the CSV file.")
    return rows


@admin_bp.before_request
def guard_admin() -> None:
    """Apply CSRF protection to mutating requests."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        csrf.protect()


@admin_bp.route("/")
@employee_required()
def dashboard() -> str:
    """Render the admin landing page for staff accounts.

    The :func:`app.policies.employee_required` decorator ensures only
    authenticated super administrators or approved employees reach the view.
    Administrators see the full management dashboard populated with
    :class:`app.models.User` records while approved employees are directed to a
    lightweight panel that links to :func:`quote.admin_view.quotes_html`.

    Inputs:
        None.

    Returns:
        str: Rendered HTML for either ``admin_dashboard.html`` or
        ``admin_employee_dashboard.html`` depending on the caller's role.

    External dependencies:
        * :class:`app.models.User` to populate the administrator table.
        * :class:`app.models.ExpenseReport` to surface pending reviews for
          super administrators.
        * :data:`flask_login.current_user` to branch between templates.
    """

    if getattr(current_user, "role", None) == "super_admin" or getattr(
        current_user, "is_admin", False
    ):
        users = User.query.order_by(User.created_at.desc()).all()
        pending_reports = _pending_review_reports()
        return render_template(
            "admin_dashboard.html",
            users=users,
            pending_reports=pending_reports,
            settings_url=url_for("admin.list_settings"),
        )

    return render_template("admin_employee_dashboard.html")


@admin_bp.route("/reports/<int:report_id>/review", methods=["GET", "POST"])
@super_admin_required
def review_report(report_id: int) -> Union[str, Response]:
    """Review a pending expense report from the admin dashboard.

    Inputs:
        report_id: Unique identifier of the :class:`app.models.ExpenseReport`
            targeted for review.

    Outputs:
        A rendered HTML page for GET requests or a redirect response after
        applying the review decision on POST.

    External dependencies:
        * Calls :func:`app.services.expense_workflow.apply_line_item_review_actions`
          to update line statuses and report status.
        * Uses :class:`app.models.ExpenseReport` to load persisted report data.
        * Writes updates through :data:`app.models.db.session`.
    """

    report = ExpenseReport.query.get_or_404(report_id)
    if report.status != "Pending Review":
        flash("That report is not awaiting review.", "info")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        decisions = {
            line.id: (
                request.form.get(f"line_{line.id}_action") or "",
                request.form.get(f"line_{line.id}_comment") or "",
            )
            for line in report.lines
        }

        try:
            message, category = apply_line_item_review_actions(
                report, decisions=decisions
            )
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("admin.review_report", report_id=report_id))

        db.session.add(report)
        db.session.commit()
        flash(message, category)
        return redirect(url_for("admin.dashboard"))

    return render_template("expenses/review_report.html", report=report)


@admin_bp.route("/settings")
@super_admin_required
def list_settings() -> str:
    """Display persisted configuration overrides."""

    cache = get_settings_cache()
    settings = sorted(cache.values(), key=lambda record: record.key)
    return render_template("admin_settings_index.html", settings=settings)


@admin_bp.route("/settings/new", methods=["GET", "POST"])
@super_admin_required
def create_setting() -> Union[str, Response]:
    """Create a new :class:`AppSetting` record."""

    form = AppSettingForm()
    if form.validate_on_submit():
        key = (form.key.data or "").strip()
        value = form.value.data
        set_setting(key, value, is_secret=form.is_secret.data)
        db.session.commit()
        overrides = reload_overrides(current_app)
        display_key = key.strip().upper()
        flash(
            f"Saved setting {display_key or '(blank)'} ({len(overrides)} active settings).",
            "success",
        )
        return redirect(url_for("admin.list_settings"))

    return render_template("admin_settings_form.html", form=form, setting=None)


@admin_bp.route("/settings/<int:setting_id>/edit", methods=["GET", "POST"])
@super_admin_required
def edit_setting(setting_id: int) -> Union[str, Response]:
    """Edit an existing :class:`AppSetting`."""

    setting = db.session.get(AppSetting, setting_id)
    if not setting:
        abort(404)

    form = AppSettingForm(obj=setting)
    if request.method == "GET":
        form.key.data = setting.key
        form.value.data = setting.value or ""
        form.is_secret.data = setting.is_secret

    if form.validate_on_submit():
        new_key = (form.key.data or "").strip().lower()
        if not new_key:
            form.key.errors.append("Enter a key for the setting.")
            return render_template(
                "admin_settings_form.html", form=form, setting=setting
            )

        conflict = (
            AppSetting.query.filter(
                AppSetting.key == new_key, AppSetting.id != setting.id
            )
            .with_entities(AppSetting.id)
            .first()
        )
        if conflict:
            form.key.errors.append("A setting with that key already exists.")
            return render_template(
                "admin_settings_form.html", form=form, setting=setting
            )

        value = form.value.data
        set_setting(new_key, value, is_secret=form.is_secret.data)
        if new_key != setting.key:
            set_setting(setting.key, None)
        db.session.commit()
        overrides = reload_overrides(current_app)
        flash(
            f"Saved setting {new_key.upper()} ({len(overrides)} active settings).",
            "success",
        )
        return redirect(url_for("admin.list_settings"))

    return render_template("admin_settings_form.html", form=form, setting=setting)


@admin_bp.route("/settings/<int:setting_id>/delete", methods=["POST"])
@super_admin_required
def delete_setting(setting_id: int) -> Response:
    """Delete an :class:`AppSetting` row."""

    setting = db.session.get(AppSetting, setting_id)
    if not setting:
        abort(404)

    key = setting.key
    set_setting(key, None)
    db.session.commit()
    overrides = reload_overrides(current_app)
    flash(
        f"Deleted setting {key.upper()} ({len(overrides)} active settings).",
        "success",
    )
    return redirect(url_for("admin.list_settings"))


@admin_bp.route("/toggle/<int:user_id>", methods=["POST"])
@super_admin_required
def toggle_active(user_id: int) -> Response:
    """Enable or disable a user account.

    Loads the target :class:`User` and toggles its ``is_active`` flag. No
    template is rendered; the view redirects back to the dashboard.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    user.is_active = not user.is_active
    db.session.commit()
    flash("User status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/promote/<int:user_id>", methods=["POST"])
@super_admin_required
def promote(user_id: int) -> Response:
    """Grant administrative privileges to a user.

    Retrieves a :class:`User` instance, sets ``is_admin`` to ``True`` and
    redirects to the dashboard without rendering a template.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    previous_role = (
        user.role
        if user.role != "super_admin"
        else user.admin_previous_role or "customer"
    )
    previous_employee_approved = (
        user.employee_approved
        if user.role != "super_admin"
        else user.admin_previous_employee_approved or False
    )
    user.is_admin = True
    _sync_admin_role(
        user,
        True,
        previous_role=previous_role,
        previous_employee_approved=previous_employee_approved,
    )
    db.session.commit()
    flash("User promoted to admin.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/demote/<int:user_id>", methods=["POST"])
@super_admin_required
def demote(user_id: int) -> Response:
    """Revoke administrative privileges from a user.

    Works on the :class:`User` model and redirects to the dashboard without
    rendering a template.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    previous_role = user.admin_previous_role or (
        user.role if user.role != "super_admin" else "customer"
    )
    previous_employee_approved = (
        user.admin_previous_employee_approved
        if user.admin_previous_employee_approved is not None
        else (user.employee_approved if user.role != "super_admin" else False)
    )
    user.is_admin = False
    _sync_admin_role(
        user,
        False,
        previous_role=previous_role,
        previous_employee_approved=previous_employee_approved,
    )
    db.session.commit()
    flash("User demoted from admin.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/new", methods=["GET", "POST"])
@super_admin_required
def create_user() -> Union[str, Response]:
    """Create a new user account via the admin dashboard.

    Returns:
        Union[str, Response]: Renders the creation form on ``GET`` requests or
        redirects back to the dashboard after persisting the new user. Redirects
        to the form again with a warning flash message when validation fails.

    External dependencies:
        * :data:`flask.request.form` for submitted field values.
        * :func:`flask.flash` to communicate validation errors or success.
        * :class:`app.models.User` and :data:`app.models.db` for persistence.
    """

    available_rate_sets = get_available_rate_sets()
    form_data: Dict[str, Any] = {}
    if request.method == "POST":
        form_data = {
            "email": (request.form.get("email") or "").strip().lower(),
            "first_name": (request.form.get("first_name") or "").strip(),
            "last_name": (request.form.get("last_name") or "").strip(),
            "phone": (request.form.get("phone") or "").strip(),
            "company_name": (request.form.get("company_name") or "").strip(),
            "company_phone": (request.form.get("company_phone") or "").strip(),
            "name": (request.form.get("name") or "").strip(),
            "password": request.form.get("password") or "",
            "role": (request.form.get("role") or "customer").strip(),
            "employee_approved": bool(request.form.get("employee_approved")),
            "rate_set": request.form.get("rate_set") or DEFAULT_RATE_SET,
        }
        display_name = (
            form_data["name"]
            or f"{form_data['first_name']} {form_data['last_name']}".strip()
        )
        rate_set = form_data["rate_set"]
        try:
            rate_set = _parse_rate_set(
                rate_set,
                available_sets=available_rate_sets,
                allow_new_rate_sets=True,
            )
        except ValueError as exc:
            flash(str(exc), "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=None,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        if rate_set not in available_rate_sets:
            available_rate_sets = [*available_rate_sets, rate_set]

        if not form_data["email"] or not form_data["password"]:
            flash("Email and password are required.", "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=None,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        if form_data["role"] not in {"customer", "employee", "super_admin"}:
            flash("Invalid role selected.", "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=None,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        if User.query.filter_by(email=form_data["email"]).first():
            flash("Email already exists.", "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=None,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        is_super_admin = form_data["role"] == "super_admin"
        employee_approved = False
        if form_data["role"] == "employee":
            employee_approved = form_data["employee_approved"]
        elif is_super_admin:
            employee_approved = True

        user = User(
            email=form_data["email"],
            name=display_name,
            first_name=form_data["first_name"] or None,
            last_name=form_data["last_name"] or None,
            phone=form_data["phone"] or None,
            company_name=form_data["company_name"] or None,
            company_phone=form_data["company_phone"] or None,
            is_admin=is_super_admin,
            role=form_data["role"],
            employee_approved=employee_approved,
            rate_set=rate_set,
        )
        user.set_password(form_data["password"])

        if is_super_admin:
            _sync_admin_role(
                user,
                True,
                previous_role="customer",
                previous_employee_approved=True,
            )

        db.session.add(user)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin_user_form.html",
        user=None,
        form_data=form_data,
        available_rate_sets=available_rate_sets,
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@super_admin_required
def edit_user(user_id: int) -> Union[str, Response]:
    """Edit an existing user's details from the admin dashboard.

    Args:
        user_id: Primary key for the :class:`~app.models.User` being updated.

    Returns:
        Union[str, Response]: Renders the edit form on ``GET`` requests. On
        ``POST`` validates input, persists the changes, and redirects back to
        the dashboard. Validation failures redirect back to the edit form with a
        flash message explaining the error.

    External dependencies:
        * :data:`flask.request.form` for submitted field values.
        * :func:`flask.flash` to communicate validation errors or success.
        * :class:`app.models.User` and :data:`app.models.db` for persistence.
    """

    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    available_rate_sets = get_available_rate_sets()
    form_data: Dict[str, Any] = {}
    if request.method == "POST":
        form_data = {
            "email": (request.form.get("email") or "").strip().lower(),
            "first_name": (request.form.get("first_name") or "").strip(),
            "last_name": (request.form.get("last_name") or "").strip(),
            "phone": (request.form.get("phone") or "").strip(),
            "company_name": (request.form.get("company_name") or "").strip(),
            "company_phone": (request.form.get("company_phone") or "").strip(),
            "name": (request.form.get("name") or "").strip(),
            "password": request.form.get("password") or "",
            "role": (request.form.get("role") or "customer").strip(),
            "employee_approved": bool(request.form.get("employee_approved")),
            "rate_set": request.form.get("rate_set") or user.rate_set,
        }
        display_name = (
            form_data["name"]
            or f"{form_data['first_name']} {form_data['last_name']}".strip()
        )

        try:
            parsed_rate_set = _parse_rate_set(
                form_data["rate_set"],
                available_sets=available_rate_sets,
                allow_new_rate_sets=True,
            )
        except ValueError as exc:
            flash(str(exc), "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=user,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        if parsed_rate_set not in available_rate_sets:
            available_rate_sets = [*available_rate_sets, parsed_rate_set]

        if not form_data["email"]:
            flash("Email is required.", "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=user,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        if form_data["role"] not in {"customer", "employee", "super_admin"}:
            flash("Invalid role selected.", "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=user,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        existing = User.query.filter_by(email=form_data["email"]).first()
        if existing and existing.id != user.id:
            flash("Email already exists.", "warning")
            return (
                render_template(
                    "admin_user_form.html",
                    user=user,
                    form_data=form_data,
                    available_rate_sets=available_rate_sets,
                ),
                400,
            )

        previous_role = (
            user.role
            if user.role != "super_admin"
            else user.admin_previous_role or "customer"
        )
        previous_employee_approved = (
            user.employee_approved
            if user.role != "super_admin"
            else user.admin_previous_employee_approved
        )

        employee_approved = False
        if form_data["role"] == "employee":
            employee_approved = form_data["employee_approved"]
        elif form_data["role"] == "super_admin":
            employee_approved = True

        was_super_admin = user.role == "super_admin"
        is_super_admin = form_data["role"] == "super_admin"

        user.email = form_data["email"]
        user.name = display_name
        user.first_name = form_data["first_name"] or None
        user.last_name = form_data["last_name"] or None
        user.phone = form_data["phone"] or None
        user.company_name = form_data["company_name"] or None
        user.company_phone = form_data["company_phone"] or None
        user.rate_set = parsed_rate_set

        if is_super_admin:
            user.is_admin = True
            _sync_admin_role(
                user,
                True,
                previous_role=previous_role,
                previous_employee_approved=previous_employee_approved,
            )
        else:
            user.is_admin = False
            if was_super_admin:
                user.admin_previous_role = None
                user.admin_previous_employee_approved = None
                _sync_admin_role(
                    user,
                    False,
                    previous_role=form_data["role"],
                    previous_employee_approved=employee_approved,
                )
            user.role = form_data["role"]
            user.employee_approved = employee_approved

        if form_data["password"]:
            user.set_password(form_data["password"])

        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin_user_form.html",
        user=user,
        form_data=form_data,
        available_rate_sets=available_rate_sets,
    )


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@super_admin_required
def delete_user(user_id: int) -> Response:
    """Remove a user account."""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/approve_employee/<int:user_id>", methods=["POST"])
@super_admin_required
def approve_employee(user_id: int) -> Response:
    """Mark an employee account as approved for internal tools.

    Args:
        user_id: Primary key of the :class:`app.models.User` being updated.

    Returns:
        Response: Redirect back to :func:`dashboard` after updating the record.

    External dependencies:
        * :func:`flask.flash` to communicate success to the caller.
        * :data:`flask.request.form` for an optional ``next`` redirect target.
        * :mod:`sqlalchemy` session helpers via :func:`db.session.get`.
    """

    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    user.employee_approved = True
    db.session.commit()
    flash("Employee access approved.", "success")

    redirect_target = request.form.get("next") or url_for("admin.dashboard")
    return redirect(redirect_target)


# Cost zone routes
@admin_bp.route("/cost_zones")
@super_admin_required
def list_cost_zones() -> str:
    """List all cost zone mappings."""

    zones = CostZone.query.order_by(CostZone.id).all()
    return render_template("admin_cost_zones.html", cost_zones=zones)


@admin_bp.route("/cost_zones/new", methods=["GET", "POST"])
@super_admin_required
def new_cost_zone() -> Union[str, Response]:
    """Create a new cost zone mapping."""

    form = CostZoneForm()
    if form.validate_on_submit():
        cz = CostZone(concat=form.concat.data, cost_zone=form.cost_zone.data)
        db.session.add(cz)
        db.session.commit()
        flash("Cost zone created.", "success")
        return redirect(url_for("admin.list_cost_zones"))
    return render_template("admin_cost_zone_form.html", form=form, cost_zone=None)


@admin_bp.route("/cost_zones/<int:cz_id>/edit", methods=["GET", "POST"])
@super_admin_required
def edit_cost_zone(cz_id: int) -> Union[str, Response]:
    """Edit an existing cost zone mapping."""

    cz = db.session.get(CostZone, cz_id)
    if not cz:
        abort(404)
    form = CostZoneForm(obj=cz)
    if form.validate_on_submit():
        cz.concat = form.concat.data
        cz.cost_zone = form.cost_zone.data
        db.session.commit()
        flash("Cost zone updated.", "success")
        return redirect(url_for("admin.list_cost_zones"))
    return render_template("admin_cost_zone_form.html", form=form, cost_zone=cz)


@admin_bp.route("/cost_zones/<int:cz_id>/delete", methods=["POST"])
@super_admin_required
def delete_cost_zone(cz_id: int) -> Response:
    """Delete a cost zone mapping."""

    cz = db.session.get(CostZone, cz_id)
    if not cz:
        abort(404)
    db.session.delete(cz)
    db.session.commit()
    flash("Cost zone deleted.", "success")
    return redirect(url_for("admin.list_cost_zones"))


@admin_bp.route("/<string:table>/upload", methods=["GET", "POST"])
@super_admin_required
def upload_csv(table: str) -> Union[str, Response]:
    """Upload a CSV file and either append to or replace a rate table.

    The expected column headers are defined in :data:`TABLE_SPECS`. Uploads
    with mismatched headers are rejected to guarantee the template matches the
    database schema. When appending to tables that have a natural key, such as
    configured with ``unique_attr`` in :data:`TABLE_SPECS`, duplicates are skipped
    using :func:`scripts.import_air_rates.save_unique`.
    """

    spec = _get_table_spec(table)
    form = CSVUploadForm()
    if form.validate_on_submit():
        file_storage = form.file.data
        try:
            objects = _parse_csv_rows(file_storage, spec)
        except (ValueError, pd.errors.EmptyDataError) as exc:
            form.file.errors.append(str(exc))
        else:
            action = form.action.data
            inserted = len(objects)
            skipped = 0
            if action == "replace":
                db.session.query(spec.model).delete(synchronize_session=False)
                db.session.flush()
                db.session.bulk_save_objects(objects)
                message = f"{spec.label} data replaced with {inserted} row(s)."
            else:
                if spec.unique_attr:
                    inserted, skipped = save_unique(
                        db.session, spec.model, objects, spec.unique_attr
                    )
                else:
                    db.session.bulk_save_objects(objects)
                message = f"{spec.label} upload added {inserted} row(s)."
                if spec.unique_attr and skipped:
                    message = (
                        f"{spec.label} upload added {inserted} row(s) "
                        f"({skipped} duplicate row(s) skipped)."
                    )

            db.session.commit()
            flash(message, "success")
            return redirect(url_for(spec.list_endpoint))

    status = 400 if request.method == "POST" else 200
    return (
        render_template(
            "admin_upload.html",
            form=form,
            table=table,
            table_label=spec.label,
            expected_headers=[col.header for col in spec.columns],
            download_url=url_for("admin.download_csv", table=table),
            cancel_url=url_for(spec.list_endpoint),
        ),
        status,
    )


@admin_bp.route("/<string:table>/download")
@super_admin_required
def download_csv(table: str) -> Response:
    """Stream the requested rate table as a CSV template."""

    spec = _get_table_spec(table)
    query = spec.model.query
    if spec.order_by is not None:
        order_by = (
            spec.order_by
            if isinstance(spec.order_by, (list, tuple))
            else (spec.order_by,)
        )
        query = query.order_by(*order_by)
    rows = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    headers = [column.header for column in spec.columns]
    writer.writerow(headers)
    for row in rows:
        writer.writerow([column.export(row) for column in spec.columns])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = (
        f"attachment; filename={spec.name}_template.csv"
    )
    return response
