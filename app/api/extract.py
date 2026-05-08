from fastapi import APIRouter, Query

from app.providers.mock_provider import mock_extract
from app.services.save_record import save_prescription_record

router = APIRouter()


@router.get("/extract")
def extract_demo(
    file_name: str = Query(...)
):

    result = mock_extract(
        file_name
    )

    save_prescription_record(result)

    return result