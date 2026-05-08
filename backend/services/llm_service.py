"""LLM 调用服务。

策略：
- 优先级遍历 settings.default_provider_priority，挑选首个已配置 API Key 的 provider；
- 复用 mingli_bench.utils.config.load_config 解析 .env，避免重复读取；
- 调用通过 OpenAI 兼容 SDK；DeepSeek / OpenRouter / OpenAI 均使用 OpenAI 客户端，
  Anthropic 与 Google 在本期暂用 OpenAI 兼容兜底（如不可用则继续向下挑选）。
- 永不返回 / 永不日志打印 API Key 原文。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from mingli_bench.utils.config import load_config

from ..core.settings import settings
from .prompt_service import append_disclaimer, get_system_prompt

logger = logging.getLogger(__name__)


_PLACEHOLDER_HINTS = ("your_", "sk-or-...", "sk-...", "sk-ant-...", "ep-...", "<")


def _is_placeholder(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    sl = value.strip().lower()
    return any(h in sl for h in _PLACEHOLDER_HINTS)


@dataclass(frozen=True)
class LLMSelection:
    provider: str
    model: str
    base_url: Optional[str]
    has_key: bool


# 主对话默认模型能力优先，小任务则走轻量模型节省费用 / 提高响应速度。
_LIGHT_MODELS = {
    "deepseek":   "deepseek-v4-flash",
    "openrouter": "deepseek/deepseek-chat",
    "openai":     "gpt-4o-mini",
    "anthropic":  "claude-3-5-haiku",
    "google":     "gemini-1.5-flash",
}

# 不支持 temperature 调节的推理型模型名片段（调用时不传 temperature）
_REASONER_MODEL_HINTS = ("reasoner", "-r1", "o1", "o3")


def _is_reasoner(model_name: str | None) -> bool:
    if not model_name:
        return False
    name = model_name.lower()
    return any(h in name for h in _REASONER_MODEL_HINTS)


def _select_provider() -> Optional[LLMSelection]:
    cfg = load_config()
    for provider in settings.default_provider_priority:
        pcfg = cfg.get(provider) or {}
        api_key = pcfg.get("api_key")
        if _is_placeholder(api_key):
            continue
        model = settings.default_models.get(provider)
        return LLMSelection(
            provider=provider,
            model=model,
            base_url=pcfg.get("base_url"),
            has_key=True,
        )
    return None


def _light_model_for(provider: str, fallback: str) -> str:
    return _LIGHT_MODELS.get(provider) or fallback


def get_active_provider_info() -> Dict[str, Any]:
    """暴露给前端的 LLM 状态摘要（不含密钥）。"""
    sel = _select_provider()
    if not sel:
        return {"available": False, "provider": None, "model": None}
    return {"available": True, "provider": sel.provider, "model": sel.model}


def chat_complete(
    *,
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.4,
) -> Dict[str, Any]:
    """发起 LLM 调用。

    返回 {"ok": bool, "content": str, "provider": str, "model": str, "error": str|None}
    """
    sel = _select_provider()
    if not sel:
        return {
            "ok": False,
            "content": "",
            "provider": None,
            "model": None,
            "error": "no_llm_provider_configured",
        }

    sys_prompt = system_prompt or get_system_prompt()
    full_messages = [{"role": "system", "content": sys_prompt}] + list(messages)

    try:
        from openai import OpenAI

        api_key = (load_config().get(sel.provider) or {}).get("api_key")
        client = OpenAI(api_key=api_key, base_url=sel.base_url, timeout=240, max_retries=2)
        kwargs: Dict[str, Any] = {
            "model": sel.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
        }
        if not _is_reasoner(sel.model):
            kwargs["temperature"] = temperature
        resp = client.chat.completions.create(**kwargs)
        content = (resp.choices[0].message.content or "").strip()
        content = append_disclaimer(content)
        return {
            "ok": True,
            "content": content,
            "provider": sel.provider,
            "model": sel.model,
            "error": None,
        }
    except Exception as e:  # 不打印 API key
        logger.exception("llm_call_failed provider=%s model=%s", sel.provider, sel.model)
        return {
            "ok": False,
            "content": "",
            "provider": sel.provider,
            "model": sel.model,
            "error": f"{type(e).__name__}",
        }


def chat_complete_stream(
    *,
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.4,
) -> Generator[Dict[str, Any], None, None]:
    """流式 LLM 调用。

    生成事件序列：
        {"event": "meta",  "provider": ..., "model": ...}
        {"event": "delta", "content": "..."}      # 多次
        {"event": "done"}                           # 正常结束
    或：
        {"event": "error", "error": "<TypeName>"}

    调用方应在收到 done/error 后停止迭代。
    """
    sel = _select_provider()
    if not sel:
        yield {"event": "error", "error": "no_llm_provider_configured"}
        return

    sys_prompt = system_prompt or get_system_prompt()
    full_messages = [{"role": "system", "content": sys_prompt}] + list(messages)

    yield {"event": "meta", "provider": sel.provider, "model": sel.model}

    try:
        from openai import OpenAI

        api_key = (load_config().get(sel.provider) or {}).get("api_key")
        client = OpenAI(api_key=api_key, base_url=sel.base_url, timeout=240, max_retries=2)
        stream_kwargs: Dict[str, Any] = {
            "model": sel.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if not _is_reasoner(sel.model):
            stream_kwargs["temperature"] = temperature
        stream = client.chat.completions.create(**stream_kwargs)
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
            except Exception:
                continue
            # 忽略 reasoning_content（推理过程），只输出最终 content
            content = getattr(delta, "content", None)
            if content:
                yield {"event": "delta", "content": content}
        yield {"event": "done"}
    except Exception as e:
        logger.exception("llm_stream_failed provider=%s model=%s", sel.provider, sel.model)
        yield {"event": "error", "error": type(e).__name__}


# ------------------------- 会话标题总结 -------------------------

_TITLE_SYSTEM = (
    "你是一名编辑助手。请把用户对话总结成一个简短中文标题，要求："
    "8 至 16 个字、不加引号、不加句号、不出现「标题」二字、突出核心议题。"
    "只输出标题本身，不要任何前缀。"
)


def summarize_session_title(history: List[Dict[str, str]]) -> Optional[str]:
    """让 LLM 生成会话标题。小任务强制走轻量模型，避免使用 reasoner 口重金。"""
    sel = _select_provider()
    if not sel:
        return None

    # 小任务走轻量模型（仅同 provider 下替换模型名）
    light_model = _light_model_for(sel.provider, sel.model)

    sample = history[:6]
    user_block = "\n".join(
        f"[{m.get('role')}] {m.get('content', '').strip()[:200]}" for m in sample
    )

    try:
        from openai import OpenAI

        api_key = (load_config().get(sel.provider) or {}).get("api_key")
        client = OpenAI(api_key=api_key, base_url=sel.base_url)
        resp = client.chat.completions.create(
            model=light_model,
            messages=[
                {"role": "system", "content": _TITLE_SYSTEM},
                {"role": "user", "content": "请基于下列对话生成标题：\n" + user_block},
            ],
            max_tokens=40,
            temperature=0.2,
        )
        title = (resp.choices[0].message.content or "").strip()
        # 清理常见包裹符号
        for ch in ['"', "'", "「", "」", "“", "”", "《", "》"]:
            title = title.replace(ch, "")
        title = title.strip().split("\n")[0]
        return title[:32] or None
    except Exception:
        logger.exception("summarize_session_title_failed provider=%s", sel.provider)
        return None
