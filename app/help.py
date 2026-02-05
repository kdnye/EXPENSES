"""Help center blueprint providing end-user guidance pages."""

from __future__ import annotations

from typing import Final, List, TypedDict

from flask import Blueprint, render_template


class HelpTopic(TypedDict):
    """Structure describing a help topic listed on the help landing page."""

    slug: str
    title: str
    endpoint: str
    summary: str
    details: list[str]


help_bp = Blueprint("help", __name__)
# Flask blueprint responsible for the ``/help`` section.

HELP_TOPICS: Final[List[HelpTopic]] = [
    {
        "slug": "getting-started",
        "title": "Getting Started",
        "endpoint": "help.getting_started",
        "summary": "Set up your account and learn where to submit expense reports.",
        "details": [
            "Register from the account request page, then wait for administrator approval before your first sign-in.",
            "After login, open My Reports to review past submissions and start a new report.",
            "Keep your profile email and phone current so supervisors can reach you quickly when follow-up is needed.",
        ],
    },
    {
        "slug": "report-submission",
        "title": "Report Submission",
        "endpoint": "help.report_submission",
        "summary": "Build complete expense reports with clear descriptions and totals.",
        "details": [
            "Use New Expense Report to enter date, category, amount, and business purpose for each expense item.",
            "Review totals before submitting so your supervisor sees an accurate request the first time.",
            "Submit only when all required expenses and notes are included, because supervisors evaluate the full report package.",
        ],
    },
    {
        "slug": "supervisor-review",
        "title": "Supervisor Review",
        "endpoint": "help.supervisor_review",
        "summary": "Understand how supervisors assess pending reports and request updates.",
        "details": [
            "Supervisors open the dashboard to view submitted reports assigned to their team.",
            "Each review checks policy alignment, receipt quality, and whether the business purpose supports reimbursement.",
            "If information is missing, supervisors reject with comments so employees can revise and resubmit quickly.",
        ],
    },
    {
        "slug": "approvals",
        "title": "Approvals & Statuses",
        "endpoint": "help.approvals",
        "summary": "Track what each report status means from draft through final decision.",
        "details": [
            "Draft reports are visible only to the employee until submission.",
            "Submitted reports are locked for supervisor review and move to approved or rejected after evaluation.",
            "Use My Reports to monitor status changes and read reviewer feedback before making edits.",
        ],
    },
    {
        "slug": "receipts",
        "title": "Receipts",
        "endpoint": "help.receipts",
        "summary": "Prepare and attach proof-of-purchase documentation that passes review.",
        "details": [
            "Upload clear receipt images that show vendor, date, amount, and payment confirmation.",
            "Combine multi-page receipts before upload when possible so reviewers can verify one expense in one place.",
            "When a receipt is unavailable, add a short explanation in report notes and follow your reimbursement policy.",
        ],
    },
    {
        "slug": "account-management",
        "title": "Account Management",
        "endpoint": "help.account_management",
        "summary": "Maintain secure access with updated profile details and password hygiene.",
        "details": [
            "Update your contact information from settings so approval reminders and support messages reach you.",
            "Use the password reset workflow immediately if you cannot sign in or suspect unauthorized account access.",
            "Contact an administrator when role changes require supervisor or administrator permissions.",
        ],
    },
]
"""Ordered list of help topics displayed in the sidebar navigation."""


def _render_help_page(active_topic: str | None) -> str:
    """Return the help landing page with the requested topic highlighted.

    Args:
        active_topic: URL-friendly slug for the topic that should be displayed in
            the main content area. ``None`` shows the general overview.

    Returns:
        Rendered HTML string produced by :func:`flask.render_template`.
    """

    selected_topic: HelpTopic | None = next(
        (topic for topic in HELP_TOPICS if topic["slug"] == active_topic),
        None,
    )
    return render_template(
        "help/index.html",
        topics=HELP_TOPICS,
        active_topic=active_topic,
        selected_topic=selected_topic,
    )


