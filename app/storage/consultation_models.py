from sqlalchemy import Column, Integer, String, Text, Float
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
    transcript_json  = Column(Text, nullable=True)   # JSON list of turns
    report_json      = Column(Text, nullable=True)   # JSON structured report
    summary          = Column(Text, nullable=True)
    status           = Column(String, default="recording")