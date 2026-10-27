from functools import lru_cache

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


class EmbeddingService:
    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        device: str | None = None,
    ) -> None:
        self.model = SentenceTransformer(model_name, device=device)
        if self.model.get_embedding_dimension() != EMBEDDING_DIMENSION:
            raise ValueError(
                f"{model_name} must produce {EMBEDDING_DIMENSION}-dimension vectors"
            )

    def embed_text(self, text: str) -> list[float]:
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Text to embed cannot be empty")

        embedding = self.model.encode(
            normalized_text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [float(value) for value in embedding]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
