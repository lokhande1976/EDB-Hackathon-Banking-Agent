import os
from functools import cached_property

from dotenv import load_dotenv
from google.adk.models.google_llm import Gemini
from google.genai import Client

load_dotenv()


class VertexGemini(Gemini):
    """Gemini via Vertex AI — uses Application Default Credentials."""

    @cached_property
    def api_client(self) -> Client:
        return Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )


def get_model(model_name: str | None = None) -> Gemini:
    """Return Gemini via API key if set, otherwise via Vertex AI (ADC)."""
    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
    if os.getenv("GOOGLE_API_KEY"):
        return Gemini(model=model_name)
    return VertexGemini(model=model_name)
