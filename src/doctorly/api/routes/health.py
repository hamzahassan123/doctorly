import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from doctorly.db.session import get_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", tags=["health"])
def readiness(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "dependency": "database"},
        ) from exc

    return {"status": "ok"}
