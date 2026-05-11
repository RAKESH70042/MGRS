from pydantic import BaseModel
from typing import List, Optional


class TranscriptTurn(BaseModel):
    speaker: str          # "Doctor" or "Patient"
    text: str
    timestamp: float      # seconds from start


class ConsultationTranscript(BaseModel):
    turns: List[TranscriptTurn] = []


class Medication(BaseModel):
    medication_name: Optional[str] = None
    dosage: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    special_instructions: Optional[str] = None


class StructuredReport(BaseModel):
    patient_complaints: Optional[str] = None
    symptoms: Optional[str] = None
    doctor_observations: Optional[str] = None
    diagnosis: Optional[str] = None
    prescribed_medicines: List[Medication] = []
    tests_recommended: Optional[str] = None
    follow_up_instructions: Optional[str] = None
    treatment_plan: Optional[str] = None
    important_notes: Optional[str] = None
    icd10_suggestions: Optional[str] = None
    soap_note: Optional[str] = None


class ConsultationRecord(BaseModel):
    consultation_id: str
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    audio_file: Optional[str] = None
    transcript: ConsultationTranscript = ConsultationTranscript()
    report: Optional[StructuredReport] = None
    summary: Optional[str] = None
    status: str = "recording"   # recording | completed | reviewed