"""Expense management routes for employee submission and supervisor review."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import List

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from .models import ExpenseLine, ExpenseReport, User, db
from .policies import employee_required, super_admin_required
from app.services.expense_workflow import (
    dispatch_csv_via_sftp,
    format_pending_reports_csv,
    load_expense_types,
    load_gl_accounts,
    upload_receipt_to_cloud_storage,
)

expenses_bp = Blueprint("expenses", __name__, template_folder="templates")


@expenses_bp.route("/new", methods=["GET", "POST"])
@login_required
@employee_required(approved_only=True)
def new_expense() -> str | Response:
    """Render and process new expense report entry using dynamic line items."""

    supervisors = (
        User.query.filter(
            User.id != current_user.id, User.role.in_(["employee", "super_admin"])
        )
        .order_by(User.first_name.asc(), User.last_name.asc())
        .all()
    )
    gl_accounts = load_gl_accounts()
    expense_types = load_expense_types()

    if request.method == "POST":
        supervisor_id_raw = (request.form.get("supervisor_id") or "").strip()
        report_month_raw = (request.form.get("report_month") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        submit_action = (request.form.get("submit_action") or "save_draft").strip()

        try:
            supervisor_id = int(supervisor_id_raw)
        except ValueError:
            flash("Select a valid supervisor.", "warning")
            return redirect(url_for("expenses.new_expense"))

        supervisor = User.query.get(supervisor_id)
        if not supervisor:
            flash("Selected supervisor was not found.", "warning")
            return redirect(url_for("expenses.new_expense"))

        try:
            report_month = (
                datetime.strptime(report_month_raw, "%Y-%m").date().replace(day=1)
            )
        except ValueError:
            flash("Choose a valid report month.", "warning")
            return redirect(url_for("expenses.new_expense"))

        dates = request.form.getlist("line_date")
        types = request.form.getlist("expense_type")
        gls = request.form.getlist("gl_account")
        vendors = request.form.getlist("vendor")
        descriptions = request.form.getlist("description")
        amounts = request.form.getlist("amount")

        if not dates:
            flash("Add at least one expense line.", "warning")
            return redirect(url_for("expenses.new_expense"))

        report_status = (
            "Pending Review" if submit_action == "submit_review" else "Draft"
        )
        report = ExpenseReport(
            employee_id=current_user.id,
            supervisor_id=supervisor_id,
            report_month=report_month,
            notes=notes,
            status=report_status,
        )
        db.session.add(report)
        db.session.flush()

        for index, line_date_raw in enumerate(dates):
            if not line_date_raw.strip():
                continue
            try:
                line_date = datetime.strptime(line_date_raw.strip(), "%Y-%m-%d").date()
            except ValueError:
                db.session.rollback()
                flash(f"Line {index + 1}: invalid date.", "warning")
                return redirect(url_for("expenses.new_expense"))

            try:
                amount = Decimal(
                    (amounts[index] if index < len(amounts) else "0").strip()
                )
            except (InvalidOperation, AttributeError):
                db.session.rollback()
                flash(f"Line {index + 1}: amount must be numeric.", "warning")
                return redirect(url_for("expenses.new_expense"))

            receipt_file = request.files.get(f"receipt_{index}")
            receipt_url = upload_receipt_to_cloud_storage(
                receipt_file,
                report_id=report.id,
                line_index=index,
            )

            line = ExpenseLine(
                expense_report_id=report.id,
                date=line_date,
                expense_type=(types[index] if index < len(types) else "").strip(),
                gl_account=(gls[index] if index < len(gls) else "").strip(),
                vendor=(vendors[index] if index < len(vendors) else "").strip(),
                description=(
                    descriptions[index] if index < len(descriptions) else ""
                ).strip(),
                amount=amount,
                receipt_url=receipt_url,
            )
            db.session.add(line)

        db.session.commit()
        flash("Expense report saved.", "success")
        return redirect(url_for("expenses.my_reports"))

    return render_template(
        "expenses/new_expense.html",
        supervisors=supervisors,
        gl_accounts=gl_accounts,
        expense_types=expense_types,
        reference_workbook="Dave Alexander Expense Report 12.12.2023.xlsx",
    )


@expenses_bp.route("/mine")
@login_required
@employee_required(approved_only=True)
def my_reports() -> str:
    """List reports submitted by the currently authenticated employee."""

    reports = (
        ExpenseReport.query.filter_by(employee_id=current_user.id)
        .order_by(ExpenseReport.created_at.desc())
        .all()
    )
    return render_template("expenses/my_reports.html", reports=reports)


@expenses_bp.route("/supervisor")
@login_required
@employee_required(approved_only=True)
def supervisor_dashboard() -> str:
    """Show only reports awaiting review by the logged-in supervisor."""

    reports = (
        ExpenseReport.query.filter_by(
            supervisor_id=current_user.id, status="Pending Review"
        )
        .order_by(ExpenseReport.created_at.asc())
        .all()
    )
    return render_template("expenses/supervisor_dashboard.html", reports=reports)


@expenses_bp.route("/supervisor/report/<int:report_id>", methods=["GET", "POST"])
@login_required
@employee_required(approved_only=True)
def review_report(report_id: int) -> str | Response:
    """Allow supervisors to approve/reject pending reports with comments."""

    report = ExpenseReport.query.get_or_404(report_id)
    if report.supervisor_id != current_user.id:
        flash("You are not assigned to this report.", "danger")
        return redirect(url_for("expenses.supervisor_dashboard"))

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        comment = (request.form.get("comment") or "").strip()

        if action == "reject" and not comment:
            flash("Rejection comment is required.", "warning")
            return redirect(url_for("expenses.review_report", report_id=report_id))

        if action == "approve":
            report.status = "Pending Upload"
            report.rejection_comment = None
            flash("Report approved and queued for NetSuite upload.", "success")
        elif action == "reject":
            report.status = "Draft"
            report.rejection_comment = comment
            flash("Report rejected and returned to employee draft status.", "info")
        else:
            flash("Select a valid review action.", "warning")
            return redirect(url_for("expenses.review_report", report_id=report_id))

        db.session.add(report)
        db.session.commit()
        return redirect(url_for("expenses.supervisor_dashboard"))

    return render_template("expenses/review_report.html", report=report)


@expenses_bp.route("/export/pending-upload.csv")
@login_required
@super_admin_required
def export_pending_upload_csv() -> Response:
    """Export all reports in ``Pending Upload`` status into one CSV file."""

    reports = (
        ExpenseReport.query.filter_by(status="Pending Upload")
        .order_by(ExpenseReport.id.asc())
        .all()
    )
    payload = format_pending_reports_csv(reports)
    return send_file(
        BytesIO(payload.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="netsuite-expense-upload.csv",
    )


@expenses_bp.route("/dispatch", methods=["POST"])
@login_required
@super_admin_required
def dispatch_pending_uploads() -> Response:
    """Send ``Pending Upload`` reports via SFTP and mark them as completed."""

    reports = ExpenseReport.query.filter_by(status="Pending Upload").all()
    if not reports:
        flash("No reports are waiting for upload.", "info")
        return redirect(url_for("expenses.supervisor_dashboard"))

    payload = format_pending_reports_csv(reports)
    filename = f"netsuite-expenses-{date.today().isoformat()}.csv"
    dispatch_csv_via_sftp(payload, filename=filename)

    for report in reports:
        report.status = "Completed"
        db.session.add(report)
    db.session.commit()

    flash(
        f"Dispatched {len(reports)} reports to NetSuite and marked completed.",
        "success",
    )
    return redirect(url_for("expenses.supervisor_dashboard"))
