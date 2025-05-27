"""
Embeddings module for generating text embeddings using Google Generative AI.
"""
import os
import logging
from typing import Optional
from google import genai
import dotenv

dotenv.load_dotenv()

EMBEDDING_MODEL = "gemini-pro"  # Update to your preferred embedding model

class Embedder:
    """
    Utility class for generating text embeddings using Google Generative AI.
    """
    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment.")
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(EMBEDDING_MODEL)
        except Exception as e:
            logging.error(f"Failed to initialize embedding model: {e}")
            raise

    def embed(self, text: str) -> Optional[list]:
        """
        Generate an embedding for the given text.
        Args:
            text (str): The text to embed.
        Returns:
            Optional[list]: The embedding vector, or None on failure.
        """
        try:
            response = self.model.generate_content(
                text,
                generation_config=genai.GenerativeModel.GenerativeConfig(
                    embedding=True
                )
            )
            return getattr(response, 'embedding', None)
        except Exception as e:
            logging.error(f"Embedding generation failed: {e}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    embedder = Embedder()
    example_text = "Explain how AI works in a few words."
    embedding = embedder.embed(example_text)
    print(embedding)