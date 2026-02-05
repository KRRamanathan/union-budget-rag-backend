"""
Embedding generation service using Cohere API (free tier).
Lightweight implementation that doesn't load models into memory.
Perfect for Render's 512MB free tier.
"""
import logging
import os
import requests
import math
from typing import List, Optional
from langchain_core.embeddings import Embeddings
from app.config import Config

logger = logging.getLogger(__name__)


class CohereEmbeddings(Embeddings):
    """
    Lightweight embedding class using Cohere Embed API.
    No models loaded in memory - all embeddings via API calls.
    Free tier available: https://cohere.com/
    """
    
    def __init__(
        self,
        model_name: str = "embed-english-light-v3.0",
        api_key: Optional[str] = None
    ):
        """
        Initialize Cohere embeddings.
        
        Args:
            model_name: Cohere embedding model name (default: embed-english-v3.0)
            api_key: Cohere API key (required - get free key at https://cohere.com/)
        """
        # Validate model name is a Cohere model, not HuggingFace
        if "sentence-transformers" in model_name.lower() or "huggingface" in model_name.lower():
            logger.warning(f"Invalid model name '{model_name}' - Cohere doesn't support HuggingFace models")
            logger.warning("Defaulting to 'embed-english-v3.0'")
            model_name = "embed-english-light-v3.0"
        
        self.model_name = model_name
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "COHERE_API_KEY is required. Get a free API key at https://cohere.com/"
            )
        
        # Cohere API endpoint - use v1 for embed endpoint
        self.api_url = "https://api.cohere.ai/v1/embed"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info(f"Initialized Cohere embeddings: {model_name}")
        logger.info(f"Cohere API URL: {self.api_url}")
        logger.info(f"Cohere Model: {self.model_name}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            # Cohere supports up to 96 texts per request
            batch_size = 96
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                payload = {
                    "texts": batch,
                    "model": self.model_name,
                    "input_type": "search_document"  # Use "search_query" for queries
                }
                
                logger.debug(f"Calling Cohere API: {self.api_url} with model: {self.model_name}")
                
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"Cohere API error: Status {response.status_code}")
                    logger.error(f"Request URL: {self.api_url}")
                    logger.error(f"Request payload: {payload}")
                    logger.error(f"Response: {response.text[:1000]}")
                
                response.raise_for_status()
                result = response.json()
                
                # Extract embeddings from response
                batch_embeddings = result.get("embeddings", [])
                all_embeddings.extend(batch_embeddings)
            
            # Normalize embeddings for cosine similarity (L2 normalization)
            normalized = []
            for emb in all_embeddings:
                # Calculate L2 norm
                norm = math.sqrt(sum(x * x for x in emb))
                if norm > 0:
                    # Normalize
                    normalized.append([x / norm for x in emb])
                else:
                    normalized.append(emb)
            
            return normalized
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {str(e)}"
            if e.response.status_code == 401:
                error_msg += " - Invalid or missing Cohere API key."
            elif e.response.status_code == 429:
                error_msg += " - Rate limit exceeded. Cohere free tier has limits."
            logger.error(f"Failed to get embeddings from Cohere API: {error_msg}")
            if hasattr(e, 'response') and e.response.text:
                logger.error(f"Response: {e.response.text[:500]}")
            raise RuntimeError(f"Embedding API error: {error_msg}")
        except Exception as e:
            logger.error(f"Failed to get embeddings from Cohere API: {str(e)}")
            raise RuntimeError(f"Embedding API error: {str(e)}")
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            payload = {
                "texts": [text],
                "model": self.model_name,
                "input_type": "search_query"  # Use search_query for queries
            }
            
            logger.debug(f"Calling Cohere API: {self.api_url} with model: {self.model_name}")
            logger.debug(f"Payload keys: {list(payload.keys())}")
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Log response for debugging
            if response.status_code != 200:
                logger.error(f"Cohere API error: Status {response.status_code}")
                logger.error(f"Request URL: {self.api_url}")
                logger.error(f"Request payload: {payload}")
                logger.error(f"Response: {response.text[:1000]}")
            
            response.raise_for_status()
            result = response.json()
            
            # Extract embedding
            if "embeddings" not in result or not result["embeddings"]:
                logger.error(f"Unexpected Cohere API response: {result}")
                raise ValueError(f"Cohere API returned no embeddings: {result}")
            
            embedding = result.get("embeddings", [])[0]
            
            # Normalize for cosine similarity
            norm = math.sqrt(sum(x * x for x in embedding))
            if norm > 0:
                embedding = [x / norm for x in embedding]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get query embedding from Cohere API: {str(e)}")
            raise RuntimeError(f"Embedding API error: {str(e)}")


# Global embeddings instance (lightweight, no model loading)
_embeddings: Optional[CohereEmbeddings] = None


def get_embeddings() -> CohereEmbeddings:
    """
    Get or initialize the embedding service.
    Uses Cohere API - no models loaded in memory.
    
    Returns:
        CohereEmbeddings instance
    """
    global _embeddings
    
    if _embeddings is None:
        logger.info(f"Initializing Cohere embeddings: {Config.EMBEDDING_MODEL_NAME}")
        _embeddings = CohereEmbeddings(
            model_name=Config.EMBEDDING_MODEL_NAME,
            api_key=Config.COHERE_API_KEY
        )
        logger.info("Cohere embeddings initialized (no models in memory)")
    
    return _embeddings


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a single text string.
    
    Args:
        text: The text to embed
        
    Returns:
        List of floats representing the embedding vector
    """
    embeddings = get_embeddings()
    return embeddings.embed_query(text)


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch.
    More efficient than generating one at a time.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    embeddings = get_embeddings()
    logger.debug(f"Generating embeddings for {len(texts)} texts via Cohere API")
    
    return embeddings.embed_documents(texts)


def preload_model():
    """
    Preload/validate the embedding API connection.
    No actual model loading - just test the API connection.
    """
    try:
        # Test the API with a simple query
        test_embedding = generate_embedding("test")
        logger.info(f"Embedding API validated (test embedding dimension: {len(test_embedding)})")
    except Exception as e:
        logger.warning(f"Embedding API validation failed: {str(e)}")
        logger.info("API will be tested on first real request")
