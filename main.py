from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import user, authentication, documents
from sources import models, database
import logging
import sys
from sources.config import settings


models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

origins = [settings.BACK_LINK]

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


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
