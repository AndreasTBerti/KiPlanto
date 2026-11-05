"""Cliente do OpenRouter com duas travas de gasto.

- Preço: cada pedido leva `provider.max_price`, e o próprio OpenRouter recusa o que passar do teto.
- Orçamento: somado o custo informado nas respostas, ao chegar em OPENROUTER_MAX_SPEND_USD a IA se
  desliga até o servidor reiniciar. A rota que usa este cliente não tem autenticação.

Sem chave, ou sem orçamento, tudo que depende daqui fica desligado e o sistema continua com as regras
locais. Para um limite que valha entre reinícios, defina também um limite na chave, no painel do OpenRouter.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Escolhidos pela comparação do README: o melhor custo-benefício e, se ele falhar, o mais rápido.
DEFAULT_MODELS = ("inception/mercury-2.5", "google/gemma-4-26b-a4b-it")
DEFAULT_TIMEOUT_SECONDS = 45.0
# Em US$ por milhão de tokens.
DEFAULT_MAX_INPUT_PRICE = 0.20
DEFAULT_MAX_OUTPUT_PRICE = 0.50
DEFAULT_MAX_SPEND_USD = 1.0
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")

_spent_usd = 0.0
_spent_lock = threading.Lock()


class LLMUnavailable(Exception):
    """Nenhum modelo respondeu com um JSON válido dentro do prazo e das travas de gasto."""


@dataclass(frozen=True)
class LLMResponse:
    model: str
    data: dict[str, Any]


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


def configured_models() -> list[str]:
    raw = os.getenv("OPENROUTER_MODELS", "")
    return [model.strip() for model in raw.split(",") if model.strip()] or list(DEFAULT_MODELS)


def _api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def timeout_seconds() -> float:
    return _env_float("OPENROUTER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)


def max_spend_usd() -> float:
    return _env_float("OPENROUTER_MAX_SPEND_USD", DEFAULT_MAX_SPEND_USD)


def spent_usd() -> float:
    with _spent_lock:
        return _spent_usd


def reset_spend() -> None:
    global _spent_usd
    with _spent_lock:
        _spent_usd = 0.0


def _add_spend(cost: Any) -> None:
    global _spent_usd
    if isinstance(cost, (int, float)) and cost > 0:
        with _spent_lock:
            _spent_usd += cost


def is_enabled() -> bool:
    return bool(_api_key()) and spent_usd() < max_spend_usd()


def _price_cap() -> dict[str, float]:
    return {
        "prompt": _env_float("OPENROUTER_MAX_INPUT_PRICE", DEFAULT_MAX_INPUT_PRICE),
        "completion": _env_float("OPENROUTER_MAX_OUTPUT_PRICE", DEFAULT_MAX_OUTPUT_PRICE),
    }


def _parse_json(content: Any) -> Optional[dict[str, Any]]:
    if not isinstance(content, str):
        return None
    try:
        data = json.loads(_FENCE.sub("", content.strip()))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _ask(model: str, payload: dict[str, Any], timeout: float) -> Optional[dict[str, Any]]:
    """O JSON da resposta, ou None se este modelo falhou. A chave nunca entra nos logs."""
    try:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {_api_key()}", "X-Title": "KiPlanto"},
            json={**payload, "model": model},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning("OpenRouter: %s falhou (%s)", model, type(exc).__name__)
        return None
    if response.status_code != 200:
        logger.warning("OpenRouter: %s respondeu HTTP %s", model, response.status_code)
        return None
    try:
        body = response.json()
        choice = body["choices"][0]
        message = choice["message"]
    except (ValueError, KeyError, IndexError, TypeError):
        logger.warning("OpenRouter: %s devolveu uma resposta sem mensagem", model)
        return None
    # Conta antes de validar: resposta ruim também é cobrada.
    _add_spend((body.get("usage") or {}).get("cost"))
    data = _parse_json(message.get("content"))
    if data is None:
        logger.warning("OpenRouter: %s não devolveu JSON válido (fim: %s)", model, choice.get("finish_reason"))
    return data


def chat_json(
    system: str,
    user: str,
    *,
    schema_name: str,
    schema: dict[str, Any],
    max_tokens: int,
    models: Optional[list[str]] = None,
) -> LLMResponse:
    """Tenta os modelos em ordem até um responder. Levanta LLMUnavailable se nenhum conseguir."""
    candidates = models or configured_models()
    if not is_enabled() or not candidates:
        raise LLMUnavailable("OpenRouter desligado: sem chave ou sem orçamento")

    payload = {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        },
        # require_parameters: só provedores que respeitam o formato. max_price: a trava de preço.
        "provider": {"require_parameters": True, "max_price": _price_cap()},
    }
    deadline = time.monotonic() + timeout_seconds()
    for model in candidates:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not is_enabled():
            break
        data = _ask(model, payload, remaining)
        if data is not None:
            return LLMResponse(model=model, data=data)
    raise LLMUnavailable("nenhum modelo respondeu")
