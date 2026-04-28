"""
Purchase notification service — email and log alerts when users buy from the shop.
Configure NOTIFY_ADMIN_EMAIL and optional SMTP in .env to receive email alerts.
"""
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Admin email to notify (required for email; optional for log-only)
NOTIFY_ADMIN_EMAIL = os.environ.get("NOTIFY_ADMIN_EMAIL", "").strip()

# SMTP for email (optional — if not set, only logs to file)
# Use NOTIFY_SMTP_* to avoid conflict with SFTP_* vars
SMTP_HOST = os.environ.get("NOTIFY_SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("NOTIFY_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("NOTIFY_SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("NOTIFY_SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = os.environ.get("NOTIFY_SMTP_USE_TLS", "true").lower() == "true"

# Log file (always written)
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
PURCHASE_LOG = os.path.join(LOG_DIR, "purchase_notifications.log")


def _ensure_log_dir():
    """Ensure logs directory exists."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError:
        pass


def _log_purchase(
    amount: float,
    currency: str,
    item_id: str,
    item_name: str,
    user_id: str,
    order_id: str,
    coins_granted: int = 0,
    source: str = "paypal",
):
    """Write purchase to log file."""
    _ensure_log_dir()
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    line = (
        f"[{ts}] PURCHASE | amount={amount} {currency} | item={item_id} ({item_name}) | "
        f"user={user_id} | order={order_id} | coins_granted={coins_granted} | source={source}\n"
    )
    try:
        with open(PURCHASE_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def _send_email(subject: str, body: str, to_email: str) -> bool:
    """Send email via SMTP. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception:
        return False


def notify_purchase(
    amount: float,
    currency: str = "USD",
    item_id: str = "",
    item_name: str = "",
    user_id: str = "unknown",
    order_id: str = "",
    coins_granted: int = 0,
    source: str = "paypal",
) -> None:
    """
    Notify admin of a purchase: log to file and optionally send email.
    Call this after a successful PayPal capture or shop purchase.
    """
    _log_purchase(
        amount=amount,
        currency=currency,
        item_id=item_id,
        item_name=item_name,
        user_id=user_id,
        order_id=order_id,
        coins_granted=coins_granted,
        source=source,
    )

    if NOTIFY_ADMIN_EMAIL and amount > 0:
        subject = f"💰 MasterNoder: New purchase ${amount:.2f} {currency}"
        body = (
            f"New purchase on MasterNoder shop:\n\n"
            f"Amount: ${amount:.2f} {currency}\n"
            f"Item: {item_name or item_id or 'N/A'}\n"
            f"User ID: {user_id}\n"
            f"Order ID: {order_id}\n"
            f"Coins granted: {coins_granted}\n"
            f"Source: {source}\n\n"
            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        )
        _send_email(subject, body, NOTIFY_ADMIN_EMAIL)
