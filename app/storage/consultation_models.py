"""
app/storage/consultation_models.py

SQLAlchemy model for consultations.
Stores transcript turns and generated report as JSON text columns.
"""

from sqlalchemy import Column, Integer, String, Text
from app.storage.database import Base


class ConsultationDB(Base):
    __tablename__ = "consultations"

    id               = Column(Integer, primary_key=True, index=True)
    consultation_id  = Column(String, unique=True, index=True)
    patient_id       = Column(String, nullable=True)
    doctor_id        = Column(String, nullable=True)
    started_at       = Column(String, nullable=True)
    ended_at         = Column(String, nullable=True)
    audio_file       = Column(String, nullable=True)
    transcript_json  = Column(Text, nullable=True, default="[]")   # list of turn dicts
    report_json      = Column(Text, nullable=True, default="{}")   # structured report
    summary          = Column(Text, nullable=True)
    status           = Column(String, default="recording")         # recording | completed | reviewed