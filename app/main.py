import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.document_service import DocumentService


logger = logging.getLogger(__name__)

app = FastAPI(
    title="RBI Grade B AI Study Assistant",
    version="0.2.0",
)

document_service = DocumentService()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
MAX_UPLOAD_SIZE_MB = 25
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024

CATEGORIES = document_service.vector_service.CATEGORIES

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


@app.get("/")
async def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/categories")
async def get_categories():
    return {"categories": CATEGORIES}


@app.get("/api/documents")
async def list_documents():
    try:
        return {"documents": document_service.list_documents()}
    except Exception:
        logger.exception("Failed to list documents")
        raise HTTPException(
            status_code=500,
            detail="Failed to list documents.",
        )


@app.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
):
    if category not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid document category.",
        )

    filename = Path(file.filename or "").name

    if not filename or Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    temp_path = None

    try:
        content = await file.read(MAX_UPLOAD_SIZE + 1)

        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Maximum upload size is {MAX_UPLOAD_SIZE_MB} MB.",
            )

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid PDF.",
            )

        with tempfile.TemporaryDirectory(
            prefix="rbi_dashboard_upload_"
        ) as temp_dir:
            temp_path = Path(temp_dir) / filename
            temp_path.write_bytes(content)

            result = document_service.process_pdf(
                file_path=temp_path,
                original_filename=filename,
                user_id=None,
                category=category,
            )

            if result["stored_chunk_count"] == 0:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "No extractable text was found in the PDF. "
                        "Scanned PDFs may require OCR."
                    ),
                )

            return {
                "message": "Document uploaded successfully.",
                **result,
            }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to process uploaded PDF")
        raise HTTPException(
            status_code=500,
            detail="Failed to process the PDF.",
        )
    finally:
        await file.close()


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        deleted_chunks = document_service.delete_document(document_id)

        if deleted_chunks == 0:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        return {
            "message": "Document deleted successfully.",
            "document_id": document_id,
            "deleted_chunks": deleted_chunks,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete document")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete document.",
        )