from pydantic import BaseModel
from typing import List, Optional


class Medication(BaseModel):
    medication_name: str
    raw_medication_text: Optional[str] = None
    dosage: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[str] = None
    quantity: Optional[str] = None
    timing: Optional[str] = None
    special_instructions: Optional[str] = None
    uncertainty_notes: Optional[str] = None
    confidence_score: Optional[int] = None


class ExtractedPrescription(BaseModel):
    patient_name: Optional[str] = None
    prescriber_name: Optional[str] = None
    prescription_date: Optional[str] = None
    hospital_or_clinic: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    diagnosis: Optional[str] = None
    medications: List[Medication]
    additional_notes: Optional[str] = None


class ReviewData(BaseModel):
    status: str = "pending"
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[str] = None


class RunMetadata(BaseModel):
    model_name: str
    model_version: str
    runtime: str
    latency_ms: int
    prompt_template: str


class PrescriptionRecord(BaseModel):
    record_id: str
    source_file: str
    method: str

    extracted: ExtractedPrescription
    review: ReviewData
    run_metadata: RunMetadata