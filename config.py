import os

from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class LLMRateLimit(BaseModel):
    requests: float
    period_seconds: int

class LLMConfig(BaseModel):
    model_name: str
    max_context_tokens: int
    soft_context_limit_tokens: int
    rate_limits: List[LLMRateLimit]
    input_price_per_million_tokens: float
    output_price_per_million_tokens: float
    provider: str

class EmbeddingConfig(BaseModel):
    model_name: str
    max_tokens: int
    dimension: int
    price_per_million_tokens: float
    provider: str

class AIProviderConfig(BaseModel):
    llms: Dict[str, LLMConfig] = Field(default_factory=dict)
    embeddings: Dict[str, EmbeddingConfig] = Field(default_factory=dict)

class AIConfigModel(BaseModel):
    google: AIProviderConfig
    local: AIProviderConfig

# --- AI Model Configuration (using Pydantic models) ---
# Central, type-safe configuration for all AI models.
# This single object is the source of truth.
MASTER_AI_CONFIG = AIConfigModel(
    google=AIProviderConfig(
        llms={
            "gemini-2.5-flash-lite-preview-06-17": LLMConfig(
                model_name="gemini-2.5-flash-lite-preview-06-17",
                max_context_tokens=131072,
                soft_context_limit_tokens=16384,  # ~12.5% of max
                rate_limits=[LLMRateLimit(requests=1, period_seconds=1), LLMRateLimit(requests=60, period_seconds=60)],
                input_price_per_million_tokens=0.35,
                output_price_per_million_tokens=1.05,
                provider="google"
            ),
            "gemini-2.5-flash": LLMConfig(
                model_name="gemini-2.5-flash",
                max_context_tokens=1048576,
                soft_context_limit_tokens=131072,
                rate_limits=[LLMRateLimit(requests=1, period_seconds=1), LLMRateLimit(requests=60, period_seconds=60)],
                input_price_per_million_tokens=0.35,
                output_price_per_million_tokens=1.05,
                provider="google",
                api_key=os.getenv("GOOGLE_API_KEY")
            ),
            "gemma-3-27b-it": LLMConfig(
                model_name="gemma-3-27b-it",
                max_context_tokens=131072,
                soft_context_limit_tokens=16384,
                rate_limits=[LLMRateLimit(requests=0.5, period_seconds=1),
                             LLMRateLimit(requests=30, period_seconds=60)],
                input_price_per_million_tokens=0.0,
                output_price_per_million_tokens=0.0,
                provider="google"
            )
        }
    ),
    local=AIProviderConfig(
        embeddings={
            "alikia2x/jina-embedding-v3-m2v-1024": EmbeddingConfig(
                model_name="alikia2x/jina-embedding-v3-m2v-1024",
                max_tokens=1024,
                dimension=1024,
                # Placeholder cost for local model based on estimated hardware/power usage.
                # E.g., ~$0.02 per million tokens on a mid-range GPU.
                price_per_million_tokens=0.002,
                provider="local"
            ),
            "jinaai/jina-embeddings-v2-base-code": EmbeddingConfig(
                model_name="jinaai/jina-embeddings-v2-base-code",
                max_tokens=1024,
                dimension=768,
                price_per_million_tokens=0.02,
                provider="local"
            )
        }
    )
)


class AIConfig:
    """A static class to provide convenient access to the active model configurations."""
    # Define the active models to be used by the application
    ACTIVE_LLM_MODEL = "gemini-2.5-flash"
    # ACTIVE_EMBEDDING_MODEL = "alikia2x/jina-embedding-v3-m2v-1024"
    ACTIVE_EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-base-code"

    # --- LLM Access ---
    @classmethod
    def get_active_llm_config(cls) -> dict:
        """Returns the full configuration object for the currently active LLM."""
        for provider_conf in MASTER_AI_CONFIG.model_dump().values():
            if cls.ACTIVE_LLM_MODEL in provider_conf.get('llms', {}):
                return provider_conf['llms'][cls.ACTIVE_LLM_MODEL]
        raise ValueError(f"Active LLM '{cls.ACTIVE_LLM_MODEL}' not found in any provider configuration.")

    @classmethod
    def get_all_llm_configs(cls) -> dict[str, LLMConfig]:
        """Returns a unified dictionary of all configured LLMs."""
        all_llms = {}
        for provider_conf in MASTER_AI_CONFIG.model_dump().values():
            all_llms.update(provider_conf.get('llms', {}))
        return {name: LLMConfig(**conf) for name, conf in all_llms.items()}

    # --- Embedding Access ---
    @classmethod
    def get_active_embedding_config(cls) -> EmbeddingConfig:
        """Returns the full configuration object for the currently active embedding model."""
        for provider_conf in MASTER_AI_CONFIG.model_dump().values():
            if cls.ACTIVE_EMBEDDING_MODEL in provider_conf.get('embeddings', {}):
                return EmbeddingConfig(**provider_conf['embeddings'][cls.ACTIVE_EMBEDDING_MODEL])
        raise ValueError(
            f"Active embedding model '{cls.ACTIVE_EMBEDDING_MODEL}' not found in any provider configuration.")

    # --- General Properties ---
    EMBEDDING_DEVICES = ["auto"]
    MAX_EMBEDDING_WORKERS = 2
    VECTOR_COLLECTION_NAME = "code_chunks"