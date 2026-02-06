"""Expense workflow helpers for spreadsheet lookups, uploads, and dispatch."""

from __future__ import annotations

import csv
import io
import os
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Mapping, Sequence, Tuple

import openpyxl
import paramiko
from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.models import ExpenseReport


class ExpenseReferenceDataError(RuntimeError):
    """Raised when the runtime expense reference workbook cannot be consumed.

    Inputs:
        message: Operator-facing guidance that explains why workbook access
            failed and how to remediate the runtime deployment.

    Outputs:
        A domain-specific exception consumed by route handlers to avoid
        unhandled 500 errors for workbook-related failures.

    External dependencies:
        None.
    """


@dataclass(frozen=True)
class GLAccountOption:
    """Searchable GL account option sourced from the reference workbook."""

    account: str
    label: str


@lru_cache(maxsize=1)
def _workbook_path() -> Path:
    """Return the canonical workbook path used to mirror spreadsheet workflows."""

    return Path(current_app.root_path).parent / "expense_report_template.xlsx"


def _load_reference_workbook(*, required_sheet: str) -> openpyxl.Workbook:
    """Load the shared workbook and return it when the required sheet exists.

    Inputs:
        required_sheet: Worksheet name that must be available for the caller,
            such as ``GL Accounts`` or ``Data List``.

    Outputs:
        An open :class:`openpyxl.workbook.workbook.Workbook` object in
        read-only mode. Callers must close it after reading values.

    External dependencies:
        * Calls :func:`app.services.expense_workflow._workbook_path` to resolve
          the expected runtime path.
        * Calls :func:`openpyxl.load_workbook` to read spreadsheet data.
    """

    workbook_path = _workbook_path()
    expected_sheets = ("GL Accounts", "Data List")

    try:
        workbook = openpyxl.load_workbook(
            workbook_path,
            read_only=True,
            data_only=True,
        )
    except (
        FileNotFoundError,
        openpyxl.utils.exceptions.InvalidFileException,
        OSError,
    ) as exc:
        raise ExpenseReferenceDataError(
            "Expense reference workbook could not be loaded. "
            f"Expected file: '{workbook_path}'. "
            f"Required sheets: {', '.join(expected_sheets)}. "
            "Ensure the workbook exists and is a valid .xlsx file on the "
            "application host."
        ) from exc

    try:
        workbook[required_sheet]
    except KeyError as exc:
        workbook.close()
        raise ExpenseReferenceDataError(
            "Expense reference workbook is missing required sheet data. "
            f"Expected file: '{workbook_path}'. "
            f"Required sheets: {', '.join(expected_sheets)}. "
            "Verify the deployed workbook matches the template structure."
        ) from exc

    return workbook


@lru_cache(maxsize=1)
def load_gl_accounts() -> Tuple[GLAccountOption, ...]:
    """Read GL account values from the workbook ``GL Accounts`` sheet."""

    workbook = _load_reference_workbook(required_sheet="GL Accounts")
    sheet = workbook["GL Accounts"]
    values: List[GLAccountOption] = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        account = str(row[0] or "").strip()
        label = str(row[1] or "").strip()
        if not account:
            continue
        display = f"{account} - {label}" if label else account
        values.append(GLAccountOption(account=account, label=display))
    workbook.close()
    return tuple(values)


@lru_cache(maxsize=1)
def load_expense_types() -> Tuple[str, ...]:
    """Read standardized expense types from the workbook ``Data List`` sheet."""

    workbook = _load_reference_workbook(required_sheet="Data List")
    sheet = workbook["Data List"]
    values: List[str] = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        candidate = str(row[0] or "").strip()
        if candidate:
            values.append(candidate)
    workbook.close()
    return tuple(values)


