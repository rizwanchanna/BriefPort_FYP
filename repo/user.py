from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sources import models, schemas, hashing
from utils import email, token_utils

def create_user(request: schemas.UserCreate, db: Session):
    existing_username = db.query(models.User).filter(models.User.username == request.username).first()
    existing_email = db.query(models.User).filter(models.User.email == request.email).first()

    if existing_username:
        raise HTTPException(status_code=400, detail="Username already exists")
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = models.User(
        username=request.username,
        email=request.email,
        password=hashing.Hash.bcrypt(request.password),
        is_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = token_utils.create_access_token({"sub": new_user.username})
    email.send_email_verification(new_user.email, new_user.username, token)

    return {"message": "New user is created. Please verify your email", "details": new_user}

def authenticate_user(username: str, password: str, db: Session):
    user = db.query(models.User).filter(
        (models.User.username == username) | 
        (models.User.email == username)
    ).first()

    if not user or not hashing.Hash.verify(user.password, password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if not user.is_verified:
        raise HTTPException(status_code=401, detail="Unauthorized user. Please verify your email.")

    access_token = token_utils.create_access_token(data={"sub": user.username})
    refresh_token = token_utils.create_refresh_token(data={"sub": user.username})

    return {"access_token": access_token, "refresh_token": refresh_token}

def change_password(current_user: models.User, request: schemas.ChangePassword, db: Session):
    if not hashing.Hash.verify(current_user.password, request.current_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

    hashed_new_password = hashing.Hash.bcrypt(request.new_password)
    db.query(models.User).filter(models.User.id == current_user.id).update(
        {models.User.password: hashed_new_password}
    )

    db.commit()
    return {"detail": "Password changed successfully"}

def update_user_profile(current_user: models.User, request: schemas.UserUpdate, db: Session):
    if request.username:
        existing_user = db.query(models.User).filter(
            models.User.username == request.username,
            models.User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already taken.")
        current_user.username = request.username

    if request.email:
        existing_email = db.query(models.User).filter(
            models.User.email == request.email,
            models.User.id != current_user.id
        ).first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")
        current_user.email = request.email

    db.commit()
    db.refresh(current_user)
    return current_user

def delete_user_account(current_user: models.User, request: schemas.UserDeleteConfirmation, db: Session):
    if not hashing.Hash.verify(current_user.password, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Account deletion failed."
        )

    db.delete(current_user)
    db.commit()

    return {"detail": "User account deleted successfully."}