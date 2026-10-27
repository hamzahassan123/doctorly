import json
from pathlib import Path

import pytest

from scripts.ingest_faqs import load_faqs, slugify_title


def test_loads_hospital_kb_json_documents() -> None:
    documents = load_faqs()

    assert len(documents) == 30
    assert all(document["title"] and document["content"] for document in documents)


def test_slugifies_titles_stably() -> None:
    assert slugify_title("MRI Prep: Before Your Scan!") == "mri-prep-before-your-scan"
    assert slugify_title("Résumé — Doctor Profile") == "resume-doctor-profile"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [None],
        [{"title": "Title only"}],
        [{"title": "", "content": "Content"}],
    ],
)
def test_rejects_malformed_knowledge_base(
    tmp_path: Path,
    payload: object,
) -> None:
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        load_faqs(source)


def test_rejects_title_slug_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import ingest_faqs

    source = tmp_path / "duplicate-slugs.json"
    source.write_text(
        json.dumps(
            [
                {"title": "Policy: Cancel", "content": "First"},
                {"title": "Policy Cancel", "content": "Second"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ingest_faqs, "get_embedding_service", lambda: object())

    with pytest.raises(ValueError, match="unique document keys"):
        ingest_faqs.ingest_faqs(source)


def test_ingestion_embeds_title_and_content_and_upserts_by_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import ingest_faqs

    source = tmp_path / "hospital_kb.json"
    source.write_text(
        json.dumps(
            [
                {"title": "MRI Prep", "content": "Before the scan."},
            ]
        ),
        encoding="utf-8",
    )

    class FakeEmbeddingService:
        def __init__(self) -> None:
            self.inputs: list[str] = []

        def embed_text(self, text: str) -> list[float]:
            self.inputs.append(text)
            return [0.0] * 384

    class FakeSession:
        def __init__(self) -> None:
            self.documents = []
            self.committed = False

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def scalar(self, _statement):
            return None

        def add(self, document) -> None:
            self.documents.append(document)

        def commit(self) -> None:
            self.committed = True

    embedding_service = FakeEmbeddingService()
    session = FakeSession()
    monkeypatch.setattr(ingest_faqs, "get_embedding_service", lambda: embedding_service)
    monkeypatch.setattr(ingest_faqs, "SessionLocal", lambda: session)

    count = ingest_faqs.ingest_faqs(source)

    assert count == 1
    assert embedding_service.inputs == ["MRI Prep\n\nBefore the scan."]
    assert session.committed is True
    assert session.documents[0].document_key == "mri-prep"
    assert session.documents[0].source == "hospital_kb.json"
