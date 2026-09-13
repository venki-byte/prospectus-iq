"""
Multi-Provider LLM Fallback Router for ProspectusIQ.
Cascades dynamically: Google Gemini 1.5 Flash -> xAI Grok -> OpenRouter.
Enforces JSON responses, strict stripping of markdown fences, and 25s timeout guarantees.
"""
import concurrent.futures
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from config import (
    GEMINI_API_KEY,
    GROK_API_KEY,
    GROK_BASE_URL,
    GROK_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    get_secret,
)
from core.forensic_engine import ForensicEngine

logger = logging.getLogger("prospectus_iq.llm_router")


class LLMRoutingException(Exception):
    """Raised when all configured LLM providers fail or are unavailable."""

    def __init__(self, provider_errors: Dict[str, str]):
        self.provider_errors = provider_errors
        err_msg = "All LLM providers failed in fallback chain:\n" + "\n".join(
            f"  - {provider}: {err}" for provider, err in provider_errors.items()
        )
        super().__init__(err_msg)


class LLMRouter:
    """Manages the failover cascade between Gemini, Grok, and OpenRouter."""

    @classmethod
    def call_gemini(cls, system_prompt: str, user_prompt: str, timeout: float = 25.0) -> Tuple[Dict[str, Any], str]:
        """
        Primary Provider: Google Gemini lowest model (gemini-flash-lite-latest / gemini-2.5-flash-lite).
        Enforces application/json MIME type and strict 25s timeout.
        """
        from dotenv import load_dotenv
        load_dotenv(override=True)
        api_key = get_secret("GEMINI_API_KEY", "").strip()
        preferred_model = get_secret("GEMINI_MODEL", "gemini-flash-lite-latest").strip()

        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured in environment or Streamlit secrets.")

        import google.generativeai as genai
        genai.configure(api_key=api_key)

        candidate_models = [
            preferred_model,
            "gemini-flash-lite-latest",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
            "gemini-2.5-flash",
        ]
        # Deduplicate while preserving order
        unique_models = []
        for m in candidate_models:
            if m and m not in unique_models:
                unique_models.append(m)

        last_error = None
        for model_name in unique_models:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.2,
                    },
                    system_instruction=system_prompt,
                )

                def _invoke():
                    response = model.generate_content(user_prompt)
                    if not response or not response.text:
                        raise ValueError(f"Empty response received from Gemini model {model_name}.")
                    return response.text

                # Enforce timeout via ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_invoke)
                    raw_text = future.result(timeout=timeout)

                parsed = ForensicEngine.parse_and_validate_audit(raw_text)
                return parsed, model_name
            except Exception as e:
                logger.warning(f"Gemini model {model_name} failed: {e}. Trying next candidate...")
                last_error = e

        raise last_error or RuntimeError("All candidate Gemini models failed.")

    @classmethod
    def call_grok(cls, system_prompt: str, user_prompt: str, timeout: float = 25.0) -> Dict[str, Any]:
        """
        First Fallback: xAI Grok (via OpenAI SDK client).
        """
        api_key = get_secret("GROK_API_KEY", "").strip()
        base_url = get_secret("GROK_BASE_URL", GROK_BASE_URL).strip()
        model = get_secret("GROK_MODEL", GROK_MODEL).strip()
        if not api_key:
            raise ValueError("GROK_API_KEY not configured in environment or Streamlit secrets.")

        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from Grok endpoint.")

        return ForensicEngine.parse_and_validate_audit(content)

    @classmethod
    def call_openrouter(cls, system_prompt: str, user_prompt: str, timeout: float = 25.0) -> Dict[str, Any]:
        """
        Second Fallback: OpenRouter (via OpenAI SDK client).
        """
        api_key = get_secret("OPENROUTER_API_KEY", "").strip()
        base_url = get_secret("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL).strip()
        model = get_secret("OPENROUTER_MODEL", OPENROUTER_MODEL).strip()
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not configured in environment or Streamlit secrets.")

        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenRouter endpoint.")

        return ForensicEngine.parse_and_validate_audit(content)

    @classmethod
    def generate_json(
        cls,
        system_prompt: str,
        user_prompt: str,
        symbol_hint: Optional[str] = None,
        allow_benchmark_fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Unified interface providing failover cascade:
        Gemini 1.5 Flash -> xAI Grok -> OpenRouter -> Benchmark Fallback / Explicit Exception.
        """
        provider_errors: Dict[str, str] = {}

        # 1. Primary: Google Gemini
        try:
            logger.info("Routing prompt to Primary Provider: Gemini lowest model...")
            result, chosen_model = cls.call_gemini(system_prompt, user_prompt)
            result["_provider_used"] = f"Google Gemini ({chosen_model})"
            return result
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Gemini provider failed: {err_str}. Cascading to First Fallback (Grok)...")
            provider_errors["Google Gemini"] = err_str

        # 2. First Fallback: xAI Grok
        try:
            logger.info("Routing prompt to First Fallback: xAI Grok...")
            result = cls.call_grok(system_prompt, user_prompt)
            result["_provider_used"] = f"xAI Grok ({GROK_MODEL})"
            return result
        except Exception as e:
            err_str = str(e)
            logger.warning(f"xAI Grok provider failed: {err_str}. Cascading to Second Fallback (OpenRouter)...")
            provider_errors["xAI Grok"] = err_str

        # 3. Second Fallback: OpenRouter
        try:
            logger.info("Routing prompt to Second Fallback: OpenRouter...")
            result = cls.call_openrouter(system_prompt, user_prompt)
            result["_provider_used"] = f"OpenRouter ({OPENROUTER_MODEL})"
            return result
        except Exception as e:
            err_str = str(e)
            logger.warning(f"OpenRouter provider failed: {err_str}.")
            provider_errors["OpenRouter"] = err_str

        # 4. Infallible Demo Fallback for Benchmark Registry (if keys unconfigured or blocked)
        if allow_benchmark_fallback and symbol_hint:
            sym_clean = symbol_hint.upper()
            if any(b in sym_clean for b in ["SWIGGY", "NSE", "AFCONS"]):
                logger.info(f"Engaging pre-computed forensic benchmark for {sym_clean} due to remote LLM exhaustion.")
                bench_result = ForensicEngine.get_benchmark_audit(sym_clean)
                bench_result["_provider_used"] = "Offline Institutional Benchmark (All LLM keys exhausted/offline)"
                bench_result["_fallback_notice"] = (
                    "Audit generated via pre-extracted forensic benchmark model because remote API keys were unconfigured or quota-exhausted. "
                    f"Provider logs: {provider_errors}"
                )
                return bench_result

        # 5. Final Exception Handling: All failed
        raise LLMRoutingException(provider_errors)
