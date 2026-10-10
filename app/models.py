from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List


@dataclass
class User:
    user_id: int
    role: str  # 'Admin', 'Teacher', 'Parent'
    full_name: str
    email: str
    password_hash: str
    phone: Optional[str] = None
    classroom: Optional[str] = None  # only set for teachers


@dataclass
class Child:
    child_id: int
    first_name: str
    last_name: str
    date_of_birth: date
    classroom: str
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None
    dietary_requirements: Optional[str] = None
    medical_notes: Optional[str] = None


@dataclass
class Immunization:
    immunization_id: int
    child_id: int
    vaccine_name: str
    dose_label: Optional[str]
    date_given: Optional[date]
    status: str  # 'completed', 'scheduled', 'overdue', 'exempt'
    notes: Optional[str] = None


@dataclass
class Announcement:
    announcement_id: int
    sender_id: int
    classroom: str
    content: str
    recipient_count: int
    created_at: datetime


@dataclass
class LearningStory:
    story_id: int
    child_id: int
    teacher_id: int
    title: str
    content: str
    strands: List[str]
    created_at: datetime


@dataclass
class AttendanceRecord:
    attendance_id: int
    child_id: int
    date: date
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    status: str


@dataclass
class AccidentForm:
    accident_id: int
    child_id: int
    teacher_id: int
    incident_datetime: datetime
    location: str
    description: str
    body_part: Optional[str]
    action_taken: str
    medical_attention_needed: bool
    notifiable_event: bool
    parent_acknowledged_at: Optional[datetime]
