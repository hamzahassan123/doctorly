import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from sqlalchemy import select

from doctorly.db.session import SessionLocal
from doctorly.models import FAQDocument
from doctorly.services.embeddings import EmbeddingService, get_embedding_service

KB_PATH = Path(__file__).resolve().parent / "data" / "hospital_kb.json"


def load_faqs(path: Path = KB_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as file:
        documents: Any = json.load(file)

    if not isinstance(documents, list):
        raise ValueError(f"{path} must contain a JSON array")

    validated_documents: list[dict[str, str]] = []
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValueError(f"FAQ entry {index} in {path} must be a JSON object")

        title = document.get("title")
        content = document.get("content")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"FAQ entry {index} in {path} must have a title")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"FAQ entry {index} in {path} must have content")

        validated_documents.append(
            {"title": title.strip(), "content": content.strip()}
        )

    return validated_documents


def slugify_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    slug = slug[:150].rstrip("-")
    if not slug:
        raise ValueError("FAQ title must produce a non-empty document key")
    return slug


def ingest_faqs(path: Path = KB_PATH) -> int:
    documents = load_faqs(path)
    document_keys = [slugify_title(document["title"]) for document in documents]
    if len(document_keys) != len(set(document_keys)):
        raise ValueError("FAQ titles must produce unique document keys")

    embedding_service: EmbeddingService = get_embedding_service()
    with SessionLocal() as session:
        for item, document_key in zip(documents, document_keys, strict=True):
            search_text = f"{item['title']}\n\n{item['content']}"
            values = {
                "document_key": document_key,
                "title": item["title"],
                "content": item["content"],
                "source": path.name,
                "metadata_json": {},
                "embedding": embedding_service.embed_text(search_text),
            }
            document = session.scalar(
                select(FAQDocument).where(
                    FAQDocument.document_key == document_key
                )
            )
            if document is None:
                session.add(FAQDocument(**values))
            else:
                for field, value in values.items():
                    setattr(document, field, value)
        session.commit()

    return len(documents)


if __name__ == "__main__":
    count = ingest_faqs()
    print(f"Ingested {count} FAQ documents.")
