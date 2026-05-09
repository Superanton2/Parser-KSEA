import os
import shutil
import subprocess
from typing import Optional

import requests
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

# Constants
DEFAULT_BASE_URL = "https://router.huggingface.co/v1"
OLLAMA_BASE_URL = "http://localhost:11434"

# A more robust few-shot detection prompt (RAG-style) with examples and
# a short checklist. The model should answer only 'Yes' or 'No'.
ARTICLE_DETECTION_PROMPT = (
    "You are a classifier that answers ONLY 'Yes' or 'No'.\n"
    "Decide whether the provided text is a news/article-style publication (report, blog post, research article)\n"
    "or a non-article (listing, directory entry, social post, short snippet, comment, index, login page, catalog).\n\n"
    "Checklist:\n"
    "- Does the text have a clear prose structure (multiple paragraphs, full sentences)?\n"
    "- Is there a byline, date, or publisher metadata?\n"
    "- Is the length substantial (e.g., >200 words)?\n"
    "- Does the text include narrative, analysis, or reporting language (e.g., 'reported', 'studied', 'found', 'according to')?\n\n"
    "Respond ONLY with 'Yes' if it's an article, otherwise 'No'.\n\n"
    "Example 1:\nTitle: Local festival draws crowds\nBody: Thousands of people gathered... (full paragraph)\nAnswer: Yes\n\n"
    "Example 2:\nSnippet: Contact us at info@example.com or call 123-456\nAnswer: No\n\n"
    "Now classify the following text:\n\n{text}\n\nContext: {context}\nAnswer:"
)

SYSTEM_PROMPT = "You are a strict classifier that must output only Yes or No."


class LLM:
    """A wrapper class for interacting with LLM models via OpenAI-compatible API or local Ollama.

    Supports three modes (in order of preference):
      - Ollama local (if `use_ollama=True`) via local HTTP API or CLI fallback
      - OpenAI-compatible client via `openai.OpenAI`

    The class provides a RAG-like `is_article` classifier that includes a simple
    heuristic context (length, presence of dates/byline) plus a few-shot prompt.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        use_ollama: bool = False,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url or DEFAULT_BASE_URL
        # Ollama always uses its own local URL; `base_url` is only for the remote client.
        self.ollama_base_url = OLLAMA_BASE_URL
        self.use_ollama = bool(use_ollama)

        # Resolve API key from provided value or environment variables
        resolved_api_key = api_key or os.getenv(
            "HF_API_KEY") or os.getenv("OPENAI_API_KEY")
        try:
            self.client = OpenAI(base_url=self.base_url,
                                 api_key=resolved_api_key)
        except Exception:
            self.client = None

    def _create_completion(self, prompt: str, max_tokens: int = 64, temperature: float = 0.0) -> str:
        """Create a completion using either Ollama (local) or the OpenAI-compatible client.

        Returns the model text or empty string on failure.
        """
        # Prefer Ollama/local if requested
        if self.use_ollama:
            try:
                return self._call_local_model(prompt, max_tokens=max_tokens)
            except Exception as e:
                logger.debug("Ollama/local model error: %s -- falling back to remote client", e)

        # Fall back to OpenAI-compatible client
        if self.client is None:
            logger.debug("No remote client configured and Ollama not available.")
            return ""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {
                    "role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Tolerant extraction of text
            try:
                return response.choices[0].message.content.strip()
            except Exception:
                try:
                    return str(response["choices"][0]["message"]["content"]).strip()
                except Exception:
                    return str(response).strip()

        except Exception as e:
            logger.debug("LLM API error: %s", e)
            return ""

    def _call_local_model(self, prompt: str, max_tokens: int = 64) -> str:
        """Attempt to call a local Ollama model.

        Strategy:
          1. Try the local HTTP API at http://localhost:11434/api/generate
          2. If that fails, try the `ollama` CLI (if installed)

        This function uses tolerant parsing to extract text from various response shapes.
        """
        # HTTP endpoint attempt
        try:
            url = self.ollama_base_url.rstrip("/") + "/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "num_predict": max_tokens,
                "stream": False,
            }
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()

            # Try common response shapes
            if isinstance(data, dict):
                # Ollama /api/generate returns {"response": "..."}
                if "response" in data and isinstance(data["response"], str):
                    return data["response"].strip()

                # Fallback: other nested shapes
                results = data.get("results") or data.get("choices")
                if results and isinstance(results, list):
                    # search nested dicts for text fields
                    for res in results:
                        if isinstance(res, dict):
                            for key in ("content", "text", "output", "message"):
                                val = res.get(key)
                                if isinstance(val, str) and val.strip():
                                    return val.strip()
                            # deeper shapes
                            if "content" in res and isinstance(res["content"], list):
                                for item in res["content"]:
                                    if isinstance(item, dict) and "text" in item:
                                        return str(item["text"]).strip()

                # fallback: try top-level text
                for key in ("output", "text", "content"):
                    if key in data and isinstance(data[key], str):
                        return data[key].strip()

            # If nothing found, return raw text
            return r.text.strip()
        except Exception:
            pass

        # CLI fallback
        try:
            if shutil.which("ollama"):
                proc = subprocess.run(
                    ["ollama", "run", self.model_name, prompt], capture_output=True, text=True, timeout=60)
                if proc.returncode == 0:
                    out = proc.stdout.strip()
                    if out:
                        return out
                # Try stderr as last resort
                if proc.stderr:
                    return proc.stderr.strip()
        except Exception:
            pass

        raise RuntimeError("Unable to call local Ollama model via HTTP or CLI")

    def _heuristic_context(self, text: str) -> str:
        """Build a short context summary with heuristic signals for RAG prompt."""
        words = len(text.split())
        paragraphs = max(1, text.count("\n\n") + 1)
        has_date = any(token in text for token in (
            "Published", "published", "\u00A9", "©", "20", "19"))
        has_byline = "By " in text or "by " in text
        return f"Words: {words}; Paragraphs: {paragraphs}; HasDate: {has_date}; HasByline: {has_byline}."

    def is_article(self, text: str) -> bool:
        """RAG-style article classifier.

        Builds a short heuristic context and asks the model to classify. Falls back
        to simple heuristics if the model call fails.
        """
        if not text or not text.strip():
            return False

        heur = self._heuristic_context(text)
        prompt = ARTICLE_DETECTION_PROMPT.format(text=text[:2000], context=heur)
        answer = self._create_completion(prompt, max_tokens=8, temperature=0.0)
        if not answer:
            # Fallback heuristic: long text with multiple paragraphs -> article
            words = len(text.split())
            paragraphs = text.count("\n\n") + 1
            return words >= 200 or paragraphs >= 2

        return answer.strip().lower().startswith("y")
