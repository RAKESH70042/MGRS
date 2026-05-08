from fastapi import APIRouter
from app.schemas.prescription import PrescriptionRecord

router = APIRouter()


@router.get("/test-schema")
def test_schema():

    sample = PrescriptionRecord(
        record_id="RX001",
        source_file="demo.png",
        method="medgemma",

        extracted={
            "patient_name": "John Doe",
            "prescriber_name": "Dr. Smith",
            "prescription_date": "2026-05-06",
            "medications": [
                {
                    "medication_name": "Paracetamol",
                    "dosage": "500",
                    "unit": "mg",
                    "frequency": "Twice daily"
                }
            ]
        },

        review={
            "status": "pending"
        },

        run_metadata={
            "model_name": "MockMedGemma",
            "model_version": "0.1",
            "runtime": "local",
            "latency_ms": 1200,
            "prompt_template": "default-v1"
        }
    )

    return sample