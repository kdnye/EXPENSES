"""Centralizes database table names and SQLAlchemy models for the quoting app.

The module exposes string constants that define the canonical table names used
throughout migrations, raw SQL helpers, and other services. Those constants are
paired with SQLAlchemy models such as :class:`User`,
:class:`EmailQuoteRequest`, and :class:`PasswordResetToken`, which describe the
schema and relationships for their respective tables.
"""

from datetime import datetime
import uuid
from typing import Optional
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped
from werkzeug.security import generate_password_hash, check_password_hash


# Table name constants for easy reuse across the codebase
USERS_TABLE = "users"
EMAIL_REQUESTS_TABLE = "email_quote_requests"
EMAIL_DISPATCH_LOG_TABLE = "email_dispatch_log"
PASSWORD_RESET_TOKENS_TABLE = "password_reset_tokens"
APP_SETTINGS_TABLE = "app_settings"
COST_ZONES_TABLE = "cost_zones"
EXPENSE_REPORTS_TABLE = "expense_reports"
EXPENSE_LINES_TABLE = "expense_lines"

RATE_SET_DEFAULT = "default"

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Registered application user.

    Users can authenticate and submit records in the application. The model stores
    contact information collected during registration to support quoting and
    customer service follow-up.

    Attributes:
        first_name: User's given name collected from the registration form.
        last_name: User's family name collected from the registration form.
        phone: Primary phone number supplied by the user. Stored as free-form
            text because formatting varies by country.
        company_name: Company name associated with the user account.
        company_phone: Contact phone number for the user's company.
        role: Application role flag used to enable privileged employee or
            administrative features. Acceptable values are ``"customer"``,
            ``"employee"``, or ``"super_admin"`` and the field defaults to
            ``"customer"``.
        employee_approved: Boolean gating elevated employee-only features.
            Set to ``True`` when the account has been vetted for internal tool
            access.
        admin_previous_role: Cached role restored when administrative access is
            revoked. Persisted only while :attr:`is_admin` is ``True``.
        admin_previous_employee_approved: Cached ``employee_approved`` value
            restored alongside :attr:`admin_previous_role` when demoting an
            administrator.
    """

    __tablename__ = USERS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120))
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(50))
    company_name = db.Column(db.String(120))
    company_phone = db.Column(db.String(50))
    supervisor_id = db.Column(db.Integer, db.ForeignKey(f"{USERS_TABLE}.id"))
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    role: Mapped[str] = db.Column(
        Enum("customer", "employee", "super_admin", name="user_role"),
        nullable=False,
        default="customer",
    )
    employee_approved: Mapped[bool] = db.Column(Boolean, nullable=False, default=False)
    admin_previous_role: Mapped[Optional[str]] = db.Column(
        Enum("customer", "employee", name="user_admin_previous_role"),
        nullable=True,
    )
    admin_previous_employee_approved: Mapped[Optional[bool]] = db.Column(
        Boolean, nullable=True
    )
    is_active = db.Column(db.Boolean, default=True)
    rate_set = db.Column(
        db.String(50), nullable=False, default=RATE_SET_DEFAULT, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    supervisor = db.relationship(
        "User",
        remote_side=[id],
        backref=db.backref("direct_reports", lazy="dynamic"),
        foreign_keys=[supervisor_id],
    )

    def set_password(self, raw_password: str) -> None:
        """Hash ``raw_password`` using
        :func:`werkzeug.security.generate_password_hash`.

        Args:
            raw_password: Plain text password provided by the user.

        Returns:
            None. The hashed value is stored on ``self.password_hash``.
        """

        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Validate ``raw_password`` against the stored hash using
        :func:`werkzeug.security.check_password_hash`.

        Args:
            raw_password: Plain text password to compare.

        Returns:
            ``True`` when the supplied password matches the stored hash;
            otherwise ``False``.
        """

        return check_password_hash(self.password_hash, raw_password)


