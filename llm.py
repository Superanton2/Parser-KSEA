import os
from openai import OpenAI

# Constants
DEFAULT_BASE_URL = "https://router.huggingface.co/v1"
ARTICLE_DETECTION_PROMPT = (
    "Determine if the following text is an article or not:\n\n{text}\n\n"
    "Answer with 'Yes' for article and 'No' for non-article."
)
SYSTEM_PROMPT = "You are a helpful assistant."


class LLM:
    """A wrapper class for interacting with LLM models via OpenAI-compatible API."""

    def __init__(self, model_name: str, api_key: str | None = None, base_url: str | None = None):
        """
        Initialize the LLM client.

        Args:
            model_name: The name of the model to use.
            api_key: The API key for authentication. Defaults to HF_API_KEY environment variable.
            base_url: The base URL for the API. Defaults to HuggingFace router.
        """
        self.model_name = model_name
        self.client = OpenAI(
            base_url=base_url or DEFAULT_BASE_URL,
            api_key=api_key or os.getenv("HF_API_KEY"),
        )

    def _create_completion(self, prompt: str, max_tokens: int = 10, temperature: float = 0.0) -> str:
        """
        Create a chat completion and return the response content.

        Args:
            prompt: The user prompt to send.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            The content of the model's response.
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    def is_article(self, text: str) -> bool:
        """
        Determine if the given text is an article.

        Args:
            text: The text to analyze.

        Returns:
            True if the text is classified as an article, False otherwise.
        """
        prompt = ARTICLE_DETECTION_PROMPT.format(text=text)
        answer = self._create_completion(prompt)
        return answer.lower() == "yes"