@help_bp.get("")
@help_bp.get("/")
def help_index() -> str:
    """Display the help landing page without focusing on a specific topic.

    Args:
        None.

    Returns:
        Rendered HTML string from :func:`_render_help_page` and ultimately
        :func:`flask.render_template`.
    """

    return _render_help_page(active_topic=None)


@help_bp.get("/getting-started")
def getting_started() -> str:
    """Show the "Getting Started" topic content within the help center.

    Args:
        None.

    Returns:
        Rendered HTML string from :func:`_render_help_page` with the
        ``getting-started`` topic highlighted and rendered by
        :func:`flask.render_template`.
    """

    return _render_help_page(active_topic="getting-started")


@help_bp.get("/report-submission")
def report_submission() -> str:
    """Show report creation and submission guidance.

    Returns:
        Rendered HTML string from :func:`_render_help_page` with the
        ``report-submission`` topic highlighted and rendered by
        :func:`flask.render_template`.
    """

    return _render_help_page(active_topic="report-submission")


@help_bp.get("/supervisor-review")
def supervisor_review() -> str:
    """Show the supervisor-side review lifecycle guidance.

    Returns:
        Rendered HTML string from :func:`_render_help_page` with the
        ``supervisor-review`` topic highlighted and rendered by
        :func:`flask.render_template`.
    """

    return _render_help_page(active_topic="supervisor-review")


@help_bp.get("/approvals")
def approvals() -> str:
    """Explain report status transitions for approvals and rejections.

    Returns:
        Rendered HTML string from :func:`_render_help_page` with the
        ``approvals`` topic highlighted and rendered by
        :func:`flask.render_template`.
    """

    return _render_help_page(active_topic="approvals")


@help_bp.get("/receipts")
def receipts() -> str:
    """Share receipt collection best practices for expense compliance.

    Returns:
        Rendered HTML string from :func:`_render_help_page` with the
        ``receipts`` topic highlighted and rendered by
        :func:`flask.render_template`.
    """

    return _render_help_page(active_topic="receipts")


@help_bp.get("/expense-workflow")
def expense_workflow() -> str:
    """Render the full expense reporting workflow quick-reference guide.

    Returns:
        Rendered HTML string produced directly from the
        ``help/expense_workflow.html`` template via :func:`flask.render_template`.
    """

    return render_template("help/expense_workflow.html")


@help_bp.get("/account-management")
def account_management() -> str:
    """Explain how to update profile information and secure an account.

    Args:
        None.

    Returns:
        Rendered HTML string from :func:`_render_help_page` with the
        ``account-management`` topic highlighted and rendered by
        :func:`flask.render_template`.
    """

    return _render_help_page(active_topic="account-management")


@help_bp.get("/admin")
def admin() -> str:
    """Outline administrator workflows for managing approvals and permissions.

    The view renders a standalone administrator guide that covers approval
    queues, role management, and policy checkpoints. It relies on
    :func:`flask.render_template` to display the ``templates/help/admin.html``
    document.

    Returns:
        Rendered HTML string for the administrator help page.
    """

    return render_template("help/admin.html")


@help_bp.get("/password-reset")
def password_reset_guide() -> str:
    """Provide a step-by-step walkthrough for password recovery.

    The view surfaces end-user documentation that explains how the
    :func:`app.auth.reset_request` and :func:`app.auth.reset_with_token` views
    work together. It relies on :func:`flask.render_template` to display the
    ``templates/help/password_reset.html`` article that guides users through
    requesting a reset link and setting a new password.

    Args:
        None.

    Returns:
        Rendered HTML string for the password reset help page.
    """

    return render_template("help/password_reset.html")


@help_bp.get("/register")
def account_setup_guide() -> str:
    """Render the detailed account setup walkthrough.

    The view provides long-form documentation for new users who need help
    completing the registration form. It relies on
    :func:`flask.render_template` to display the
    ``templates/help/register.html`` article.

    Args:
        None.

    Returns:
        Rendered HTML string for the account setup help page.
    """

    return render_template("help/register.html")
