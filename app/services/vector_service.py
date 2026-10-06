from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


class VectorService:
    COLLECTION_NAME = "rbi_study_material"

    def __init__(self):
        db_path = Path("chroma_db")
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(db_path)
        )

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
    ) -> int:

        if not chunks:
            return 0

        texts = [chunk["text"] for chunk in chunks]

        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
        ).tolist()

        ids = [
            f"{user_id}_{filename}_{index}"
            for index in range(len(chunks))
        ]

        metadatas = [
            {
                "filename": filename,
                "page_number": chunk["page_number"],
                "user_id": str(user_id) if user_id else "",
            }
            for chunk in chunks
        ]

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return len(chunks)

    def search(
            self,
            query: str,
            user_id: int | None,
            top_k: int = 3,
    ) -> list[dict]:
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True,
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return [
            {
                "text": document,
                "page_number": metadata.get("page_number"),
                "filename": metadata.get("filename"),
                "distance": distance,
            }
            for document, metadata, distance
            in zip(documents, metadatas, distances)
        ]