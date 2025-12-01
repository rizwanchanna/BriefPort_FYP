from fastapi import APIRouter, Depends, status, HTTPException, Body, Query
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sources import schemas, models, database, hashing, oauth2
from utils import email, token_utils
from repo import user
from sources.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=schemas.SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(request: schemas.UserCreate, db: Session = Depends(database.get_db)):
    return user.create_user(request, db)

@router.post("/login", response_model=schemas.LoginResponse, status_code=status.HTTP_202_ACCEPTED)
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    tokens = user.authenticate_user(request.username, request.password, db)
    return {
        "access_token": tokens["access_token"], 
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer"
    }    

@router.post("/refresh", response_model=schemas.Token, status_code=status.HTTP_202_ACCEPTED)
def refresh_access_token(current_user: models.User = Depends(oauth2.get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user, could not refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    new_access_token = token_utils.create_access_token(data={"sub": current_user.username})
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.get("/verify-email", status_code=status.HTTP_202_ACCEPTED)
def verify_email(token: str, db: Session = Depends(database.get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=400, detail="Invalid token")

        user_in_db = db.query(models.User).filter(models.User.username == username).first()
        if not user_in_db:
            raise HTTPException(status_code=404, detail="User not found")

        if user_in_db.is_verified:
            return {"message": "Email already verified."}

        user_in_db.is_verified = True
        db.commit()
        db.refresh(user_in_db)

        return {"message": "Email verified successfully."}

    except jwt.ExpiredSignatureError:

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False})
            username = payload.get("sub")
            if not username:
                raise HTTPException(status_code=400, detail="Invalid token")

            user_in_db = db.query(models.User).filter(models.User.username == username).first()
            if not user_in_db:
                raise HTTPException(status_code=404, detail="User not found")

            if user_in_db.is_verified:
                return {"message": "Email already verified."}

            new_token = token_utils.create_access_token({"sub": user_in_db.username})
            email.send_email_verification(user_in_db.email, user_in_db.username, new_token)
            return {"message": "Token expired. A new verification email has been sent."}

        except Exception as e:
            print("Token decode after expiration failed:", e)
            raise HTTPException(status_code=400, detail="Invalid token after expiration")

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    except Exception as e:
        print("Unexpected error:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(request: schemas.EmailOnly, db: Session = Depends(database.get_db)):
    user_in_db = db.query(models.User).filter(models.User.email == request.email).first()
    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in_db.is_verified:
        return {"message": "Email already verified."}

    token = token_utils.create_access_token({"sub": user_in_db.username})
    email.send_email_verification(user_in_db.email, user_in_db.username, token)
    return {"message": "Verification email sent again."}

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(request: schemas.EmailOnly, db: Session = Depends(database.get_db)):
    user_in_db = db.query(models.User).filter(models.User.email == request.email).first()
    if not user_in_db:
        raise HTTPException(status_code=404, detail="Email not found")

    token = token_utils.create_access_token({"sub": user_in_db.username})
    email.send_password_reset_email(user_in_db.email, user_in_db.username, token)

    return {"message": "Password reset email sent."}

@router.post("/reset-password", status_code=status.HTTP_202_ACCEPTED)
def reset_password(
    request: schemas.ResetPassword = Body(...),
    token: str = Query(...),
    db: Session = Depends(database.get_db)
):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=400, detail="Invalid token")

        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.password = hashing.Hash.bcrypt(request.new_password)
        db.commit()
        return {"message": "Password updated successfully"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token expired. Please request a new one.")

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    except Exception as e:
        print(f"Unexpected error during reset: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
