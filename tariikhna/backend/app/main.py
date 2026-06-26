"""
Entrypoint for the Tariikhna backend.

Run from the backend/ folder with:
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for interactive API docs.

Serves three things:
  - /stories, /scenes  -> the generation pipeline (create new content)
  - /library/...        -> read-only storybook data for the Streamlit reader
  - /media/...          -> the illustration PNGs (static files)
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import stories, scenes, library

app = FastAPI(
    title="Tariikhna API",
    description="Islamic historical narratives as child-friendly comic panels.",
    version="0.2.0",
)

# Allow the Streamlit frontend (any origin in dev) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stories.router)
app.include_router(scenes.router)
app.include_router(library.router)

# Serve illustrations. Ensure the directory exists so the mount never crashes
# on a fresh checkout (the importer fills it with content).
os.makedirs(settings.media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def health_check():
    return {"status": "ok", "service": "tariikhna-backend"}
