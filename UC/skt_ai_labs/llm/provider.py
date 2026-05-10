"""
SKT-AI-LABS LLM Provider
Unified interface for multiple LLM backends
"""

import os
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass

import structlog

logger = structlog.get_logger("skt_ai_labs.llm")


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class SKTLLMProvider:
    """
    Unified LLM provider supporting:
    - Google Gemini
    - OpenAI GPT
    - Groq (Llama)
    - Anthropic Claude
    - Local models (Ollama)

    Auto-detects model type from model string.
    """

    def __init__(self, model: str = "gemini-2.5-pro", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self._logger = logger

        # Detect provider from model name
        if "gemini" in model.lower() or "google" in model.lower():
            self.provider = "google"
            self._client = self._init_google()
        elif "gpt" in model.lower() or "openai" in model.lower():
            self.provider = "openai"
            self._client = self._init_openai()
        elif "llama" in model.lower() or "mixtral" in model.lower() or "groq" in model.lower():
            self.provider = "groq"
            self._client = self._init_groq()
        elif "claude" in model.lower():
            self.provider = "anthropic"
            self._client = self._init_anthropic()
        else:
            self.provider = "ollama"
            self._client = self._init_ollama()

    def _init_google(self):
        try:
            import google.generativeai as genai
            key = self.api_key or os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=key)
            return genai
        except ImportError:
            self._logger.error("google_generativeai not installed")
            return None

    def _init_openai(self):
        try:
            from openai import AsyncOpenAI
            key = self.api_key or os.getenv("OPENAI_API_KEY")
            return AsyncOpenAI(api_key=key)
        except ImportError:
            self._logger.error("openai not installed")
            return None

    def _init_groq(self):
        try:
            from groq import AsyncGroq
            key = self.api_key or os.getenv("GROQ_API_KEY")
            return AsyncGroq(api_key=key)
        except ImportError:
            self._logger.error("groq not installed")
            return None

    def _init_anthropic(self):
        try:
            from anthropic import AsyncAnthropic
            key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            return AsyncAnthropic(api_key=key)
        except ImportError:
            self._logger.error("anthropic not installed")
            return None

    def _init_ollama(self):
        try:
            import ollama
            return ollama
        except ImportError:
            self._logger.error("ollama not installed")
            return None

    async def generate(self, 
                       prompt: str, 
                       temperature: float = 0.7,
                       max_tokens: int = 2048,
                       system_prompt: Optional[str] = None) -> str:
        """Generate text completion"""

        if self.provider == "google":
            return await self._generate_google(prompt, temperature, max_tokens, system_prompt)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, temperature, max_tokens, system_prompt)
        elif self.provider == "groq":
            return await self._generate_groq(prompt, temperature, max_tokens, system_prompt)
        elif self.provider == "anthropic":
            return await self._generate_anthropic(prompt, temperature, max_tokens, system_prompt)
        else:
            return await self._generate_ollama(prompt, temperature, max_tokens)

    async def _generate_google(self, prompt, temperature, max_tokens, system_prompt):
        model = self._client.GenerativeModel(self.model)

        content = prompt
        if system_prompt:
            content = f"{system_prompt}\n\n{prompt}"

        response = await model.generate_content_async(
            content,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )
        return response.text

    async def _generate_openai(self, prompt, temperature, max_tokens, system_prompt):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def _generate_groq(self, prompt, temperature, max_tokens, system_prompt):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def _generate_anthropic(self, prompt, temperature, max_tokens, system_prompt):
        messages = [{"role": "user", "content": prompt}]

        response = await self._client.messages.create(
            model=self.model,
            system=system_prompt or "",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content[0].text

    async def _generate_ollama(self, prompt, temperature, max_tokens):
        response = self._client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return response["message"]["content"]

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream tokens (if supported by provider)"""
        # Implementation depends on provider
        # For now, yield full response
        response = await self.generate(prompt, **kwargs)
        for chunk in response.split():
            yield chunk + " "
