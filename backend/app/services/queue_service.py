"""Queue management business logic: booking, numbering, position math, and status tracking."""

from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import Token, VoiceLog


def resolve_date(day_str: str) -> str:
    """Resolves 'today', 'tomorrow', or 'YYYY-MM-DD' into an ISO date string."""
    day_lower = (day_str or "").strip().lower()
    today = date.today()
    if day_lower in ("today", ""):
        return today.isoformat()
    elif day_lower == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    try:
        parsed = date.fromisoformat(day_str.strip())
        return parsed.isoformat()
    except Exception:
        raise ValueError(f"Invalid day: '{day_str}'. Must be 'today', 'tomorrow', or 'YYYY-MM-DD'.")


def book(db: Session, day: str = "today", language: str = "te-IN") -> Token:
    """
    Books a token for today or tomorrow.
    Token numbers start at 1 for each date and increment monotonically.
    """
    target_date = resolve_date(day)

    # Next number for this specific date
    max_number = (
        db.query(func.max(Token.number))
        .filter(Token.date == target_date)
        .scalar()
    ) or 0
    next_number = max_number + 1

    token = Token(
        number=next_number,
        date=target_date,
        label=f"Patient {next_number}",
        language=language,
        status="waiting",
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def position(db: Session, token_id: int) -> int:
    """
    Returns how many tokens with status 'waiting' or 'in_consult'
    and a smaller number exist for the same date.
    """
    token = db.query(Token).filter(Token.id == token_id).first()
    if not token:
        raise ValueError(f"Token {token_id} not found.")

    ahead_count = (
        db.query(Token)
        .filter(
            Token.date == token.date,
            Token.status.in_(["waiting", "in_consult"]),
            Token.number < token.number,
        )
        .count()
    )
    return ahead_count


def cancel(db: Session, token_id: int) -> Token:
    """
    Cancels a token. A done token cannot be cancelled.
    Cancelled tokens leave the queue and positions update.
    """
    token = db.query(Token).filter(Token.id == token_id).first()
    if not token:
        raise ValueError(f"Token {token_id} not found.")

    if token.status == "done":
        raise ValueError("A done token cannot be cancelled.")

    token.status = "cancelled"
    db.commit()
    db.refresh(token)
    return token


def call_next(db: Session, target_date_str: str = "today") -> Optional[Token]:
    """
    Calls the next waiting token for the given date and marks it 'in_consult'.
    Any previous in_consult token is completed ('done').
    """
    target_date = resolve_date(target_date_str)

    # If any token is currently in_consult, mark it done
    current_in_consult = (
        db.query(Token)
        .filter(Token.date == target_date, Token.status == "in_consult")
        .first()
    )
    if current_in_consult:
        current_in_consult.status = "done"

    # Find the next waiting token with the lowest number
    next_token = (
        db.query(Token)
        .filter(Token.date == target_date, Token.status == "waiting")
        .order_by(Token.number.asc())
        .first()
    )
    if next_token:
        next_token.status = "in_consult"

    db.commit()
    if next_token:
        db.refresh(next_token)
    return next_token


def mark(db: Session, token_id: int, status: str) -> Token:
    """Marks a token with a specific status ('done', 'no_show', etc.)."""
    valid_statuses = {"waiting", "in_consult", "done", "cancelled", "no_show"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")

    token = db.query(Token).filter(Token.id == token_id).first()
    if not token:
        raise ValueError(f"Token {token_id} not found.")

    token.status = status
    db.commit()
    db.refresh(token)
    return token


def list_queue(db: Session, target_date_str: str = "today") -> List[Token]:
    """Lists all tokens for a given date ordered by number."""
    target_date = resolve_date(target_date_str)
    return (
        db.query(Token)
        .filter(Token.date == target_date)
        .order_by(Token.number.asc())
        .all()
    )


def reset_demo(db: Session) -> None:
    """Resets all tokens for clean demo/test state. Preserves voice logs."""
    db.query(Token).delete()
    db.commit()


def seed_demo(db: Session, day: str = "today", count: int = 6) -> List[Token]:
    """Creates fake tokens (default 6) labelled 'Demo Patient 1' to 'Demo Patient N'."""
    reset_demo(db)
    target_date = resolve_date(day)
    created_tokens = []

    for i in range(1, count + 1):
        status = "in_consult" if i == 1 else "waiting"
        tok = Token(
            number=i,
            date=target_date,
            label=f"Demo Patient {i}",
            language="te-IN" if i % 2 == 1 else "en-IN",
            status=status,
        )
        db.add(tok)
        created_tokens.append(tok)

    db.commit()
    for tok in created_tokens:
        db.refresh(tok)
    return created_tokens


def auto_seed_if_empty(db: Session, count: int = 4, day: str = "today") -> List[Token]:
    """Seeds fake tokens (default 4) at startup when the queue is empty.
    
    Guarantees the live demo is never blank after a free-host restart (Phase P2-8).
    """
    target_date = resolve_date(day)
    existing_count = db.query(Token).filter(Token.date == target_date).count()
    if existing_count > 0:
        return []

    created_tokens = []
    for i in range(1, count + 1):
        status = "in_consult" if i == 1 else "waiting"
        tok = Token(
            number=i,
            date=target_date,
            label=f"Demo Patient {i}",
            language="te-IN" if i % 2 == 1 else "en-IN",
            status=status,
        )
        db.add(tok)
        created_tokens.append(tok)

    db.commit()
    for tok in created_tokens:
        db.refresh(tok)
    print(f"[Demo Autoseed] Seeded {len(created_tokens)} tokens for {target_date} (queue was empty).")
    return created_tokens



