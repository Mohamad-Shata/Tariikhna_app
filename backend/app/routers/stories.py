"""
Endpoints for creating and listing stories (source Sira passages).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.db_models import Story

router = APIRouter(prefix="/stories", tags=["stories"])


@router.post("/", response_model=Story)
def create_story(story: Story, session: Session = Depends(get_session)):
    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@router.get("/", response_model=list[Story])
def list_stories(session: Session = Depends(get_session)):
    return session.exec(select(Story)).all()


@router.get("/{story_id}", response_model=Story)
def get_story(story_id: int, session: Session = Depends(get_session)):
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story