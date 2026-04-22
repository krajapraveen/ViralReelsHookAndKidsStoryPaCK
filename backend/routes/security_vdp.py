"""
Vulnerability Disclosure Program (VDP) — Public reporting + admin triage.
Responsible disclosure. Not a public bounty.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request, Form
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import hashlib
import html
import logging
import os
import re
import uuid

from shared import db, get_admin_user

logger = logging.getLogger("vdp")
router = APIRouter(prefix="/security", tags=["security-vdp"])

# ─── Enums ──────────────────────────────────────────────────────────────
STATUS_VALUES = [
    "NEW", "ACKNOWLEDGED", "TRIAGING", "NEED_MORE_INFO", "ACCEPTED",
    "DUPLICATE", "OUT_OF_SCOPE", "INFORMATIVE", "RESOLVED", "CLOSED",
]
SEVERITY_VALUES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CATEGORY_VALUES = [
    "AUTHENTICATION", "AUTHORIZATION", "IDOR", "XSS", "CSRF", "SSRF",
    "RCE", "INJECTION", "FILE_UPLOAD", "INFO_DISCLOSURE",
    "PAYMENT_BILLING", "SESSION_MANAGEMENT", "RATE_LIMIT_BYPASS", "OTHER",
]
REWARD_STATUS = ["NONE", "PENDING", "GRANTED", "REJECTED"]

REWARD_DEFAULTS = {"LOW": 100, "MEDIUM": 300, "HIGH": 700, "CRITICAL": 1500}

# ─── Config ─────────────────────────────────────────────────────────────
SECURITY_INBOXES = [
    "krajapraveen@visionary-suite.com",
    "admin@visionary-suite.com",
]
MAX_FILES = 3
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".txt"}
ALLOWED_MIMES = {
    "image/png", "image/jpeg", "image/jpg",
    "application/pdf", "text/plain",
}

SPAM_PHRASES = [
    "buy now", "click here to win", "viagra", "crypto giveaway",
    "free money", "earn $$$", "seo services", "guest post",
]
DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "tempmail.com",
    "guerrillamail.com", "trashmail.com", "throwaway.email",
}


# ─── Models ─────────────────────────────────────────────────────────────
class ReportSubmission(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    from_email: EmailStr
    subject: str = Field(..., min_length=10, max_length=200)
    category: str
    severity: str
    body: str = Field(..., min_length=50, max_length=10000)
    consent_accepted: bool
    attachment_keys: Optional[List[str]] = []
    honeypot: Optional[str] = ""  # must stay empty


class StatusUpdate(BaseModel):
    status: Optional[str] = None
    internal_severity: Optional[str] = None
    assigned_to: Optional[str] = None
    duplicate_of: Optional[str] = None
    resolution_summary: Optional[str] = None


class AdminNote(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


class RewardGrant(BaseModel):
    credits: Optional[int] = None
    reason: Optional[str] = ""


# ─── Helpers ────────────────────────────────────────────────────────────
def _hash_ip(ip: str) -> str:
    salt = os.environ.get("VDP_IP_SALT", "vs-vdp-default-salt")
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def _sanitize(text: str) -> str:
    """Escape HTML for safe rendering in admin UI."""
    if not text:
        return ""
    return html.escape(text)


def _spam_score(body: str, email: str, subject: str) -> float:
    """Simple heuristic. Returns 0.0–1.0."""
    score = 0.0
    text = f"{subject} {body}".lower()
    # Disposable email domain
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in DISPOSABLE_DOMAINS:
        score += 0.4
    # Spam phrase hits
    hits = sum(1 for p in SPAM_PHRASES if p in text)
    score += min(hits * 0.15, 0.5)
    # Too many links
    link_count = len(re.findall(r"https?://", text))
    if link_count > 8:
        score += 0.2
    # Too short but claimed critical
    if len(body) < 120:
        score += 0.1
    return min(score, 1.0)


async def _next_report_id() -> str:
    """Generate VSR-YYYY-NNNNNN. Monotonic within year."""
    year = datetime.now(timezone.utc).year
    counter = await db.vdp_counters.find_one_and_update(
        {"_id": f"vsr_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = (counter or {}).get("seq", 1) if counter else 1
    # Motor returns pre-update doc with return_document=BEFORE by default; re-fetch to be safe
    if not counter or "seq" not in counter:
        doc = await db.vdp_counters.find_one({"_id": f"vsr_{year}"})
        seq = doc.get("seq", 1) if doc else 1
    return f"VSR-{year}-{seq:06d}"


async def _rate_limit_check(ip_hash: str) -> bool:
    """Return True if allowed. Max 3 submissions per IP / 24h."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    count = await db.security_reports.count_documents({
        "source_ip_hash": ip_hash,
        "created_at": {"$gte": cutoff},
    })
    return count < 3


