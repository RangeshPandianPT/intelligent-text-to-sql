import abc
import httpx
from app.config import settings

class LLMClient(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str, require_json: bool = False) -> str:
        """Generates a response from the LLM based on the prompt."""
        pass

class OllamaClient(LLMClient):
    def __init__(self, host: str = None, model: str = None):
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        
    def generate(self, prompt: str, require_json: bool = False) -> str:
        url = f"{self.host.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if require_json:
            payload["format"] = "json"
            
        with httpx.Client() as client:
            try:
                response = client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
            except httpx.RequestError as e:
                raise RuntimeError(f"LLM request failed: {e}")
