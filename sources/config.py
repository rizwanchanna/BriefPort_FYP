from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    BACK_LINK: str
    FRONT_LINK: str
    SECRET_KEY: str
    ALGORITHM: str
    HF_TOKEN: str
    GOOGLE_API_KEY: str
    OPEN_ROUTER_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1
    
    SMTP_EMAIL: str
    SMTP_PASSWORD: str

    class Config:
        env_file = ".env"

settings = Settings()