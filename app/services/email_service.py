import resend
from app.config import settings


def send_verification_code(to_email: str, code: str) -> bool:
    """Send 6-digit verification code via Resend. Returns True on success."""
    print(f"[EMAIL] Attempting to send code to {to_email}")
    print(f"[EMAIL] RESEND_API_KEY present: {bool(settings.RESEND_API_KEY)}, starts: {settings.RESEND_API_KEY[:8] if settings.RESEND_API_KEY else 'EMPTY'}")
    print(f"[EMAIL] FROM_EMAIL: {settings.FROM_EMAIL}")

    if not settings.RESEND_API_KEY:
        print(f"[DEV] Verification code for {to_email}: {code}")
        return True

    resend.api_key = settings.RESEND_API_KEY

    try:
        result = resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"Your verification code: {code}",
            "html": (
                f'<div style="font-family:sans-serif;max-width:400px;margin:0 auto;padding:32px;">'
                f'<h2 style="color:#111;margin-bottom:8px;">Verification Code</h2>'
                f'<p style="color:#555;margin-bottom:24px;">Enter this code to verify your email:</p>'
                f'<div style="background:#f4f4f5;border-radius:12px;padding:20px;text-align:center;">'
                f'<span style="font-size:32px;font-weight:700;letter-spacing:8px;color:#111;">{code}</span>'
                f'</div>'
                f'<p style="color:#999;font-size:13px;margin-top:24px;">This code expires in 10 minutes.</p>'
                f'<p style="color:#999;font-size:13px;">If you didn\'t request this, ignore this email.</p>'
                f'</div>'
            ),
        })
        print(f"[EMAIL] Send result: {result}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email to {to_email}: {type(e).__name__}: {e}")
        return False


def send_password_reset_code(to_email: str, code: str) -> bool:
    """Send password reset code via Resend."""
    if not settings.RESEND_API_KEY:
        print(f"[DEV] Password reset code for {to_email}: {code}")
        return True

    resend.api_key = settings.RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"Password reset code: {code}",
            "html": (
                f'<div style="font-family:sans-serif;max-width:400px;margin:0 auto;padding:32px;">'
                f'<h2 style="color:#111;margin-bottom:8px;">Password Reset</h2>'
                f'<p style="color:#555;margin-bottom:24px;">Enter this code to reset your password:</p>'
                f'<div style="background:#f4f4f5;border-radius:12px;padding:20px;text-align:center;">'
                f'<span style="font-size:32px;font-weight:700;letter-spacing:8px;color:#111;">{code}</span>'
                f'</div>'
                f'<p style="color:#999;font-size:13px;margin-top:24px;">This code expires in 10 minutes.</p>'
                f'<p style="color:#999;font-size:13px;">If you didn\'t request this, ignore this email.</p>'
                f'</div>'
            ),
        })
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send reset email to {to_email}: {e}")
        return False
