"""REST API router for clinic tokens, queue operations, and demo utilities."""

import time
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import Token
from backend.app.schemas import (
    CallAlertResponse,
    MessageResponse,
    QueueResponse,
    TokenCreate,
    TokenResponse,
)
from backend.app.services import credit_protection, queue_service
from backend.app.services.broadcast import (
    broadcast_demo_reset,
    broadcast_queue_change,
    broadcast_token_called,
)

_reset_rate_limits: Dict[str, list[float]] = {}
RESET_RATE_LIMIT_CALLS = 5
RESET_RATE_LIMIT_WINDOW = 60.0  # max 5 per minute per IP on deployed builds


def _check_reset_rate_limit(request: Optional[Request] = None) -> None:
    """Protects and rate-limits reset/seed endpoints on deployed builds."""
    if not request:
        return
    client_ip = credit_protection.get_client_ip(request)
    owner_key = request.headers.get("x-owner-key") if request else None
    if credit_protection.is_owner(owner_key):
        return
    if not credit_protection.is_demo_limits_active(client_ip, request):
        return
    now = time.time()
    history = _reset_rate_limits.setdefault(client_ip, [])
    _reset_rate_limits[client_ip] = [t for t in history if now - t < RESET_RATE_LIMIT_WINDOW]
    if len(_reset_rate_limits[client_ip]) >= RESET_RATE_LIMIT_CALLS:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: too many reset/seed requests. Please wait a minute.",
        )
    _reset_rate_limits[client_ip].append(now)

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


@router.get("/tokens/{token_id}/call-alert", response_model=CallAlertResponse)
def get_token_call_alert(
    token_id: int,
    lang: str = Query("te-IN", description="Language code: te-IN, en-IN, or mix"),
    db: Session = Depends(get_db),
):
    """
    Returns call alert message and optional audio for a called token (P3-2).
    Respects ALERT_VOICE (default False -> banner message only).
    """
    tok = db.query(Token).filter(Token.id == token_id).first()
    if not tok:
        raise HTTPException(status_code=404, detail="Token not found.")

    from backend.app.services.call_alert import get_token_call_alert_data

    return get_token_call_alert_data(tok, lang=lang)



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
    broadcast_token_called(tok.id, tok.number)
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
def reset_demo_data(request: Request = None, db: Session = Depends(get_db)):
    """Resets all queue tokens and interaction logs for a fresh demo."""
    _check_reset_rate_limit(request)
    queue_service.reset_demo(db)
    today_str = queue_service.resolve_date("today")
    broadcast_queue_change(today_str)
    broadcast_demo_reset()
    return MessageResponse(message="Demo queue reset successfully.")


@router.post("/demo/seed", response_model=List[TokenResponse])
def seed_demo_data(
    day: str = Query("today"),
    count: int = Query(6),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Seeds demo tokens (default 4 fake tokens)."""
    _check_reset_rate_limit(request)
    try:
        target_date = queue_service.resolve_date(day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tokens = queue_service.seed_demo(db, day=day, count=count)
    broadcast_queue_change(target_date)
    return [_to_token_response(t, db) for t in tokens]


