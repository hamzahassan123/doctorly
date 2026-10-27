from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.elements import ColumnElement

from doctorly.models import FAQDocument
from doctorly.models.base import Base
from doctorly.services.embeddings import EmbeddingService, get_embedding_service

DocumentT = TypeVar("DocumentT", bound=Base)


class RetrievalService:
    def __init__(
        self,
        session: Session,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service or get_embedding_service()

    def search_faq(self, query: str, limit: int = 3) -> list[FAQDocument]:
        return self.search_documents(
            query=query,
            document_model=FAQDocument,
            embedding_column=FAQDocument.embedding,
            limit=limit,
        )

    def search_documents(
        self,
        *,
        query: str,
        document_model: type[DocumentT],
        embedding_column: InstrumentedAttribute[list[float]],
        filters: Sequence[ColumnElement[bool]] = (),
        limit: int = 3,
    ) -> list[DocumentT]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query cannot be empty")
        if not 1 <= limit <= 50:
            raise ValueError("Search limit must be between 1 and 50")

        query_embedding = self.embedding_service.embed_text(normalized_query)
        distance = embedding_column.cosine_distance(query_embedding)
        statement = (
            select(document_model)
            .where(embedding_column.is_not(None), *filters)
            .order_by(distance)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())
