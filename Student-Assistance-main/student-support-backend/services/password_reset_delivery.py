import os
import smtplib
from email.message import EmailMessage


def _is_truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _smtp_settings():
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "").strip(),
        "use_tls": _is_truthy(os.getenv("SMTP_USE_TLS", "true")),
        "use_ssl": _is_truthy(os.getenv("SMTP_USE_SSL", "false")),
        "frontend_base_url": os.getenv("FRONTEND_BASE_URL", "").strip(),
    }


def email_delivery_ready():
    cfg = _smtp_settings()
    return bool(cfg["host"] and cfg["from_email"])


def _send_email(recipient_email, subject, body_lines):
    cfg = _smtp_settings()
    if not email_delivery_ready():
        return {
            "sent": False,
            "reason": "missing_smtp_config",
            "message": "SMTP is not configured",
        }

    recipient_email = (recipient_email or "").strip()
    if not recipient_email:
        return {
            "sent": False,
            "reason": "missing_recipient_email",
            "message": "No recipient email found",
        }

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_email"]
    msg["To"] = recipient_email
    msg.set_content("\n".join(body_lines))

    try:
        use_ssl = cfg["use_ssl"] or cfg["port"] == 465
        if use_ssl:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as server:
                if cfg["username"] and cfg["password"]:
                    server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                server.ehlo()
                if cfg["use_tls"]:
                    server.starttls()
                    server.ehlo()
                if cfg["username"] and cfg["password"]:
                    server.login(cfg["username"], cfg["password"])
                server.send_message(msg)

        return {"sent": True, "reason": "email_sent"}
    except Exception as e:
        return {"sent": False, "reason": "email_error", "message": str(e)}


def send_password_reset_email(recipient_email, reset_token, expires_in_minutes, audience="student"):
    cfg = _smtp_settings()

    audience_name = "Student" if audience == "student" else "Admin"
    reset_link = ""
    if cfg["frontend_base_url"]:
        base = cfg["frontend_base_url"].rstrip("/")
        if audience == "student":
            reset_link = f"{base}/login"
        else:
            reset_link = f"{base}/admin/login"

    subject = f"{audience_name} Password Reset Token"
    body_lines = [
        f"Hello {audience_name},",
        "",
        "We received a password reset request for your account.",
        f"Reset token: {reset_token}",
        f"This token will expire in {expires_in_minutes} minutes.",
        "",
        "Use this token in the Forgot Password section of the login page.",
    ]
    if reset_link:
        body_lines.extend(["", f"Login page: {reset_link}"])
    body_lines.extend(["", "If you did not request this, you can ignore this email."])

    return _send_email(recipient_email, subject, body_lines)


def send_smtp_test_email(recipient_email, requested_by="admin"):
    body_lines = [
        "Hello,",
        "",
        "This is a test email from the AI Student Support System.",
        f"Requested by: {requested_by or 'admin'}",
        "If you received this message, SMTP configuration is working correctly.",
    ]
    return _send_email(
        recipient_email=recipient_email,
        subject="SMTP Test Email - AI Student Support",
        body_lines=body_lines,
    )