class EmailQuoteRequest(db.Model):
    """Supplemental details for a quote submitted via email.

    Stores supplemental shipment details keyed by a ``quote_id`` value.
    """

    __tablename__ = EMAIL_REQUESTS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.String(36), nullable=False, index=True)
    shipper_name = db.Column(db.String)
    shipper_address = db.Column(db.String)
    shipper_contact = db.Column(db.String)
    shipper_phone = db.Column(db.String)
    consignee_name = db.Column(db.String)
    consignee_address = db.Column(db.String)
    consignee_contact = db.Column(db.String)
    consignee_phone = db.Column(db.String)
    total_weight = db.Column(db.Float)
    special_instructions = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmailDispatchLog(db.Model):
    """Audit trail for outbound emails sent by the application.

    Rows are created by :func:`app.send_email` via
    :func:`services.mail.log_email_dispatch` to support rate limiting and
    troubleshooting. Each entry associates an optional :class:`User` with a
    feature label and recipient address.
    """

    __tablename__ = EMAIL_DISPATCH_LOG_TABLE

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f"{USERS_TABLE}.id"))
    feature = db.Column(db.String(50), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")


class AppSetting(db.Model):
    """Database-persisted configuration override.

    Attributes:
        key: Unique identifier for the setting (for example, ``"mail_username"``).
        value: Optional string payload stored for the key.
        is_secret: Flags whether the value should be hidden in administrative UIs.
        created_at: UTC timestamp when the row was created.
        updated_at: UTC timestamp automatically refreshed on modification.
    """

    __tablename__ = APP_SETTINGS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    is_secret = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class PasswordResetToken(db.Model):
    """One-time token used to reset a user's password.

    Associated with a single :class:`User`. The ``token`` column stores the
    SHA-256 digest generated by :func:`services.auth_utils.hash_reset_token` so
    leaked database rows do not expose usable reset links.
    """

    __tablename__ = PASSWORD_RESET_TOKENS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f"{USERS_TABLE}.id"), nullable=False)
    token = db.Column(
        db.String(128), unique=True, nullable=False
    )  # hashed token value (SHA-256 hex digest)
    expires_at = db.Column(db.DateTime, nullable=False)  # UTC expiration timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)
    user = db.relationship("User")


class CostZone(db.Model):
    """Lookup for cost zones based on origin/destination pairs."""

    __tablename__ = COST_ZONES_TABLE

    __table_args__ = (
        UniqueConstraint("rate_set", "concat", name="uq_cost_zones_rate_set_concat"),
    )

    id = db.Column(db.Integer, primary_key=True)
    concat = db.Column(db.String(5), nullable=False)  # concatenated origin/dest key
    cost_zone = db.Column(db.String(5), nullable=False)  # resulting cost zone code
    rate_set = db.Column(
        db.String(50), nullable=False, default=RATE_SET_DEFAULT, index=True
    )


class ExpenseReport(db.Model):
    """Expense report header submitted by an employee.

    Each report groups one or more :class:`ExpenseLine` entries. Supervisors
    review reports as part of a state machine before finance uploads the
    records to NetSuite.
    """

    __tablename__ = EXPENSE_REPORTS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey(f"{USERS_TABLE}.id"), nullable=False
    )
    supervisor_id = db.Column(
        db.Integer, db.ForeignKey(f"{USERS_TABLE}.id"), nullable=False
    )
    report_month = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    status: Mapped[str] = db.Column(
        Enum(
            "Draft",
            "Pending Review",
            "Pending Upload",
            "Completed",
            name="expense_report_status",
        ),
        nullable=False,
        default="Draft",
    )
    rejection_comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    employee = db.relationship("User", foreign_keys=[employee_id])
    supervisor = db.relationship("User", foreign_keys=[supervisor_id])
    lines = db.relationship(
        "ExpenseLine",
        cascade="all, delete-orphan",
        backref="report",
        lazy="joined",
    )


class ExpenseLine(db.Model):
    """Individual expense row attached to an :class:`ExpenseReport`.

    The columns mirror the spreadsheet-driven workflow used by employees for
    monthly reimbursement submissions.
    """

    __tablename__ = EXPENSE_LINES_TABLE

    id = db.Column(db.Integer, primary_key=True)
    expense_report_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{EXPENSE_REPORTS_TABLE}.id"),
        nullable=False,
        index=True,
    )
    date = db.Column(db.Date, nullable=False)
    expense_type = db.Column(db.String(120), nullable=False)
    gl_account = db.Column(db.String(32), nullable=False)
    vendor = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))
    receipt_url = db.Column(db.String(1024))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
