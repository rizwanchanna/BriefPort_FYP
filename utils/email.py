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
      <body style="
        font-family: Arial, sans-serif; 
        color: #222; 
        margin: 0; 
        padding: 30px; 
        background: #6a11cb; 
        background: linear-gradient(135deg, #6a11cb, #2575fc); 
      ">
        <div style="
          max-width: 520px; 
          margin: auto; 
          padding: 25px; 
          border-radius: 12px; 
          background: #EDEDED; 
          border: 1px solid rgba(255,255,255,0.4); 
          backdrop-filter: blur(4px);
          box-shadow: 0px 8px 25px rgba(0,0,0,0.25);
        ">
          <h2 style="color: #6a11cb; margin-bottom: 10px;">
            Hi {username},
          </h2>

          <p style="font-size: 15px; color: #444;">
            We received a request to verify your account.
          </p>

          <p style="text-align: center; padding: 15px;">
            <a href="{verify_url}" style="
              display: inline-block; 
              padding: 12px 25px; 
              color: white; 
              background: linear-gradient(135deg, #ff416c, #ff4b2b); 
              text-decoration: none; 
              border-radius: 30px;
              font-weight: bold;
              box-shadow: 0px 4px 12px rgba(0,0,0,0.2);
            ">
              Verify Account
            </a>
          </p>

          <p style="font-size: 14px; color: #555;">
            If you didn’t request this, you can safely ignore this email.
          </p>

          <p style="margin-top: 25px; font-size: 12px; color: #777; text-align: center;">
            This link will expire in 1 minute.
          </p>
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
      <body style="
        font-family: Arial, sans-serif; 
        color: #222; 
        margin: 0; 
        padding: 30px; 
        background: #EDEDED; 
        background: linear-gradient(135deg, #6a11cb, #2575fc); 
      ">
        <div style="
          max-width: 520px; 
          margin: auto; 
          padding: 25px; 
          border-radius: 12px; 
          background: #EDEDED; 
          border: 1px solid rgba(255,255,255,0.4); 
          backdrop-filter: blur(4px);
          box-shadow: 0px 8px 25px rgba(0,0,0,0.25);
        ">
          <h2 style="color: #6a11cb; margin-bottom: 10px;">
            Hi {username},
          </h2>

          <p style="font-size: 15px; color: #444;">
            We received a request to RESET your password.
          </p>

          <p style="text-align: center; padding: 15px;">
            <a href="{reset_link}" style="
              display: inline-block; 
              padding: 12px 25px; 
              color: white; 
              background: linear-gradient(135deg, #ff416c, #ff4b2b); 
              text-decoration: none; 
              border-radius: 30px;
              font-weight: bold;
              box-shadow: 0px 4px 12px rgba(0,0,0,0.2);
            ">
              Reset Password
            </a>
          </p>

          <p style="font-size: 14px; color: #555;">
            If you didn’t request this, you can safely ignore this email.
          </p>

          <p style="margin-top: 25px; font-size: 12px; color: #777; text-align: center;">
            This link will expire in 1 minute.
          </p>
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
