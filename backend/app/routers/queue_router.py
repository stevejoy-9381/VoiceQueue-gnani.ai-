"""REST API router for clinic tokens, queue operations, and demo utilities."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import Token
from backend.app.schemas import MessageResponse, QueueResponse, TokenCreate, TokenResponse
from backend.app.services import queue_service
from backend.app.services.broadcast import broadcast_demo_reset, broadcast_queue_change

router = APIRouter(tags=["Queue & Tokens"])


def _to_token_response(tok, db: Session) -> TokenResponse:
    ahead = queue_service.position(db, tok.id) if tok.status in ("waiting", "in_consult") else None
    return TokenResponse(
        id=tok.id,
        number=tok.number,
        date=tok.date,
        label=tok.label,
        language=tok.language,
        status=tok.status,
        created_at=tok.created_at,
        ahead_count=ahead,
    )


@router.post("/tokens", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def book_token(payload: TokenCreate, db: Session = Depends(get_db)):
    """Books a new token for today or tomorrow."""
    try:
        tok = queue_service.book(db, day=payload.day, language=payload.language)
        broadcast_queue_change(tok.date)
        return _to_token_response(tok, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tokens/{token_id}", response_model=TokenResponse)
def get_token(token_id: int, db: Session = Depends(get_db)):
    """Retrieves token details and current queue position."""
    tok = db.query(Token).filter(Token.id == token_id).first()
    if not tok:
        raise HTTPException(status_code=404, detail="Token not found.")
    return _to_token_response(tok, db)


@router.post("/tokens/{token_id}/cancel", response_model=TokenResponse)
def cancel_token(token_id: int, db: Session = Depends(get_db)):
    """Cancels a token. Done tokens cannot be cancelled."""
    existing = db.query(Token).filter(Token.id == token_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Token not found.")
    try:
        tok = queue_service.cancel(db, token_id)
        broadcast_queue_change(tok.date)
        return _to_token_response(tok, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/queue", response_model=QueueResponse)
def get_queue(day: str = Query("today", description="Day: today, tomorrow, or YYYY-MM-DD"), db: Session = Depends(get_db)):
    """Retrieves the full queue and active consult token for a date."""
    try:
        target_date = queue_service.resolve_date(day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tokens = queue_service.list_queue(db, target_date)

    in_consult_tok = next((t for t in tokens if t.status == "in_consult"), None)
    waiting_count = sum(1 for t in tokens if t.status == "waiting")

    return QueueResponse(
        date=target_date,
        total_tokens=len(tokens),
        waiting_count=waiting_count,
        current_in_consult=_to_token_response(in_consult_tok, db) if in_consult_tok else None,
        tokens=[_to_token_response(t, db) for t in tokens],
    )


@router.post("/queue/next", response_model=Optional[TokenResponse])
def call_next_token(day: str = Query("today", description="Day: today, tomorrow, or YYYY-MM-DD"), db: Session = Depends(get_db)):
    """Advances the queue by moving next waiting patient to in_consult."""
    try:
        target_date = queue_service.resolve_date(day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tok = queue_service.call_next(db, target_date)
    broadcast_queue_change(target_date)
    if not tok:
        return None
    return _to_token_response(tok, db)


@router.post("/queue/{token_id}/done", response_model=TokenResponse)
def mark_token_done(token_id: int, db: Session = Depends(get_db)):
    """Marks a token consult as done."""
    existing = db.query(Token).filter(Token.id == token_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Token not found.")
    try:
        tok = queue_service.mark(db, token_id, "done")
        broadcast_queue_change(tok.date)
        return _to_token_response(tok, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/queue/{token_id}/no-show", response_model=TokenResponse)
def mark_token_no_show(token_id: int, db: Session = Depends(get_db)):
    """Marks a token as no-show."""
    existing = db.query(Token).filter(Token.id == token_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Token not found.")
    try:
        tok = queue_service.mark(db, token_id, "no_show")
        broadcast_queue_change(tok.date)
        return _to_token_response(tok, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/demo/reset", response_model=MessageResponse)
def reset_demo_data(db: Session = Depends(get_db)):
    """Resets all queue tokens and interaction logs for a fresh demo."""
    queue_service.reset_demo(db)
    today_str = queue_service.resolve_date("today")
    broadcast_queue_change(today_str)
    broadcast_demo_reset()
    return MessageResponse(message="Demo queue reset successfully.")


@router.post("/demo/seed", response_model=List[TokenResponse])
def seed_demo_data(day: str = Query("today"), db: Session = Depends(get_db)):
    """Seeds 6 demo tokens (Demo Patient 1 to 6)."""
    try:
        target_date = queue_service.resolve_date(day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tokens = queue_service.seed_demo(db, day=day)
    broadcast_queue_change(target_date)
    return [_to_token_response(t, db) for t in tokens]


