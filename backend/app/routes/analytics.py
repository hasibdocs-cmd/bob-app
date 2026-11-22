from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/city", response_model=schemas.CityStats)
def city_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    total = db.query(models.Complaint).count()
    open_c = db.query(models.Complaint).filter(
        models.Complaint.status.in_(["open", "assigned", "in_progress", "escalated"])
    ).count()

    today_start = datetime.combine(date.today(), datetime.min.time())
    resolved_today = db.query(models.Complaint).filter(
        models.Complaint.status == "resolved",
        models.Complaint.resolved_at >= today_start
    ).count()

    # Average resolution time in hours
    resolved = db.query(models.Complaint).filter(
        models.Complaint.status == "resolved",
        models.Complaint.resolved_at.isnot(None)
    ).all()
    if resolved:
        total_hours = sum(
            (c.resolved_at - c.created_at).total_seconds() / 3600
            for c in resolved if c.resolved_at and c.created_at
        )
        avg_hours = round(total_hours / len(resolved), 1)
    else:
        avg_hours = 0.0

    # Top category
    top = db.query(models.Complaint.category, func.count(models.Complaint.id).label("cnt")) \
            .group_by(models.Complaint.category).order_by(func.count(models.Complaint.id).desc()).first()
    top_category = top[0] if top else "N/A"

    high_risk = db.query(models.Ward).filter(models.Ward.flood_risk_score >= 7.0).count()

    return {
        "total_complaints": total,
        "open_complaints": open_c,
        "resolved_today": resolved_today,
        "avg_resolution_hours": avg_hours,
        "top_category": top_category,
        "high_risk_wards": high_risk,
    }


@router.get("/ward-heatmap")
def ward_heatmap(db: Session = Depends(get_db), _=Depends(get_current_user)):
    wards = db.query(models.Ward).all()
    result = []
    for w in wards:
        open_c = db.query(models.Complaint).filter(
            models.Complaint.ward_id == w.id,
            models.Complaint.status.in_(["open", "assigned", "in_progress"])
        ).count()
        result.append({
            "ward_id": w.id,
            "ward_name": w.name,
            "zone": w.zone,
            "open_complaints": open_c,
            "flood_risk_score": w.flood_risk_score,
            "cleanliness_score": w.cleanliness_score,
        })
    return result


@router.get("/contractors")
def contractor_leaderboard(db: Session = Depends(get_db), _=Depends(get_current_user)):
    contractors = db.query(models.Contractor).order_by(models.Contractor.compliance_score.desc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "ward_id": c.ward_id,
            "compliance_score": c.compliance_score,
            "total_assigned": c.total_assigned,
            "total_resolved": c.total_resolved,
            "resolution_rate": round(c.total_resolved / c.total_assigned * 100, 1) if c.total_assigned else 0,
        }
        for c in contractors
    ]
