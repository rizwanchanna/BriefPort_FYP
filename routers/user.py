from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sources import schemas, database, oauth2, models, config
from repo import user
import smtplib
from email.message import EmailMessage

router = APIRouter(
    prefix="/user",
    tags=["Users"]
)

@router.get("/me", response_model=schemas.UserPublic, status_code=status.HTTP_202_ACCEPTED)
def get_current_user_data(current_user: models.User = Depends(oauth2.get_current_user)):
    return current_user

@router.patch("/me", response_model=schemas.UserPublic, status_code=status.HTTP_202_ACCEPTED)
def update_me(
    request: schemas.UserUpdate, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    return user.update_user_profile(current_user, request, db)

@router.post("/change-password", status_code=status.HTTP_202_ACCEPTED)
def change_user_password(
    request: schemas.ChangePassword, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    try:
        return user.change_password(current_user, request, db)
    except Exception as e:
        print(f"Password change error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_me(
    request: schemas.UserDeleteConfirmation,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    return user.delete_user_account(current_user, request, db)

@router.post("/contact/send-email")
def send_contact_email(form: schemas.ContactForm):
    try:
        msg = EmailMessage()
        msg["Subject"] = f"[Contact] {form.subject}"
        msg["From"] = config.settings.SMTP_EMAIL
        msg["To"] = config.settings.SMTP_Admin_EMAIL

        msg.set_content(
            f"New message from: {form.name}\n\n({form.email})\n\n{form.message}"
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(config.settings.SMTP_EMAIL, config.settings.SMTP_PASSWORD)
            smtp.send_message(msg)

        return {"message": "Email sent successfully"}

    except Exception as e:
        print("Email error:", e)
        raise HTTPException(status_code=500, detail="Failed to send email")