def upload_receipt_to_cloud_storage(
    file_storage: FileStorage,
    *,
    report_id: int,
    line_index: int,
) -> str:
    """Upload a receipt image to GCS and return its URL.

    This function calls ``google.cloud.storage.Client`` when the
    ``EXPENSE_RECEIPT_BUCKET`` configuration is present.
    """

    if not file_storage or not file_storage.filename:
        return ""

    bucket_name = (current_app.config.get("EXPENSE_RECEIPT_BUCKET") or "").strip()
    if not bucket_name:
        return ""

    from google.cloud import storage  # Imported lazily to keep startup fast.

    safe_name = secure_filename(file_storage.filename)
    extension = Path(safe_name).suffix.lower()
    unique_name = (
        f"expense-receipts/{report_id}/{line_index}-{uuid.uuid4().hex}{extension}"
    )

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(unique_name)
    blob.upload_from_file(
        file_storage.stream,
        content_type=file_storage.content_type or "application/octet-stream",
    )
    blob.make_public()
    return blob.public_url


def apply_line_item_review_actions(
    report: ExpenseReport,
    *,
    decisions: Mapping[int, Tuple[str, str]],
) -> Tuple[str, str]:
    """Update expense lines and report status based on line-level decisions.

    Inputs:
        report: The :class:`app.models.ExpenseReport` instance being reviewed.
        decisions: Mapping of expense line identifiers to a tuple containing the
            selected action (``"approve"`` or ``"reject"``) and reviewer notes.

    Outputs:
        A two-item tuple containing the flash message and category that the
        caller should present to the user interface.

    External dependencies:
        Mutates ``report`` and its ``lines`` in-place. The caller must commit
        the database session after invoking this helper.
    """

    if not report.lines:
        raise ValueError("This report has no expense lines to review.")

    any_rejected = False

    for line in report.lines:
        decision = decisions.get(line.id)
        if not decision:
            raise ValueError("Select approve or reject for every expense line.")

        action, comment = decision
        normalized_action = action.strip().lower()
        trimmed_comment = comment.strip()

        if normalized_action == "approve":
            line.review_status = "Approved"
            line.review_comment = None
            continue

        if normalized_action == "reject":
            if not trimmed_comment:
                raise ValueError(
                    "Provide a rejection comment for each rejected expense line."
                )
            line.review_status = "Rejected"
            line.review_comment = trimmed_comment
            any_rejected = True
            continue

        raise ValueError("Select a valid review action for every expense line.")

    if any_rejected:
        report.status = "Draft"
        report.rejection_comment = "Line-level feedback provided."
        return "Report returned to draft with line-level feedback.", "info"

    report.status = "Pending Upload"
    report.rejection_comment = None
    return "All expense lines approved. Report queued for NetSuite upload.", "success"


def format_pending_reports_csv(reports: Sequence[ExpenseReport]) -> str:
    """Serialize ``Pending Upload`` reports into a single NetSuite-ready CSV."""

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "report_id",
            "employee_email",
            "supervisor_email",
            "expense_date",
            "expense_type",
            "gl_account",
            "vendor",
            "description",
            "amount",
            "receipt_url",
        ]
    )

    for report in reports:
        for line in report.lines:
            if getattr(line, "review_status", "Approved") != "Approved":
                continue
            writer.writerow(
                [
                    report.id,
                    getattr(report.employee, "email", ""),
                    getattr(report.supervisor, "email", ""),
                    line.date.isoformat(),
                    line.expense_type,
                    line.gl_account,
                    line.vendor,
                    line.description or "",
                    f"{line.amount:.2f}",
                    line.receipt_url or "",
                ]
            )

    return output.getvalue()


def dispatch_csv_via_sftp(payload: str, *, filename: str) -> None:
    """Transmit a generated expense export to the configured NetSuite SFTP host."""

    host = (current_app.config.get("NETSUITE_SFTP_HOST") or "").strip()
    username = (current_app.config.get("NETSUITE_SFTP_USERNAME") or "").strip()
    password = (current_app.config.get("NETSUITE_SFTP_PASSWORD") or "").strip()
    remote_dir = (current_app.config.get("NETSUITE_SFTP_DIRECTORY") or "/").strip()
    port = int(current_app.config.get("NETSUITE_SFTP_PORT", 22))

    if not host or not username or not password:
        raise ValueError("NetSuite SFTP credentials are not fully configured.")

    transport = paramiko.Transport((host, port))
    try:
        transport.connect(username=username, password=password)
        client = paramiko.SFTPClient.from_transport(transport)
        remote_path = f"{remote_dir.rstrip('/')}/{filename}"
        with client.file(remote_path, "w") as remote_file:
            remote_file.write(payload)
    finally:
        transport.close()
