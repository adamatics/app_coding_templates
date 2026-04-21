from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.db import get_session
from app.schemas.report import CsvAnalysis
from app.services import reports as service

router = APIRouter(prefix="/reports", tags=["reports"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/analyze-csv", response_model=CsvAnalysis)
async def analyze_csv(
    file: UploadFile = File(...),
    _user: str = Depends(get_current_user),
) -> CsvAnalysis:
    if not (file.filename and file.filename.lower().endswith(".csv")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only .csv files are accepted. Swap csv for openpyxl here to parse .xlsx.",
        )
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "File too large (5 MB max).",
        )
    result = service.analyze_csv_bytes(file.filename, content)
    return CsvAnalysis.model_validate(result)


@router.get("/employees.csv")
def export_employees_csv(
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> Response:
    payload = service.export_employees_csv(session)
    return Response(
        content=payload,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="employees.csv"'},
    )


@router.get("/employees.xlsx")
def export_employees_xlsx(
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> Response:
    payload = service.export_employees_xlsx(session)
    return Response(
        content=payload,
        media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        headers={"Content-Disposition": 'attachment; filename="employees.xlsx"'},
    )
