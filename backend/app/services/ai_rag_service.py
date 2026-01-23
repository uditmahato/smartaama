# backend/app/services/ai_rag_service.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, TYPE_CHECKING, Any
from uuid import UUID

from app.schemas.ai import GuidelineCitation

if TYPE_CHECKING:
    from app.services.risk_engine import _LatestEvent  # type-only import to avoid circular dependency
else:
    _LatestEvent = Any


@dataclass(frozen=True)
class RagQueryContext:
    patient_id: UUID
    flags: Sequence[Tuple[str, str]]  # (section, factor)
    clinical_question: Optional[str]


class AiRagService:
    """
    Retrieval-Augmented Generation (RAG) service facade.

    Design goals:
    - Always return structured citations (even if empty).
    - Never generate autonomous clinical decisions.
    - Keep the interface stable while you iterate on vector DB / retriever / prompt design.

    NOTE:
    This initial implementation is a placeholder until you provide:
    - guideline documents
    - vector DB configuration (Qdrant or Weaviate)
    - embeddings + retrieval configuration
    """

    def __init__(self) -> None:
        # In future, initialize clients here:
        # - QdrantClient / Weaviate client
        # - embeddings model
        # - langchain retriever
        pass

    def get_guideline_citations(
        self,
        *,
        patient_id: UUID,
        latest_events: List[_LatestEvent],
        flags: List[Tuple[str, str]],
        clinical_question: Optional[str] = None,
        top_k: int = 4,
    ) -> List[GuidelineCitation]:
        """
        Return structured guideline citations relevant to:
        - the flagged risk signals (section,factor)
        - optionally a clinician-provided question

        For now, returns an empty list because guideline sources are not yet ingested.
        """
        _ = RagQueryContext(patient_id=patient_id, flags=flags, clinical_question=clinical_question)
        _ = latest_events
        _ = top_k

        # Placeholder: return empty citations until guidelines are ingested.
        return []

    # Future extension points (not yet used by risk_engine)
    def ingest_guidelines(self, documents: Sequence[str]) -> None:
        """
        Ingest guideline documents into vector DB.
        """
        raise NotImplementedError("Guideline ingestion not configured yet")

    def retrieve(self, query: str, top_k: int = 4) -> List[GuidelineCitation]:
        """
        Retrieve citations relevant to a query from vector DB.
        """
        raise NotImplementedError("Retriever not configured yet")
