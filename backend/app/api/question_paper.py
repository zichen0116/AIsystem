"""用户保存的试卷 CRUD（按 user_id 隔离）"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.database import get_db
from app.models.question_paper import QuestionPaper
from app.schemas.question_paper import (
    QuestionPaperCreate,
    QuestionPaperCreateResponse,
    QuestionPaperDetail,
    QuestionPaperListItem,
    QuestionPaperListResponse,
)

router = APIRouter(prefix="/question-papers", tags=["question-papers"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


def _to_detail(row: QuestionPaper) -> QuestionPaperDetail:
    return QuestionPaperDetail(
        id=row.id,
        title=row.title,
        subject=row.subject,
        difficulty=row.difficulty,
        questions=list(row.questions) if row.questions is not None else [],
        created_at=row.created_at,
    )


def _to_list_item(row: QuestionPaper) -> QuestionPaperListItem:
    n = len(row.questions) if row.questions is not None else 0
    return QuestionPaperListItem(
        id=row.id,
        title=row.title,
        subject=row.subject,
        difficulty=row.difficulty,
        question_count=n,
        created_at=row.created_at,
    )


@router.post("", response_model=QuestionPaperCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_question_paper(
    payload: QuestionPaperCreate,
    user: CurrentUser,
    db: DbSession,
):
    paper = QuestionPaper(
        user_id=user.id,
        title=payload.title.strip(),
        subject=(payload.subject or "").strip() or "未命名学科",
        difficulty=payload.difficulty or "medium",
        questions=payload.questions,
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)
    return QuestionPaperCreateResponse(paper=_to_detail(paper))


@router.get("", response_model=QuestionPaperListResponse)
async def list_question_papers(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(QuestionPaper)
        .where(QuestionPaper.user_id == user.id)
        .order_by(QuestionPaper.created_at.desc())
    )
    rows = result.scalars().all()
    return QuestionPaperListResponse(items=[_to_list_item(r) for r in rows])


@router.get("/{paper_id}", response_model=QuestionPaperDetail)
async def get_question_paper(paper_id: int, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(QuestionPaper).where(
            QuestionPaper.id == paper_id,
            QuestionPaper.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    return _to_detail(row)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_paper(paper_id: int, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(QuestionPaper).where(
            QuestionPaper.id == paper_id,
            QuestionPaper.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    await db.delete(row)
    await db.commit()
    return None
