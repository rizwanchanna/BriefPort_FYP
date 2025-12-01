from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import user, authentication, documents
from sources import models, database
import logging
import sys
import os
from sources.config import settings


models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

origins = [settings.FRONT_LINK]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(authentication.router)
app.include_router(user.router)
app.include_router(documents.router)

# Mount static files for audio summaries file to play on dashboard(frontend) 
audio_dir = os.path.join(os.path.dirname(__file__), "audio_summaries")
os.makedirs(audio_dir, exist_ok=True)
app.mount("/audio_summaries", StaticFiles(directory=audio_dir), name="audio_summaries")


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
