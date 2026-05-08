from app.schemas.prescription import PrescriptionRecord
import uuid

def mock_extract(file_name: str):

    result = PrescriptionRecord(
        record_id=f"RX-{uuid.uuid4().hex[:8]}",
        source_file=file_name,
        method="medgemma",

        extracted={
            "patient_name": "Demo Patient",
            "prescriber_name": "Dr. Demo",
            "prescription_date": "2026-05-06",

            "medications": [
                {
                    "medication_name": "Paracetamol",
                    "dosage": "500",
                    "unit": "mg",
                    "frequency": "Twice daily",
                    "route": "Oral",
                    "duration": "5 days",
                    "special_instructions": "After food",
                    "uncertainty_notes": "Handwriting slightly unclear"
                }
            ]
        },

        review={
            "status": "pending",
            "reviewer_notes": None,
            "reviewed_at": None
        },

        run_metadata={
            "model_name": "MockMedGemma",
            "model_version": "0.1",
            "runtime": "local",
            "latency_ms": 850,
            "prompt_template": "default-v1"
        }
    )

    return result