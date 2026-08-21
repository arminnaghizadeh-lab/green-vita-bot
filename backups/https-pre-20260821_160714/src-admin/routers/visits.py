from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Diagnosis, Plant, User
from src.db.models.visit_status import VisitStatus

router = APIRouter(tags=["visits"])
templates = Jinja2Templates(directory="src/admin/templates")

STATUS_LABELS = {
    VisitStatus.PENDING.value: "در انتظار بررسی",
    VisitStatus.REVIEWING.value: "در حال بررسی",
    VisitStatus.SCHEDULED.value: "زمان‌بندی‌شده",
    VisitStatus.CONFIRMED.value: "تأییدشده",
    VisitStatus.IN_PROGRESS.value: "در حال انجام",
    VisitStatus.COMPLETED.value: "انجام‌شده",
    VisitStatus.CANCELLED.value: "لغوشده",
}

STATUS_CLASSES = {
    "pending": "status-pending",
    "reviewing": "status-reviewing",
    "scheduled": "status-scheduled",
    "confirmed": "status-confirmed",
    "in_progress": "status-progress",
    "completed": "status-completed",
    "cancelled": "status-cancelled",
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
            Diagnosis.visit_scheduled_at.desc().nullslast(),
            Diagnosis.created_at.desc(),
        )
    )

    if status in STATUS_LABELS:
        query = query.where(Diagnosis.visit_status == status)

    rows = (await session.execute(query)).all()

    visits = [
        {
            "diagnosis": diagnosis,
            "user": user,
            "plant": plant,
            "status_label": STATUS_LABELS.get(
                diagnosis.visit_status.value
                if hasattr(diagnosis.visit_status, "value")
                else diagnosis.visit_status,
                "نامشخص",
            ),
            "status_class": STATUS_CLASSES.get(
                diagnosis.visit_status.value
                if hasattr(diagnosis.visit_status, "value")
                else diagnosis.visit_status,
                "status-cancelled",
            ),
        }
        for diagnosis, user, plant in rows
    ]

    counts_result = await session.execute(
        select(Diagnosis.visit_status, func.count())
        .where(Diagnosis.expert_visit_requested.is_(True))
        .group_by(Diagnosis.visit_status)
    )

    counts = {}
    for row in counts_result.all():
        key = row[0].value if hasattr(row[0], "value") else row[0]
        counts[key] = row[1]

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

    if diagnosis.visit_status == VisitStatus.PENDING:
        diagnosis.visit_status = VisitStatus.REVIEWING
        await session.commit()

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
        raise HTTPException(status_code=400, detail="Invalid visit status")

    diagnosis = await session.get(Diagnosis, diagnosis_id)
    if not diagnosis or not diagnosis.expert_visit_requested:
        raise HTTPException(status_code=404, detail="Visit request not found")

    diagnosis.visit_status = VisitStatus(status)
    diagnosis.admin_notes = admin_note.strip() or None

    if scheduled_at.strip():
        try:
            diagnosis.visit_scheduled_at = datetime.fromisoformat(
                scheduled_at.strip()
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid scheduled_at",
            ) from exc
    else:
        diagnosis.visit_scheduled_at = None

    await session.commit()

    return RedirectResponse("/visits", status_code=303)
