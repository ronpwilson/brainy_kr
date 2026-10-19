from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import chromadb
from sentence_transformers import SentenceTransformer

class VectorService:
    COLLECTION_NAME = "rbi_study_material"

    CATEGORIES = [
        "Current Affairs",
        "Previous Year Question Papers",
        "Official RBI Material",
        "Economics & Social Issues",
        "Finance & Management",
        "Quantitative Aptitude",
        "Reasoning",
        "English",
        "General Study Notes",
    ]

    def __init__(self):
        db_path = Path(__file__).resolve().parents[2] / "chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)

        print(f"ChromaDB path: {db_path.resolve()}")

        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME
        )
        self.embedding_model = SentenceTransformer(
            "BAAI/bge-small-en-v1.5"
        )

    def add_chunks(
        self,
        chunks: list[dict],
        filename: str,
        user_id: int | None,
        category: str = "General Study Notes",
    ) -> dict:
        if not chunks:
            return {
                "document_id": None,
                "stored_chunk_count": 0,
            }

        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid document category: {category}")

        document_id = str(uuid4())
        texts = [chunk["text"] for chunk in chunks]

        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
        ).tolist()

        upload_time = datetime.now(timezone.utc).isoformat()
        ids = [
            f"{document_id}_{index}"
            for index in range(len(chunks))
        ]

        metadatas = [
            {
                "document_id": document_id,
                "filename": filename,
                "category": category,
                "page_number": chunk["page_number"],
                "user_id": str(user_id) if user_id is not None else "",
                "uploaded_at": upload_time,
            }
            for chunk in chunks
        ]

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return {
            "document_id": document_id,
            "stored_chunk_count": len(chunks),
        }


    def search(
            self,
            query: str,
            user_id: int | None,
            top_k: int = 3,
            categories: list[str] | None = None,
    ) -> list[dict]:
        # Return immediately if the collection is empty.
        total_chunks = self.collection.count()
        if total_chunks == 0:
            return []

        # Convert the query into an embedding.
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True,
        ).tolist()

        # Shared library: do not filter results by user_id.
        # If categories are supplied, search only those categories.
        where = None

        if categories:
            invalid_categories = [
                category
                for category in categories
                if category not in self.CATEGORIES
            ]

            if invalid_categories:
                raise ValueError(
                    f"Invalid categories: {invalid_categories}"
                )

            where = {
                "category": {
                    "$in": categories
                }
            }

        # Search ChromaDB for the most relevant chunks.
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, total_chunks),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # Format the results for the RAG pipeline.
        return [
            {
                "text": document,
                "document_id": metadata.get("document_id"),
                "page_number": metadata.get("page_number"),
                "filename": metadata.get("filename"),
                "category": metadata.get("category"),
                "distance": distance,
            }
            for document, metadata, distance
            in zip(documents, metadatas, distances)
        ]


    def list_documents(self) -> list[dict]:
        results = self.collection.get(
            include=["metadatas"]
        )

        documents = {}

        for metadata in results.get("metadatas", []):
            if not metadata:
                continue

            document_id = metadata.get("document_id")

            # Ignore legacy chunks that don't have document IDs.
            if not document_id:
                continue

            if document_id not in documents:
                documents[document_id] = {
                    "document_id": document_id,
                    "filename": metadata.get("filename", ""),
                    "category": metadata.get(
                        "category", "General Study Notes"
                    ),
                    "uploaded_at": metadata.get("uploaded_at", ""),
                    "user_id": metadata.get("user_id", ""),
                    "chunk_count": 0,
                }

            documents[document_id]["chunk_count"] += 1

        return sorted(
            documents.values(),
            key=lambda item: item["uploaded_at"],
            reverse=True,
        )

    def delete_document(self, document_id: str) -> int:
        results = self.collection.get(
            where={"document_id": document_id},
            include=[],
        )

        ids = results.get("ids", [])

        if ids:
            self.collection.delete(ids=ids)

        return len(ids)
