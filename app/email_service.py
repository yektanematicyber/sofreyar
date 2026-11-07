import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("safreyar.email")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER or "noreply@safreyar.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "سفره‌یار (Safreyar)")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() in ("true", "1", "yes")


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Sends a password reset email using SMTP in the background.

    If SMTP is not configured in .env, logs the token gracefully without
    crashing the server.
    """
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            "[EMAIL SERVICE] SMTP is not configured in .env. "
            "Password reset token for %s: %s",
            to_email,
            reset_token,
        )
        print(
            f"[EMAIL MOCK] Password reset token for {to_email}: {reset_token}"
        )
        return False

    subject = "بازیابی رمز عبور سفره‌یار"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Tahoma, Arial, sans-serif; background-color: #f7f9fa; margin: 0; padding: 20px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}
            .header {{ text-align: center; border-bottom: 2px solid #eef2f5; padding-bottom: 16px; margin-bottom: 24px; }}
            .header h2 {{ color: #2e7d32; margin: 0; }}
            .content {{ line-height: 1.8; color: #333333; font-size: 14px; text-align: right; }}
            .token-box {{ background: #f0f7f1; border: 1px dashed #2e7d32; border-radius: 8px; padding: 14px; margin: 20px 0; text-align: center; word-break: break-all; font-family: monospace; font-size: 15px; color: #1b5e20; font-weight: bold; }}
            .footer {{ text-align: center; font-size: 12px; color: #888888; margin-top: 30px; border-top: 1px solid #eeeeee; padding-top: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>سفره‌یار</h2>
            </div>
            <div class="content">
                <p>سلام،</p>
                <p>درخواستی برای بازیابی رمز عبور حساب کاربری شما در <strong>سفره‌یار</strong> ثبت شده است.</p>
                <p>توکن بازیابی رمز عبور شما (معتبر تا <strong>۱۵ دقیقه</strong> آینده):</p>
                <div class="token-box">{reset_token}</div>
                <p>این توکن را در صفحه تغییر رمز عبور در اپلیکیشن وارد کنید.</p>
                <p style="color: #d32f2f; font-size: 13px;">اگر شما این درخواست را نداده‌اید، نیازی به انجام کاری نیست و رمز عبور شما تغییری نخواهد کرد.</p>
            </div>
            <div class="footer">
                <p>این پیام به صورت خودکار ارسال شده است، لطفاً به آن پاسخ ندهید.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = (
        f"سلام،\n\n"
        f"توکن بازیابی رمز عبور شما در سفره‌یار:\n{reset_token}\n\n"
        f"این توکن تا ۱۵ دقیقه آینده معتبر است.\n"
        f"اگر شما این درخواست را نداده‌اید، این پیام را نادیده بگیرید."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("[EMAIL SERVICE] Password reset email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("[EMAIL SERVICE] Failed to send email to %s: %s", to_email, str(e))
        return False
