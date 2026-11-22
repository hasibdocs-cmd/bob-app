from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/wards", tags=["wards"])


@router.get("/", response_model=list[schemas.WardOut])
def list_wards(db: Session = Depends(get_db)):
    return db.query(models.Ward).all()


@router.get("/{ward_id}/stats", response_model=schemas.WardStats)
def ward_stats(ward_id: int, db: Session = Depends(get_db)):
    ward = db.query(models.Ward).filter(models.Ward.id == ward_id).first()
    open_count = db.query(models.Complaint).filter(
        models.Complaint.ward_id == ward_id,
        models.Complaint.status.in_(["open", "assigned", "in_progress"])
    ).count()
    resolved_count = db.query(models.Complaint).filter(
        models.Complaint.ward_id == ward_id,
        models.Complaint.status == "resolved"
    ).count()
    return {
        "ward_id": ward.id,
        "ward_name": ward.name,
        "open_count": open_count,
        "resolved_count": resolved_count,
        "flood_risk_score": ward.flood_risk_score,
        "cleanliness_score": ward.cleanliness_score,
    }
