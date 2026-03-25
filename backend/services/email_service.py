"""
Email Nudge Service — Sends retention emails via Resend.
Requires RESEND_API_KEY in backend/.env
"""
import os
import logging

logger = logging.getLogger("creatorstudio.email")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "stories@visionary-suite.com")
APP_URL = os.environ.get("APP_URL", "https://trust-engine-5.preview.emergentagent.com")


def is_email_enabled():
    return bool(RESEND_API_KEY)


async def send_nudge_email(to_email: str, subject: str, character_name: str, cliffhanger: str, link: str):
    """Send a story continuation nudge email."""
    if not RESEND_API_KEY:
        logger.warning("[EMAIL] Resend API key not configured — email not sent")
        return False

    try:
        import resend
        resend.api_key = RESEND_API_KEY

        full_link = f"{APP_URL}{link}" if link.startswith("/") else link
        display_name = character_name or "Your story"

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 20px; background-color: #0a0a0f; color: #e2e8f0;">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="display: inline-block; width: 40px; height: 40px; border-radius: 8px; background: linear-gradient(135deg, #8b5cf6, #ec4899); line-height: 40px; font-size: 18px; color: white; font-weight: bold;">V</div>
            </div>
            <h1 style="font-size: 22px; font-weight: 800; color: #ffffff; text-align: center; margin-bottom: 8px;">{display_name}'s story isn't finished...</h1>
            <div style="background: rgba(245, 158, 11, 0.06); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 12px; padding: 16px; margin: 20px 0; text-align: center;">
                <p style="font-style: italic; color: #fbbf24; font-size: 15px; line-height: 1.6; margin: 0;">"{cliffhanger}"</p>
            </div>
            <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-bottom: 24px;">What happens next might change everything</p>
            <div style="text-align: center; margin-bottom: 32px;">
                <a href="{full_link}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white; font-size: 16px; font-weight: 700; text-decoration: none; border-radius: 12px;">Continue Now</a>
            </div>
            <p style="color: #475569; font-size: 11px; text-align: center;">Made with AI on Visionary Suite</p>
        </div>
        """

        params = {
            "from": f"Visionary Suite <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }

        resend.Emails.send(params)
        logger.info(f"[EMAIL] Sent nudge to {to_email[:20]}... subject='{subject[:40]}'")
        return True

    except Exception as e:
        logger.error(f"[EMAIL] Failed to send to {to_email[:20]}...: {e}")
        return False
