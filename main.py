from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.storage.database import engine
from app.storage.models import Base
from app.storage.consultation_models import ConsultationDB

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)
ConsultationDB.metadata.create_all(bind=engine)

from app.api.health           import router as health_router
from app.api.upload           import router as upload_router
from app.api.test_schema      import router as schema_router
from app.api.extract          import router as extract_router
from app.api.records          import router as records_router
from app.api.review           import router as review_router
from app.api.export           import router as export_router
from app.api.transcription    import router as transcription_router
from app.api.consultation_api import router as consultation_router
from app.api.report           import router as report_router

import os

app = FastAPI(title="MedGemma Prescription Review", version="0.2.0")

app.include_router(health_router)
app.include_router(schema_router)
app.include_router(upload_router)
app.include_router(extract_router)
app.include_router(records_router)
app.include_router(review_router)
app.include_router(export_router)
app.include_router(transcription_router)
app.include_router(consultation_router)
app.include_router(report_router)


@app.get("/")
def root():
    use_mock = os.getenv("USE_MOCK", "false").lower() == "true"
    return {
        "message": "MedGemma Prescription Review API",
        "version": "0.2.0",
        "provider": "mock" if use_mock else "medgemma-llama-cpp-local",
    }