async def _append_event(report_id: str, event_type: str, actor_type: str, actor_id: Optional[str], metadata: dict):
    await db.security_report_events.insert_one({
        "id": str(uuid.uuid4()),
        "report_id": report_id,
        "event_type": event_type,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def _send_reporter_ack(to_email: str, report_id: str, subject: str):
    try:
        from services.email_service import RESEND_API_KEY, FROM_EMAIL
        if not RESEND_API_KEY:
            logger.warning("[VDP] RESEND_API_KEY missing — reporter ack not sent")
            return
        import resend
        resend.api_key = RESEND_API_KEY
        html_body = f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:560px;margin:0 auto;padding:32px 24px;background:#0B0F1A;color:#e2e8f0;border-radius:12px;">
  <div style="text-align:center;margin-bottom:28px;">
    <div style="display:inline-block;padding:6px 14px;border-radius:999px;background:rgba(139,92,246,0.12);border:1px solid rgba(139,92,246,0.3);font-size:11px;color:#c4b5fd;letter-spacing:0.08em;">SECURITY · RESPONSIBLE DISCLOSURE</div>
  </div>
  <h1 style="font-size:22px;font-weight:800;color:#fff;margin:0 0 12px 0;">Report received</h1>
  <p style="color:#cbd5e1;font-size:14px;line-height:1.6;margin:0 0 20px 0;">Thank you for helping improve Visionary Suite security. Your report has been received and is queued for review by our team.</p>
  <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;margin:16px 0;">
    <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 6px 0;">Report ID</p>
    <p style="color:#fff;font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;margin:0;">{report_id}</p>
  </div>
  <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;margin:16px 0;">
    <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 6px 0;">Subject</p>
    <p style="color:#fff;font-size:14px;margin:0;">{_sanitize(subject)}</p>
  </div>
  <p style="color:#94a3b8;font-size:13px;line-height:1.6;margin:20px 0 0 0;">
    Our team typically acknowledges legitimate reports within 72 hours. Please retain this ID for future communication, and avoid public disclosure until coordinated remediation.
  </p>
  <p style="color:#475569;font-size:11px;text-align:center;margin:28px 0 0 0;">Visionary Suite Security · Responsible Disclosure Program</p>
</div>"""
        resend.Emails.send({
            "from": f"Visionary Suite Security <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": f"Visionary Suite Security Report Received — {report_id}",
            "html": html_body,
        })
        logger.info(f"[VDP] Ack email sent to {to_email[:30]}")
    except Exception as e:
        logger.error(f"[VDP] Reporter ack send failed: {e}")


def _send_admin_alert(report: dict):
    try:
        from services.email_service import RESEND_API_KEY, FROM_EMAIL
        if not RESEND_API_KEY:
            logger.warning("[VDP] RESEND_API_KEY missing — admin alert not sent")
            return
        import resend
        resend.api_key = RESEND_API_KEY
        rid = report.get("report_id")
        subject = report.get("subject", "")
        severity = report.get("severity", "")
        category = report.get("category", "")
        from_email = report.get("from_email", "")
        body_preview = (report.get("body", "") or "")[:800]
        attachment_keys = report.get("attachment_keys", []) or []

        att_html = ""
        if attachment_keys:
            att_rows = "".join([f"<li style='color:#94a3b8;font-size:12px;font-family:monospace;'>{_sanitize(k)}</li>" for k in attachment_keys])
            att_html = f"<p style='color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;margin:16px 0 6px 0;'>Attachments</p><ul style='margin:0;padding-left:20px;'>{att_rows}</ul>"

        html_body = f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:640px;margin:0 auto;padding:28px 24px;background:#0B0F1A;color:#e2e8f0;">
  <div style="display:inline-block;padding:4px 10px;border-radius:6px;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);font-size:11px;color:#fca5a5;letter-spacing:0.08em;margin-bottom:12px;">[{severity}] NEW SECURITY REPORT</div>
  <h1 style="font-size:18px;font-weight:700;color:#fff;margin:0 0 16px 0;">{_sanitize(subject)}</h1>
  <table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
    <tr><td style="color:#94a3b8;padding:6px 0;font-size:12px;width:120px;">Report ID</td><td style="color:#fff;font-family:monospace;font-size:13px;">{rid}</td></tr>
    <tr><td style="color:#94a3b8;padding:6px 0;font-size:12px;">Category</td><td style="color:#fff;font-size:13px;">{category}</td></tr>
    <tr><td style="color:#94a3b8;padding:6px 0;font-size:12px;">Severity</td><td style="color:#fff;font-size:13px;">{severity}</td></tr>
    <tr><td style="color:#94a3b8;padding:6px 0;font-size:12px;">Reporter</td><td style="color:#fff;font-size:13px;">{_sanitize(from_email)}</td></tr>
  </table>
  <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;">
    <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 8px 0;">Body (preview)</p>
    <pre style="white-space:pre-wrap;color:#e2e8f0;font-size:12px;line-height:1.6;margin:0;font-family:inherit;">{_sanitize(body_preview)}</pre>
  </div>
  {att_html}
  <p style="color:#94a3b8;font-size:12px;margin:20px 0 0 0;">Open in admin: <a style="color:#a78bfa;" href="https://www.visionary-suite.com/app/admin/security-reports/{rid}">Admin dashboard</a></p>
</div>"""
        resend.Emails.send({
            "from": f"Visionary Suite Security <{FROM_EMAIL}>",
            "to": SECURITY_INBOXES,
            "subject": f"[Security Report][{severity}] {subject} — {rid}",
            "html": html_body,
        })
        logger.info(f"[VDP] Admin alert sent to {len(SECURITY_INBOXES)} inboxes for {rid}")
    except Exception as e:
        logger.error(f"[VDP] Admin alert send failed: {e}")


# ─── Public endpoints ──────────────────────────────────────────────────

@router.post("/report")
async def submit_report(submission: ReportSubmission, request: Request):
    # Honeypot
    if submission.honeypot:
        logger.info("[VDP] Honeypot triggered — silently accepted")
        return {"success": True, "report_id": "VSR-OK", "message": "Report received."}

    # Consent enforcement
    if not submission.consent_accepted:
        raise HTTPException(status_code=400, detail="You must accept the responsible disclosure policy.")

    # Enum validation
    if submission.category not in CATEGORY_VALUES:
        raise HTTPException(status_code=400, detail="Invalid category")
    if submission.severity not in SEVERITY_VALUES:
        raise HTTPException(status_code=400, detail="Invalid severity")

    # Rate limit
    ip = _client_ip(request)
    ip_hash = _hash_ip(ip)
    if not await _rate_limit_check(ip_hash):
        raise HTTPException(status_code=429, detail="Too many submissions from your network. Please try again in 24 hours.")

    # Attachment sanity (keys are R2 keys previously uploaded)
    attachment_keys = (submission.attachment_keys or [])[:MAX_FILES]

    # Duplicate hash — same body content
    body_hash = hashlib.sha256(submission.body.strip().lower().encode()).hexdigest()

    spam = _spam_score(submission.body, submission.from_email, submission.subject)
    is_spam = spam >= 0.7

    report_id = await _next_report_id()
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "report_id": report_id,
        "full_name": submission.full_name.strip(),
        "from_email": submission.from_email.lower(),
        "to_email": ", ".join(SECURITY_INBOXES),
        "subject": submission.subject.strip(),
        "body": submission.body.strip(),
        "category": submission.category,
        "severity": submission.severity,
        "reported_severity": submission.severity,
        "internal_severity": None,
        "attachment_keys": attachment_keys,
        "body_hash": body_hash,
        "consent_accepted": True,
        "status": "NEW",
        "assigned_to": None,
        "duplicate_of": None,
        "resolution_summary": None,
        "reward_status": "NONE",
        "reward_amount": 0,
        "reward_granted_at": None,
        "source_ip_hash": ip_hash,
        "user_agent": (request.headers.get("user-agent", "") or "")[:500],
        "spam_score": spam,
        "is_spam": is_spam,
        "created_at": now,
        "updated_at": now,
        "acknowledged_at": None,
        "resolved_at": None,
    }
    await db.security_reports.insert_one(doc)
    # Strip _id for event metadata
    await _append_event(report_id, "REPORT_CREATED", "PUBLIC", None, {
        "category": submission.category, "severity": submission.severity, "is_spam": is_spam
    })

    # Send emails (fire-and-forget, but we log failures)
    try:
        _send_reporter_ack(submission.from_email, report_id, submission.subject)
        _send_admin_alert(doc)
    except Exception as e:
        logger.error(f"[VDP] Email dispatch error: {e}")

    return {
        "success": True,
        "report_id": report_id,
        "message": "Your report has been received.",
    }


@router.post("/attachment/upload")
async def upload_attachment(file: UploadFile = File(...)):
    """Public attachment upload for report form. Private R2 storage."""
    filename = file.filename or "upload.bin"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Use png, jpg, jpeg, pdf, txt.")
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        # Browsers sometimes send octet-stream for txt — accept ext-only in that case
        if file.content_type != "application/octet-stream":
            raise HTTPException(status_code=400, detail="Invalid content type.")

    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        from services.cloudflare_r2_storage import CloudflareR2Storage
        storage = CloudflareR2Storage()
        if not storage.is_configured:
            raise HTTPException(status_code=503, detail="Storage not available.")
        # Date-partitioned project_id
        now = datetime.now(timezone.utc)
        partition = f"{now.year}/{now.month:02d}"
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)[:80]
        success, public_url, key = await storage.upload_bytes(
            data, "security_report", safe_name, partition
        )
        if not success:
            raise HTTPException(status_code=500, detail="Upload failed.")
        return {"success": True, "file_key": key, "filename": safe_name, "size": len(data)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VDP] Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed.")


