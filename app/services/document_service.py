from pathlib import Path

import pymupdf

from app.services.vector_service import VectorService

class DocumentService:
    CHUNK_SIZE = 1200
    CHUNK_OVERLAP = 200

    def __init__(self):
        self.vector_service = VectorService()

    def process_pdf(
        self,
        file_path: Path,
        original_filename: str,
        user_id: int | None,
        category: str = "General Study Notes",
    ) -> dict:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Temporary file does not exist: {file_path}"
            )

        pages = self.extract_pages(file_path)
        chunks = self.create_chunks(pages)

        result = self.vector_service.add_chunks(
            chunks=chunks,
            filename=original_filename,
            user_id=user_id,
            category=category,
        )

        return {
            "document_id": result["document_id"],
            "filename": original_filename,
            "category": category,
            "size_bytes": file_path.stat().st_size,
            "user_id": user_id,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "stored_chunk_count": result["stored_chunk_count"],
            "status": "embedded_and_stored",
        }

    def extract_pages(self, file_path: Path) -> list[dict]:
        pages = []

        with pymupdf.open(file_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text", sort=True).strip()

                if text:
                    pages.append({
                        "page_number": page_number,
                        "text": text,
                    })

        return pages

    def create_chunks(self, pages: list[dict]) -> list[dict]:
        chunks = []

        for page in pages:
            text = page["text"]
            start = 0
            text_length = len(text)

            while start < text_length:
                end = start + self.CHUNK_SIZE
                chunk_text = text[start:end].strip()

                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "page_number": page["page_number"],
                    })

                if end >= text_length:
                    break

                start = end - self.CHUNK_OVERLAP

        return chunks

    def search(
        self,
        query: str,
        user_id: int | None,
        categories: list[str] | None = None,
    ) -> list[dict]:
        return self.vector_service.search(
            query=query,
            user_id=user_id,
            top_k=3,
            categories=categories,
        )

    def list_documents(self) -> list[dict]:
        return self.vector_service.list_documents()

    def delete_document(self, document_id: str) -> int:
        return self.vector_service.delete_document(document_id)
