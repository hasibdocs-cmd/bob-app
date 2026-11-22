from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr
from app.models import UserRole, IssueCategory, IssuePriority, IssueStatus, ChannelType, MediaType


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: UserRole = UserRole.citizen
    ward_id: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    role: UserRole
    ward_id: Optional[int]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ── Ward ─────────────────────────────────────────────────────────────────────

class WardOut(BaseModel):
    id: int
    name: str
    zone: Optional[str]
    flood_risk_score: float
    cleanliness_score: float

    class Config:
        from_attributes = True


# ── Contractor ───────────────────────────────────────────────────────────────

class ContractorOut(BaseModel):
    id: int
    name: str
    ward_id: Optional[int]
    compliance_score: float
    total_assigned: int
    total_resolved: int

    class Config:
        from_attributes = True


# ── Complaints ────────────────────────────────────────────────────────────────

class ComplaintCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: IssueCategory
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    ward_id: Optional[int] = None


class ComplaintUpdate(BaseModel):
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    assignee_id: Optional[int] = None
    contractor_id: Optional[int] = None
    note: Optional[str] = None


class ComplaintRating(BaseModel):
    rating: int


class ComplaintUpdateOut(BaseModel):
    id: int
    status: IssueStatus
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ComplaintOut(BaseModel):
    id: int
    ticket_id: str
    title: str
    description: Optional[str]
    category: IssueCategory
    priority: IssuePriority
    status: IssueStatus
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    image_url: Optional[str]
    ai_classification: Optional[str]
    ai_confidence: Optional[float]
    ai_summary: Optional[str]
    reporter_id: int
    assignee_id: Optional[int]
    ward_id: Optional[int]
    contractor_id: Optional[int]
    sla_deadline: Optional[datetime]
    resolved_at: Optional[datetime]
    citizen_rating: Optional[int]
    created_at: datetime
    updates: List[ComplaintUpdateOut] = []

    class Config:
        from_attributes = True


# ── Analytics ─────────────────────────────────────────────────────────────────

class CityStats(BaseModel):
    total_complaints: int
    open_complaints: int
    resolved_today: int
    avg_resolution_hours: float
    top_category: str
    high_risk_wards: int


class WardStats(BaseModel):
    ward_id: int
    ward_name: str
    open_count: int
    resolved_count: int
    flood_risk_score: float
    cleanliness_score: float


# ── Multi-channel intake ───────────────────────────────────────────────────────

class MediaAttachmentOut(BaseModel):
    id: int
    media_type: MediaType
    url: str
    mime_type: Optional[str]
    file_size_bytes: Optional[int]
    ai_description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class InboundMessageOut(BaseModel):
    id: int
    channel: ChannelType
    external_id: Optional[str]
    sender_id: Optional[str]
    sender_name: Optional[str]
    raw_text: Optional[str]
    language: Optional[str]
    ai_transcript: Optional[str]
    ai_summary: Optional[str]
    ai_category: Optional[str]
    ai_priority: Optional[str]
    ai_confidence: Optional[float]
    location_text: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    complaint_id: Optional[int]
    is_processed: bool
    created_at: datetime
    attachments: List[MediaAttachmentOut] = []

    class Config:
        from_attributes = True


class ChannelDispatchOut(BaseModel):
    id: int
    complaint_id: int
    channel: ChannelType
    recipient: str
    message_body: str
    external_id: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DispatchRequest(BaseModel):
    """Body for POST /api/channels/dispatch — manually trigger outbound notification."""
    complaint_id: int
    channel: ChannelType
    recipient: str                       # phone / email / telegram chat_id / etc.
    message_body: Optional[str] = None  # leave None → auto-generate from complaint


# ── Channel webhook payloads (internal) ───────────────────────────────────────

class TwilioWebhookPayload(BaseModel):
    """Twilio sends form-encoded data; we parse it into this shape."""
    From: str
    To: str
    Body: Optional[str] = None
    MessageSid: Optional[str] = None
    NumMedia: Optional[str] = "0"
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None
    CallSid: Optional[str] = None
    TranscriptionText: Optional[str] = None

    class Config:
        extra = "allow"


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class MetaWebhookPayload(BaseModel):
    object: str
    entry: List[Dict[str, Any]] = []

    class Config:
        extra = "allow"
