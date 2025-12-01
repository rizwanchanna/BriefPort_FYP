import smtplib
from fastapi import HTTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sources.config import settings

def send_email_verification(to_email: str, username: str, token: str):
    subject = "Verify your email"
    verify_url = f"{settings.FRONT_LINK}/verify-email?token={token}" 

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 500px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
          <h2 style="color: #000;">Hi {username},</h2>
          <p>We received a request to VERIFY your account.</p>
          <p style="text-align: center; padding: 10px;">
            <a href="{verify_url}" style="display: inline-block; padding: 10px 20px; color: white; background-color: #3897f0; text-decoration: none; border-radius: 5px;">
              Verify Account
            </a>
          </p>
          <p>If you didn’t request this, you can safely ignore this email.</p>
          <p style="margin-top: 20px; font-size: 12px; color: #999;">This link will expire in 1 minute.</p>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_EMAIL, to_email, msg.as_string())
    except Exception as e:
        print("Error sending email:", e)
        raise HTTPException(status_code=500, detail="Failed to send email")

def send_password_reset_email(to_email: str, username: str, token: str):
    subject = "Reset Your Password"
    reset_link = f"{settings.FRONT_LINK}/reset-password?token={token}"

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 500px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
          <h2 style="color: #000;">Hi {username},</h2>
          <p>We received a request to RESET your password.</p>
          <p>
            <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; color: white; background-color: #3897f0; text-decoration: none; border-radius: 5px;">
              Reset Password
            </a>
          </p>
          <p>If you didn’t request this, you can safely ignore this email.</p>
          <p style="margin-top: 20px; font-size: 12px; color: #999;">This link will expire in 1 minute.</p>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_EMAIL, to_email, msg.as_string())
    except Exception as e:
        print("Error sending email:", e)
        raise HTTPException(status_code=500, detail="Failed to send email")
