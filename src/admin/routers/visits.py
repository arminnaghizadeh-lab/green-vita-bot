"""Admin workflow for Green Vita expert visit requests."""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Diagnosis, Plant, User


router = APIRouter(tags=["visits"])
templates = Jinja2Templates(directory="src/admin/templates")

STATUS_LABELS = {
    "new": "جدید",
    "reviewing": "در حال بررسی",
    "waiting_contact": "در انتظار تماس",
    "scheduled": "زمان‌بندی‌شده",
    "in_progress": "در حال انجام",
    "completed": "انجام‌شده",
    "cancelled": "لغوشده",
    "rejected": "ردشده",
}

STATUS_CLASSES = {
    "new": "bg-red-100 text-red-700",
    "reviewing": "bg-blue-100 text-blue-700",
    "waiting_contact": "bg-amber-100 text-amber-700",
    "scheduled": "bg-purple-100 text-purple-700",
    "in_progress": "bg-indigo-100 text-indigo-700",
    "completed": "bg-emerald-100 text-emerald-700",
    "cancelled": "bg-gray-200 text-gray-700",
    "rejected": "bg-gray-200 text-gray-700",
}


@router.get("/visits")
async def visits_list(
    request: Request,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    query = (
        select(Diagnosis, User, Plant)
        .join(User, Diagnosis.user_id == User.id)
        .outerjoin(Plant, Diagnosis.plant_id == Plant.id)
        .where(Diagnosis.expert_visit_requested.is_(True))
        .order_by(
            Diagnosis.expert_visit_updated_at.desc().nullslast(),
            Diagnosis.created_at.desc(),
        )
    )
    if status in STATUS_LABELS:
        query = query.where(Diagnosis.expert_visit_status == status)

    rows = (await session.execute(query)).all()

    visits = [
        {
            "diagnosis": diagnosis,
            "user": user,
            "plant": plant,
            "status_label": STATUS_LABELS.get(
                diagnosis.expert_visit_status, diagnosis.expert_visit_status
            ),
            "status_class": STATUS_CLASSES.get(
                diagnosis.expert_visit_status, "bg-gray-100 text-gray-700"
            ),
        }
        for diagnosis, user, plant in rows
    ]

    counts_result = await session.execute(
        select(Diagnosis.expert_visit_status, func.count())
        .where(Diagnosis.expert_visit_requested.is_(True))
        .group_by(Diagnosis.expert_visit_status)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    return templates.TemplateResponse(
        "visits.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "visits": visits,
            "counts": counts,
            "status_labels": STATUS_LABELS,
            "selected_status": status,
        },
    )


@router.get("/visits/{diagnosis_id}")
async def visit_detail(
    diagnosis_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    result = await session.execute(
        select(Diagnosis, User, Plant)
        .join(User, Diagnosis.user_id == User.id)
        .outerjoin(Plant, Diagnosis.plant_id == Plant.id)
        .where(
            Diagnosis.id == diagnosis_id,
            Diagnosis.expert_visit_requested.is_(True),
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Visit request not found")

    diagnosis, user, plant = row
    return templates.TemplateResponse(
        "visit_detail.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "diagnosis": diagnosis,
            "user": user,
            "plant": plant,
            "status_labels": STATUS_LABELS,
            "status_classes": STATUS_CLASSES,
        },
    )


@router.post("/visits/{diagnosis_id}/update")
async def update_visit(
    diagnosis_id: int,
    request: Request,
    status: str = Form(...),
    admin_note: str = Form(""),
    scheduled_at: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    if status not in STATUS_LABELS:
        return RedirectResponse(url=f"/visits/{diagnosis_id}", status_code=303)

    diagnosis = await session.get(Diagnosis, diagnosis_id)
    if not diagnosis or not diagnosis.expert_visit_requested:
        raise HTTPException(status_code=404, detail="Visit request not found")

    diagnosis.expert_visit_status = status
    diagnosis.expert_visit_updated_at = datetime.now().astimezone()
    diagnosis.expert_visit_admin_note = admin_note.strip() or None

    if scheduled_at.strip():
        try:
            diagnosis.expert_visit_scheduled_at = datetime.fromisoformat(
                scheduled_at.strip()
            )
        except ValueError:
            diagnosis.expert_visit_scheduled_at = None
    else:
        diagnosis.expert_visit_scheduled_at = None

    await session.commit()
    return RedirectResponse(url=f"/visits/{diagnosis_id}", status_code=303)
