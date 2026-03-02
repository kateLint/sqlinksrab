"""
FastAPI REST API service for HRM portal timesheet automation.
Provides endpoints to extract PDF data, trigger automation, and check job status.

Run with: uvicorn src.api_service:app --reload
"""

import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

try:
    from .config import Config
    from .pdf_extractor import PDFExtractor
    from .portal_client import PortalClient
    from .reporting import ReportGenerator
except ImportError:
    from config import Config
    from pdf_extractor import PDFExtractor
    from portal_client import PortalClient
    from reporting import ReportGenerator

app = FastAPI(
    title="HRM Timesheet Automation API",
    description="API for automating timesheet entry into Malam HRM portal",
    version="1.0.0"
)

# In-memory job store
jobs: dict = {}


# =====================================================================
# Models
# =====================================================================

class FillTimesheetRequest(BaseModel):
    target_month: str = "2026-01"
    pdf_path: Optional[str] = None
    dry_run: bool = True
    config_path: str = "config.json"


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, waiting_for_otp, completed, failed
    created_at: str
    updated_at: str
    message: str = ""
    progress: Optional[dict] = None
    report_path: Optional[str] = None
    records_processed: int = 0
    records_total: int = 0
    results: Optional[list] = None


# =====================================================================
# Endpoints
# =====================================================================

@app.get("/")
def root():
    return {
        "service": "HRM Timesheet Automation API",
        "version": "1.0.0",
        "endpoints": {
            "POST /extract-pdf": "Upload PDF, get parsed timesheet records",
            "POST /fill-timesheet": "Trigger automation to fill timesheet",
            "GET /status/{job_id}": "Check job status",
            "GET /report/{job_id}": "Get audit report for completed job",
            "GET /jobs": "List all jobs",
        }
    }


@app.post("/extract-pdf")
async def extract_pdf(
    file: UploadFile = File(...),
    target_month: str = "2026-01"
):
    """Upload a PDF timesheet file and get parsed records as JSON."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Save uploaded file temporarily
    temp_dir = Path("output/uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"upload_{uuid.uuid4().hex[:8]}.pdf"

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Extract records
        extractor = PDFExtractor(str(temp_path), target_month=target_month)
        records = extractor.extract()

        return {
            "filename": file.filename,
            "target_month": target_month,
            "total_records": len(records),
            "records": [r.to_dict() for r in records],
            "summary": {
                "workdays_with_times": sum(
                    1 for r in records
                    if r.start_time and r.end_time
                ),
                "weekends": sum(
                    1 for r in records
                    if r.day_type in ("friday", "saturday")
                ),
                "missing_data": sum(
                    1 for r in records
                    if not r.start_time and not r.end_time
                    and r.day_type not in ("friday", "saturday")
                ),
                "flagged": sum(
                    1 for r in records
                    if r.notes
                ),
            }
        }
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@app.post("/fill-timesheet")
def fill_timesheet(request: FillTimesheetRequest):
    """
    Trigger the automation to fill timesheet data.
    Returns a job ID for tracking progress.

    Note: This requires a visible browser for OTP verification.
    The job will enter 'waiting_for_otp' status when OTP is needed.
    """
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "message": "Job created, starting automation...",
        "records_processed": 0,
        "records_total": 0,
        "results": [],
        "report_path": None,
        "request": request.model_dump(),
    }

    # Run automation in background thread
    thread = threading.Thread(
        target=_run_automation,
        args=(job_id, request),
        daemon=True
    )
    thread.start()

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Automation job started. Use GET /status/{job_id} to track progress.",
    }


@app.get("/status/{job_id}")
def get_status(job_id: str):
    """Get the status of an automation job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]
    return JobStatus(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        message=job["message"],
        records_processed=job["records_processed"],
        records_total=job["records_total"],
        results=job["results"],
        report_path=job["report_path"],
    )


@app.get("/report/{job_id}")
def get_report(job_id: str):
    """Get the audit report for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is {job['status']}, not completed yet"
        )

    report_path = job.get("report_path")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    import json
    with open(report_path, 'r', encoding='utf-8') as f:
        if report_path.endswith('.json'):
            return json.load(f)
        else:
            return {"report_path": report_path, "format": "csv"}


@app.get("/jobs")
def list_jobs():
    """List all automation jobs."""
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "created_at": j["created_at"],
                "message": j["message"],
                "records_processed": j["records_processed"],
                "records_total": j["records_total"],
            }
            for j in jobs.values()
        ]
    }


# =====================================================================
# Background automation runner
# =====================================================================

def _run_automation(job_id: str, request: FillTimesheetRequest):
    """Run the automation in a background thread."""
    job = jobs[job_id]

    try:
        # Load config
        config = Config(request.config_path)
        config._config["automation"]["target_month"] = request.target_month
        config._config["automation"]["dry_run"] = request.dry_run
        config._config["automation"]["headless"] = False  # OTP requires visible browser

        # Update job status
        job["status"] = "running"
        job["updated_at"] = datetime.now().isoformat()
        job["message"] = "Extracting PDF data..."

        # Extract PDF records
        pdf_path = request.pdf_path or "timesheet.pdf"
        extractor = PDFExtractor(pdf_path, target_month=request.target_month)
        records = extractor.extract()
        job["records_total"] = len(records)
        job["message"] = f"Extracted {len(records)} records. Starting browser..."

        # Initialize report
        report = ReportGenerator(config.report_directory)

        with PortalClient(config) as portal:
            # Login
            job["message"] = "Logging in... (OTP may be required)"
            job["status"] = "waiting_for_otp"
            job["updated_at"] = datetime.now().isoformat()

            if not portal.login():
                job["status"] = "failed"
                job["message"] = "Login failed"
                job["updated_at"] = datetime.now().isoformat()
                return

            job["status"] = "running"
            job["message"] = "Logged in. Navigating to timesheet..."
            job["updated_at"] = datetime.now().isoformat()

            # Navigate
            if not portal.navigate_to_timesheet():
                job["status"] = "failed"
                job["message"] = "Could not navigate to timesheet"
                job["updated_at"] = datetime.now().isoformat()
                return

            # Process records
            job["message"] = "Processing timesheet entries..."

            for i, record in enumerate(records, 1):
                job["records_processed"] = i
                job["message"] = f"Processing {record.work_date} ({i}/{len(records)})"
                job["updated_at"] = datetime.now().isoformat()

                try:
                    action, status = portal.enter_timesheet_data(
                        record, dry_run=config.dry_run
                    )

                    result_entry = {
                        "date": record.work_date,
                        "action": action,
                        "status": status,
                        "entry_time": record.start_time,
                        "exit_time": record.end_time,
                    }
                    job["results"].append(result_entry)

                    screenshot_path = ""
                    if action == "failed" and config.screenshots_on_failure:
                        screenshot_path = portal.take_screenshot(
                            f"failure_{record.work_date}.png"
                        )

                    report.log_action(
                        date=record.work_date,
                        action=action,
                        values=record.to_dict(),
                        status=status,
                        screenshot=screenshot_path,
                        notes=record.notes
                    )

                except Exception as e:
                    job["results"].append({
                        "date": record.work_date,
                        "action": "failed",
                        "status": str(e),
                    })

        # Generate report
        if config.report_format == "csv":
            report_path = report.generate_csv()
        else:
            report_path = report.generate_json()

        job["report_path"] = str(report_path)
        job["status"] = "completed"
        job["message"] = f"Completed. Report: {report_path}"
        job["updated_at"] = datetime.now().isoformat()

    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"Error: {str(e)}"
        job["updated_at"] = datetime.now().isoformat()
