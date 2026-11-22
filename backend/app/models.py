import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class UserRole(str, enum.Enum):
    citizen = "citizen"
    field_officer = "field_officer"
    ward_officer = "ward_officer"
    commissioner = "commissioner"


class IssueCategory(str, enum.Enum):
    garbage_black_spot = "garbage_black_spot"
    cd_waste = "cd_waste"
    waterlogging = "waterlogging"
    drain_blockage = "drain_blockage"
    groundwater = "groundwater"
    other = "other"


class IssuePriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IssueStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    escalated = "escalated"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.citizen, nullable=False)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ward = relationship("Ward", back_populates="users")
    complaints = relationship("Complaint", back_populates="reporter", foreign_keys="Complaint.reporter_id")
    assigned_complaints = relationship("Complaint", back_populates="assignee", foreign_keys="Complaint.assignee_id")


class Ward(Base):
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    zone = Column(String(100), nullable=True)
    population = Column(Integer, nullable=True)
    flood_risk_score = Column(Float, default=0.0)
    cleanliness_score = Column(Float, default=100.0)

    users = relationship("User", back_populates="ward")
    complaints = relationship("Complaint", back_populates="ward")
    contractors = relationship("Contractor", back_populates="ward")


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact = Column(String(100), nullable=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    compliance_score = Column(Float, default=100.0)
    total_assigned = Column(Integer, default=0)
    total_resolved = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ward = relationship("Ward", back_populates="contractors")
    complaints = relationship("Complaint", back_populates="contractor")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(IssueCategory), nullable=False)
    priority = Column(Enum(IssuePriority), default=IssuePriority.medium)
    status = Column(Enum(IssueStatus), default=IssueStatus.open)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)

    image_url = Column(String(500), nullable=True)
    ai_classification = Column(String(100), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_summary = Column(Text, nullable=True)

    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=True)

    sla_deadline = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    citizen_rating = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reporter = relationship("User", back_populates="complaints", foreign_keys=[reporter_id])
    assignee = relationship("User", back_populates="assigned_complaints", foreign_keys=[assignee_id])
    ward = relationship("Ward", back_populates="complaints")
    contractor = relationship("Contractor", back_populates="complaints")
    updates = relationship("ComplaintUpdate", back_populates="complaint")


class ComplaintUpdate(Base):
    __tablename__ = "complaint_updates"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(IssueStatus), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="updates")
