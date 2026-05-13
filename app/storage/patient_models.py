"""
patient_models.py
Stores consultation transcripts linked to a patient record.
Separate from ConsultationDB — this is the long-term patient-facing record.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.storage.database import Base


class PatientTranscriptDB(Base):
    __tablename__ = "patient_transcripts"

    id                = Column(Integer, primary_key=True, index=True)

    # Links
    patient_id        = Column(String, index=True, nullable=True)   # e.g. "PAT001"
    doctor_id         = Column(String, nullable=True)               # e.g. "DR001"
    consultation_id   = Column(String, index=True, nullable=True)   # links to ConsultationDB
    prescription_id   = Column(String, nullable=True)               # links to PrescriptionRecordDB (optional)

    # Content
    transcript_json   = Column(Text,   nullable=True)   # JSON list of {speaker, text, timestamp}
    report_json       = Column(Text,   nullable=True)   # structured MedGemma report (optional)
    summary           = Column(Text,   nullable=True)   # plain-text summary

    # Meta
    started_at        = Column(String, nullable=True)
    ended_at          = Column(String, nullable=True)
    duration_seconds  = Column(Integer, nullable=True)
    status            = Column(String, default="active")   # active | completed | archived

    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())