# ─── Admin endpoints ───────────────────────────────────────────────────

@router.get("/admin/reports")
async def admin_list_reports(
    admin: dict = Depends(get_admin_user),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    reward_status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
):
    query = {}
    if status and status in STATUS_VALUES:
        query["status"] = status
    if severity and severity in SEVERITY_VALUES:
        query["$or"] = [{"internal_severity": severity}, {"severity": severity}]
    if category and category in CATEGORY_VALUES:
        query["category"] = category
    if reward_status and reward_status in REWARD_STATUS:
        query["reward_status"] = reward_status
    if search:
        query["$or"] = [
            {"subject": {"$regex": re.escape(search), "$options": "i"}},
            {"from_email": {"$regex": re.escape(search), "$options": "i"}},
            {"report_id": {"$regex": re.escape(search), "$options": "i"}},
        ]
    total = await db.security_reports.count_documents(query)
    reports = await db.security_reports.find(
        query, {"_id": 0, "body": 0, "user_agent": 0, "source_ip_hash": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"success": True, "total": total, "reports": reports}


@router.get("/admin/reports/stats")
async def admin_stats(admin: dict = Depends(get_admin_user)):
    total = await db.security_reports.count_documents({})
    new = await db.security_reports.count_documents({"status": "NEW"})
    triaging = await db.security_reports.count_documents({"status": "TRIAGING"})
    accepted = await db.security_reports.count_documents({"status": "ACCEPTED"})
    resolved = await db.security_reports.count_documents({"status": "RESOLVED"})
    critical = await db.security_reports.count_documents({
        "$or": [{"internal_severity": "CRITICAL"}, {"severity": "CRITICAL"}],
        "status": {"$nin": ["RESOLVED", "CLOSED", "DUPLICATE", "OUT_OF_SCOPE"]},
    })
    return {
        "total": total, "new": new, "triaging": triaging,
        "accepted": accepted, "resolved": resolved, "open_critical": critical,
    }


@router.get("/admin/reports/{report_id}")
async def admin_get_report(report_id: str, admin: dict = Depends(get_admin_user)):
    report = await db.security_reports.find_one({"report_id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    events = await db.security_report_events.find(
        {"report_id": report_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    notes = await db.security_report_notes.find(
        {"report_id": report_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(200)

    # Generate presigned URLs for attachments
    attachment_urls = []
    keys = report.get("attachment_keys") or []
    if keys:
        try:
            from services.cloudflare_r2_storage import CloudflareR2Storage
            storage = CloudflareR2Storage()
            if storage.is_configured:
                for k in keys:
                    try:
                        url = storage._client.generate_presigned_url(
                            "get_object",
                            Params={"Bucket": os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod"), "Key": k},
                            ExpiresIn=600,
                        )
                        attachment_urls.append({"key": k, "url": url})
                    except Exception as e:
                        logger.warning(f"[VDP] Presign failed for {k}: {e}")
                        attachment_urls.append({"key": k, "url": None})
        except Exception as e:
            logger.error(f"[VDP] Attachment presign init failed: {e}")

    return {
        "success": True, "report": report, "events": events,
        "notes": notes, "attachments": attachment_urls,
    }


@router.patch("/admin/reports/{report_id}")
async def admin_update_report(report_id: str, update: StatusUpdate, admin: dict = Depends(get_admin_user)):
    report = await db.security_reports.find_one({"report_id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    changes = {}
    events = []

    if update.status is not None:
        if update.status not in STATUS_VALUES:
            raise HTTPException(status_code=400, detail="Invalid status")
        if update.status != report.get("status"):
            changes["status"] = update.status
            events.append(("STATUS_CHANGED", {"from": report.get("status"), "to": update.status}))
            if update.status == "ACKNOWLEDGED":
                changes["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
            elif update.status == "RESOLVED":
                changes["resolved_at"] = datetime.now(timezone.utc).isoformat()

    if update.internal_severity is not None:
        if update.internal_severity not in SEVERITY_VALUES:
            raise HTTPException(status_code=400, detail="Invalid severity")
        if update.internal_severity != report.get("internal_severity"):
            changes["internal_severity"] = update.internal_severity
            events.append(("SEVERITY_CHANGED", {"to": update.internal_severity}))

    if update.assigned_to is not None:
        changes["assigned_to"] = update.assigned_to or None
        events.append(("OWNER_ASSIGNED", {"to": update.assigned_to}))

    if update.duplicate_of is not None:
        changes["duplicate_of"] = update.duplicate_of or None
        events.append(("DUPLICATE_LINKED", {"of": update.duplicate_of}))

    if update.resolution_summary is not None:
        changes["resolution_summary"] = update.resolution_summary
        events.append(("RESOLUTION_UPDATED", {"length": len(update.resolution_summary or "")}))

    if not changes:
        return {"success": True, "message": "No changes"}

    changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.security_reports.update_one({"report_id": report_id}, {"$set": changes})
    for etype, meta in events:
        await _append_event(report_id, etype, "ADMIN", admin.get("id"), meta)

    return {"success": True, "changes": changes}


@router.post("/admin/reports/{report_id}/notes")
async def admin_add_note(report_id: str, note: AdminNote, admin: dict = Depends(get_admin_user)):
    report = await db.security_reports.find_one({"report_id": report_id}, {"_id": 0, "report_id": 1})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    doc = {
        "id": str(uuid.uuid4()),
        "report_id": report_id,
        "note": note.note.strip(),
        "created_by": admin.get("id"),
        "created_by_email": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.security_report_notes.insert_one({**doc})
    await _append_event(report_id, "NOTE_ADDED", "ADMIN", admin.get("id"), {"length": len(note.note)})
    doc.pop("_id", None)
    return {"success": True, "note": doc}


@router.post("/admin/reports/{report_id}/grant-reward")
async def admin_grant_reward(report_id: str, grant: RewardGrant, admin: dict = Depends(get_admin_user)):
    report = await db.security_reports.find_one({"report_id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.get("reward_status") == "GRANTED":
        raise HTTPException(status_code=400, detail="Reward already granted.")

    severity = report.get("internal_severity") or report.get("severity") or "LOW"
    credits = grant.credits if grant.credits is not None else REWARD_DEFAULTS.get(severity, 100)
    if credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    from_email = (report.get("from_email") or "").lower()
    user = await db.users.find_one({"email": from_email}, {"_id": 0, "id": 1, "email": 1, "credits": 1})

    now = datetime.now(timezone.utc).isoformat()
    user_id = user.get("id") if user else None

    if user_id:
        await db.users.update_one({"id": user_id}, {"$inc": {"credits": credits}})
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "amount": credits,
            "type": "SECURITY_REWARD",
            "reference": report_id,
            "note": grant.reason or f"VDP reward for {report_id}",
            "created_at": now,
        })
        claim_link = None
    else:
        # No account — create a pending claim
        claim_token = str(uuid.uuid4())
        await db.security_reward_claims.insert_one({
            "id": str(uuid.uuid4()),
            "token": claim_token,
            "email": from_email,
            "credits": credits,
            "report_id": report_id,
            "claimed": False,
            "created_at": now,
        })
        claim_link = f"https://www.visionary-suite.com/security/claim/{claim_token}"

    await db.security_reports.update_one(
        {"report_id": report_id},
        {"$set": {
            "reward_status": "GRANTED",
            "reward_amount": credits,
            "reward_granted_at": now,
            "reward_granted_by": admin.get("id"),
            "reward_claim_link": claim_link,
            "updated_at": now,
        }}
    )
    await _append_event(report_id, "REWARD_GRANTED", "ADMIN", admin.get("id"), {
        "credits": credits, "has_account": bool(user_id), "claim_link": claim_link,
    })

    # Congrats email
    try:
        from services.email_service import RESEND_API_KEY, FROM_EMAIL
        if RESEND_API_KEY:
            import resend
            resend.api_key = RESEND_API_KEY
            claim_html = f"""<div style="text-align:center;margin:24px 0;"><a href="{claim_link}" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#8b5cf6,#ec4899);color:white;font-size:16px;font-weight:700;text-decoration:none;border-radius:12px;">Claim Your {credits} Credits</a></div>""" if claim_link else f"""<p style="color:#cbd5e1;font-size:14px;">{credits} credits have been added to your Visionary Suite account.</p>"""
            resend.Emails.send({
                "from": f"Visionary Suite Security <{FROM_EMAIL}>",
                "to": [from_email],
                "subject": f"Thank you — {credits} credits granted for {report_id}",
                "html": f"""<div style="font-family:-apple-system,sans-serif;max-width:560px;margin:0 auto;padding:32px 24px;background:#0B0F1A;color:#e2e8f0;"><h1 style="font-size:22px;color:#fff;">Thank you for your report</h1><p style="color:#cbd5e1;font-size:14px;line-height:1.6;">Your responsible disclosure (<strong style="color:#fff;font-family:monospace;">{report_id}</strong>) has been validated. As a token of appreciation, you've been granted <strong style="color:#fff;">{credits} Visionary Suite credits</strong>.</p>{claim_html}<p style="color:#475569;font-size:11px;text-align:center;margin-top:32px;">Visionary Suite Security · Responsible Disclosure Program</p></div>""",
            })
    except Exception as e:
        logger.error(f"[VDP] Reward email failed: {e}")

    return {
        "success": True, "credits": credits,
        "has_account": bool(user_id), "claim_link": claim_link,
    }


@router.post("/admin/reports/{report_id}/reject-reward")
async def admin_reject_reward(report_id: str, admin: dict = Depends(get_admin_user)):
    report = await db.security_reports.find_one({"report_id": report_id}, {"_id": 0, "reward_status": 1})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.get("reward_status") == "GRANTED":
        raise HTTPException(status_code=400, detail="Already granted, cannot reject")
    now = datetime.now(timezone.utc).isoformat()
    await db.security_reports.update_one(
        {"report_id": report_id},
        {"$set": {"reward_status": "REJECTED", "updated_at": now}}
    )
    await _append_event(report_id, "REWARD_REJECTED", "ADMIN", admin.get("id"), {})
    return {"success": True}


@router.get("/claim/{token}")
async def get_claim(token: str):
    """Public — check if a claim link is valid."""
    claim = await db.security_reward_claims.find_one({"token": token}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Invalid claim link")
    return {
        "valid": not claim.get("claimed"),
        "credits": claim.get("credits"),
        "email": claim.get("email"),
        "report_id": claim.get("report_id"),
    }
