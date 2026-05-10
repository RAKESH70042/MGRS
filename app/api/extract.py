import os

from fastapi import APIRouter, Query, HTTPException

from app.services.save_record import save_prescription_record

router = APIRouter()

# -------------------------------------------------------------------
# Provider toggle
# Set USE_MOCK=true in .env to use fake data (no model needed).
# Default is false — uses real MedGemma via local llama.cpp server.
# -------------------------------------------------------------------

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

if USE_MOCK:
    from app.providers.mock_provider import mock_extract as _extract
else:
    from app.providers.medgemma_provider import medgemma_extract as _extract


@router.get("/extract")
def extract_demo(
    file_name: str = Query(...)
):
    try:
        result = _extract(file_name)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )

    save_prescription_record(result)

    return result