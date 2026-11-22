import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, require_role
from app.watsonx import classify_with_watsonx, SLA_HOURS

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


def generate_ticket_id():
    return "NGA-" + "".join(random.choices(string.digits, k=6))


@router.post("/", response_model=schemas.ComplaintOut, status_code=201)
async def create_complaint(
    payload: schemas.ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # AI Classification
    ai = await classify_with_watsonx(payload.title, payload.description or "")

    # Determine SLA deadline
    priority = ai.get("priority", "medium")
    sla_hours = SLA_HOURS.get(priority, 72)
    sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)

    # Auto-assign ward from user if not provided
    ward_id = payload.ward_id or current_user.ward_id

    # Auto-assign contractor in that ward
    contractor = None
    if ward_id:
        contractor = db.query(models.Contractor).filter(
            models.Contractor.ward_id == ward_id
        ).order_by(models.Contractor.compliance_score.desc()).first()

    complaint = models.Complaint(
        ticket_id=generate_ticket_id(),
        title=payload.title,
        description=payload.description,
        category=ai.get("category", payload.category),
        priority=priority,
        status=models.IssueStatus.open,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        image_url=payload.image_url,
        ai_classification=ai.get("category"),
        ai_confidence=ai.get("confidence"),
        ai_summary=ai.get("summary"),
        reporter_id=current_user.id,
        ward_id=ward_id,
        contractor_id=contractor.id if contractor else None,
        sla_deadline=sla_deadline,
    )
    db.add(complaint)
    if contractor:
        contractor.total_assigned += 1
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/", response_model=list[schemas.ComplaintOut])
def list_complaints(
    status: str = None,
    category: str = None,
    ward_id: int = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Complaint)

    # Scope by role
    if current_user.role == models.UserRole.citizen:
        q = q.filter(models.Complaint.reporter_id == current_user.id)
    elif current_user.role == models.UserRole.field_officer:
        q = q.filter(models.Complaint.assignee_id == current_user.id)
    elif current_user.role == models.UserRole.ward_officer:
        q = q.filter(models.Complaint.ward_id == current_user.ward_id)

    if status:
        q = q.filter(models.Complaint.status == status)
    if category:
        q = q.filter(models.Complaint.category == category)
    if ward_id:
        q = q.filter(models.Complaint.ward_id == ward_id)

    return q.order_by(models.Complaint.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{complaint_id}", response_model=schemas.ComplaintOut)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.patch("/{complaint_id}", response_model=schemas.ComplaintOut)
def update_complaint(
    complaint_id: int,
    payload: schemas.ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if payload.status:
        complaint.status = payload.status
        if payload.status == models.IssueStatus.resolved:
            complaint.resolved_at = datetime.utcnow()
            if complaint.contractor:
                complaint.contractor.total_resolved += 1
                # Recalculate compliance score
                c = complaint.contractor
                if c.total_assigned > 0:
                    c.compliance_score = round((c.total_resolved / c.total_assigned) * 100, 1)
        # Log update
        update = models.ComplaintUpdate(
            complaint_id=complaint.id,
            updated_by=current_user.id,
            status=payload.status,
            note=payload.note,
        )
        db.add(update)

    if payload.priority:
        complaint.priority = payload.priority
    if payload.assignee_id is not None:
        complaint.assignee_id = payload.assignee_id
        complaint.status = models.IssueStatus.assigned
    if payload.contractor_id is not None:
        complaint.contractor_id = payload.contractor_id

    db.commit()
    db.refresh(complaint)
    return complaint


@router.post("/{complaint_id}/rate")
def rate_complaint(
    complaint_id: int,
    payload: schemas.ComplaintRating,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not 1 <= payload.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    complaint = db.query(models.Complaint).filter(
        models.Complaint.id == complaint_id,
        models.Complaint.reporter_id == current_user.id,
    ).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.citizen_rating = payload.rating
    db.commit()
    return {"message": "Rating submitted"}
