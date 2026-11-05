import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.import_job import ImportJob
from app.schemas.import_job import ImportJobResponse, ImportSummaryResponse
from app.services.ingestion_service import IngestionService
from app.api.deps import get_current_user, require_role
from app.config import settings

router = APIRouter(prefix="/imports", tags=["Incident & Rule Ingestion"])


@router.post("/upload", response_model=ImportSummaryResponse)
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "upload"
    lower_name = filename.lower()

    # Read content with size check
    content = await file.read()
    if len(content) > settings.UPLOAD_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds maximum allowed size of {settings.UPLOAD_MAX_FILE_SIZE // (1024 * 1024)} MB"
        )

    ingestion_service = IngestionService(db)

    if lower_name.endswith(".zip"):
        job, summary = await ingestion_service.ingest_zip(
            file_bytes=content,
            filename=filename,
            username=current_user.username
        )
        return ImportSummaryResponse(**summary)

    elif lower_name.endswith(".json"):
        try:
            raw_json = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")

        job, result, msg = await ingestion_service.ingest_single_json(
            raw_data=raw_json,
            filename=filename,
            username=current_user.username
        )

        return ImportSummaryResponse(
            job_id=job.id,
            status=job.status,
            filename=filename,
            total_found=1,
            imported=1 if result == "imported" else 0,
            duplicates=1 if result == "duplicate" else 0,
            rules_detected=0,
            errors=1 if result == "error" else 0,
            error_messages=[msg] if result == "error" else [],
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a .json file or a .zip archive containing incident JSONs and rule descriptions."
        )


@router.get("/jobs", response_model=List[ImportJobResponse])
async def list_import_jobs(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ImportJob).order_by(desc(ImportJob.created_at)).limit(limit)
    res = await db.execute(stmt)
    jobs = res.scalars().all()
    return [ImportJobResponse.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ImportJob).where(ImportJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return ImportJobResponse.model_validate(job)

