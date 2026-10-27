import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from doctorly.models import Base, FAQDocument
from doctorly.services.embeddings import get_embedding_service
from doctorly.services.retrieval import RetrievalService

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="Set TEST_DATABASE_URL to run PostgreSQL retrieval tests",
)


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL retrieval tests")

    admin_engine = create_engine(database_url, pool_pre_ping=True)
    with admin_engine.connect() as connection:
        extension_exists = connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
    if not extension_exists:
        admin_engine.dispose()
        pytest.fail(
            "pgvector extension is missing; apply the FAQ vector Alembic migration first"
        )

    schema_name = f"doctorly_retrieval_test_{uuid4().hex}"
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    test_engine = admin_engine.execution_options(
        schema_translate_map={None: schema_name}
    )
    try:
        Base.metadata.create_all(test_engine)
        yield test_engine
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        admin_engine.dispose()


def test_retrieval_finds_cancellation_and_mri_documents(
    postgres_engine: Engine,
) -> None:
    embedding_service = get_embedding_service()
    documents = (
        {
            "document_key": "test-cancellation",
            "title": "Appointment cancellation policy",
            "content": (
                "Cancel an appointment by contacting the hospital appointments "
                "desk at least 24 hours before the visit."
            ),
            "source": "synthetic://test/cancellation",
            "metadata_json": {"category": "cancellation"},
        },
        {
            "document_key": "test-mri-prep",
            "title": "MRI preparation guide",
            "content": (
                "Before an MRI scan, follow imaging instructions and tell staff "
                "about implants or metal fragments. Remove metal objects."
            ),
            "source": "synthetic://test/mri-prep",
            "metadata_json": {"category": "preparation"},
        },
        {
            "document_key": "test-visiting",
            "title": "Hospital visiting hours",
            "content": "Visitors are welcome from 10 AM to 8 PM each day.",
            "source": "synthetic://test/visiting",
            "metadata_json": {"category": "visiting"},
        },
    )

    with Session(postgres_engine) as session:
        for document in documents:
            session.add(
                FAQDocument(
                    **document,
                    embedding=embedding_service.embed_text(document["content"]),
                )
            )
        session.commit()

        retrieval = RetrievalService(session, embedding_service=embedding_service)
        cancellation_results = retrieval.search_faq("How do I cancel?", limit=1)
        mri_results = retrieval.search_faq("MRI prep before scan", limit=1)

    assert len(cancellation_results) == 1
    assert cancellation_results[0].document_key == "test-cancellation"
    assert len(mri_results) == 1
    assert mri_results[0].document_key == "test-mri-prep"


def test_generic_retrieval_applies_document_metadata_filters(
    postgres_engine: Engine,
) -> None:
    embedding_service = get_embedding_service()
    content = "Cancel an appointment by contacting the appointments desk."
    with Session(postgres_engine) as session:
        session.add_all(
            [
                FAQDocument(
                    document_key="filtered-cancellation",
                    title="Cancellation",
                    content=content,
                    source="synthetic://test/cancellation",
                    metadata_json={"category": "cancellation"},
                    embedding=embedding_service.embed_text(content),
                ),
                FAQDocument(
                    document_key="filtered-other-cancellation",
                    title="Other cancellation",
                    content=content,
                    source="synthetic://test/other-cancellation",
                    metadata_json={"category": "other"},
                    embedding=embedding_service.embed_text(content),
                ),
            ]
        )
        session.commit()
        retrieval = RetrievalService(session, embedding_service=embedding_service)
        results = retrieval.search_documents(
            query="cancel appointment",
            document_model=FAQDocument,
            embedding_column=FAQDocument.embedding,
            filters=[
                FAQDocument.metadata_json["category"].as_string() == "cancellation"
            ],
        )

    assert [document.document_key for document in results] == [
        "filtered-cancellation"
    ]
