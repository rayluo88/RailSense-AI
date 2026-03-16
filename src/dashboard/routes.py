"""FastAPI routes for the Jinja2-based dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.dashboard.queries import get_alert_feed_data, get_overview_data, get_sensor_data
from src.db.session import get_db

router = APIRouter(tags=["dashboard"])

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/overview")


@router.get("/overview", response_class=HTMLResponse)
def overview_page(request: Request, db: Session = Depends(get_db)):
    data = get_overview_data(db)
    return templates.TemplateResponse("overview.html", {"request": request, **data})


@router.get("/sensors", response_class=HTMLResponse)
def sensor_explorer_page(
    request: Request,
    train_id: str = "T001",
    sensor_type: str = "vibration",
    db: Session = Depends(get_db),
):
    data = get_sensor_data(db, train_id=train_id, sensor_type=sensor_type)
    return templates.TemplateResponse("sensor_explorer.html", {"request": request, **data})


@router.get("/alerts", response_class=HTMLResponse)
def alert_feed_page(
    request: Request,
    severity: str | None = None,
    db: Session = Depends(get_db),
):
    data = get_alert_feed_data(db, severity=severity)
    return templates.TemplateResponse("alert_feed.html", {"request": request, **data})


@router.get("/models", response_class=HTMLResponse)
def model_comparison_page(request: Request):
    return templates.TemplateResponse("model_comparison.html", {"request": request})
