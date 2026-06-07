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
import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
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

_VISION_MODEL_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "openrouter": "openai/gpt-4o-mini",
    "qiniu": "qwen-vl-max-2025-01-25",
}

_IMAGE_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
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


def _select_vision_provider() -> Optional[LLMSelection]:
    """Select an OpenAI-compatible vision model when configured."""
    cfg = load_config()
    provider = (os.getenv("VISION_PROVIDER") or "").strip().lower()
    if provider:
        pcfg = cfg.get(provider) or {}
        api_key = os.getenv("VISION_API_KEY") or pcfg.get("api_key")
        if _is_placeholder(api_key):
            return None
        return LLMSelection(
            provider=provider,
            model=os.getenv("VISION_MODEL") or _VISION_MODEL_DEFAULTS.get(provider) or settings.default_models.get(provider),
            base_url=os.getenv("VISION_BASE_URL") or pcfg.get("base_url"),
            has_key=True,
        )

    # The current DeepSeek chat model is text-only in this project, so do not auto-select it for images.
    for candidate in ("openai", "openrouter"):
        pcfg = cfg.get(candidate) or {}
        api_key = pcfg.get("api_key")
        if _is_placeholder(api_key):
            continue
        return LLMSelection(
            provider=candidate,
            model=_VISION_MODEL_DEFAULTS[candidate],
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


def analyze_image_objects(*, image_path: str, room_type: str) -> Dict[str, Any]:
    """Analyze visible objects in an uploaded image via a configured vision model.

    If no compatible vision model is configured, callers receive a clean fallback signal and can
    return editable mock results.
    """
    sel = _select_vision_provider()
    if not sel:
        return {
            "ok": False,
            "analysis": None,
            "provider": None,
            "model": None,
            "error": "vision_model_not_configured",
            "image_path": image_path,
            "room_type": room_type,
        }

    path = Path(image_path)
    if not path.exists():
        return {
            "ok": False,
            "analysis": None,
            "provider": sel.provider,
            "model": sel.model,
            "error": "image_file_not_found",
            "image_path": image_path,
            "room_type": room_type,
        }
    mime_type = _IMAGE_MIME_BY_EXT.get(path.suffix.lower())
    if not mime_type:
        return {
            "ok": False,
            "analysis": None,
            "provider": sel.provider,
            "model": sel.model,
            "error": "unsupported_image_type",
            "image_path": image_path,
            "room_type": room_type,
        }

    try:
        from openai import OpenAI

        api_key = os.getenv("VISION_API_KEY") or (load_config().get(sel.provider) or {}).get("api_key")
        image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        data_url = f"data:{mime_type};base64,{image_b64}"
        system_prompt = (
            "你是图片中可见对象的结构化识别助手。只描述照片中可见的客观对象和大致位置，"
            "不要输出医疗、法律、投资结论，不要恐吓或强断。"
        )
        if room_type == "heritage_risk":
            system_prompt += (
                "当前场景是文保风险记录。严禁输出古墓定位、古墓概率、墓道/墓室/入口推测、"
                "寻找路线、挖掘建议或探测建议；只能记录山势地貌、异常地貌、人工痕迹、"
                "近期扰动和现场保护线索。不确定信息必须标注需要专业人员现场核实。"
            )
        user_prompt = (
            "请识别图片中的可见对象，返回严格 JSON，不要 Markdown。"
            "objects 只返回照片中清楚可见的客观对象，不要求凑够数量；宁可少返回，也不要把看不清的建筑、道路、人工土堆等硬猜成对象。"
            "外局山水田野照片中，前景绿色地块应优先识别为 field、farmland、grassland 或 open_space；只有明确看到水面、河流、湖泊时才返回 water。"
            "只有明确看到建筑轮廓、墙体或屋顶时才返回 building；只有明确看到路面或道路边界时才返回 road/path。"
            "不确定的内容写入 possible_issues，请用户人工核对。"
            "如果当前场景不是 heritage_risk，不要返回 artificial_mound、stone_object、inscription、surface_artifact、recent_disturbance 这类文保风险字段。"
            "不要输出笼统的画面概括，重点返回对象、位置、置信度和需要人工核对的事项。格式："
            '{"room_type":"场景类型","objects":[{"name":"bed|door|window|mirror|beam|mountain|slope|field|farmland|grassland|open_space|water|road|path|building|tree|pole|artificial_mound|stone_object|inscription|surface_artifact|recent_disturbance|target",'
            '"label":"中文标签","position":"front|back-wall|center|center-left|center-right|front-left|front-right|side|background|unknown","confidence":0.0}],'
            '"possible_issues":[],"need_user_confirm":true}。'
            f"当前场景类型：{room_type}。"
        )

        client = OpenAI(api_key=api_key, base_url=sel.base_url, timeout=120, max_retries=1)
        resp = client.chat.completions.create(
            model=sel.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                    ],
                },
            ],
            max_tokens=1200,
            temperature=0.1,
        )
        content = (resp.choices[0].message.content or "").strip()
        analysis = _extract_json_object(content)
        if not isinstance(analysis, dict):
            return {
                "ok": False,
                "analysis": None,
                "provider": sel.provider,
                "model": sel.model,
                "error": "vision_response_parse_failed",
                "image_path": image_path,
                "room_type": room_type,
            }
        analysis.setdefault("room_type", room_type)
        analysis.setdefault("scene_type", room_type)
        analysis.setdefault("objects", [])
        analysis.setdefault("possible_issues", [])
        analysis.setdefault("need_user_confirm", True)
        analysis["vision_raw_text"] = content[:2000]
        return {
            "ok": True,
            "analysis": analysis,
            "provider": sel.provider,
            "model": sel.model,
            "error": None,
            "image_path": image_path,
            "room_type": room_type,
        }
    except Exception as e:
        logger.exception("vision_call_failed provider=%s model=%s", sel.provider, sel.model)
        return {
            "ok": False,
            "analysis": None,
            "provider": sel.provider,
            "model": sel.model,
            "error": type(e).__name__,
            "image_path": image_path,
            "room_type": room_type,
        }


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    source = (text or "").strip()
    if source.startswith("```"):
        source = source.strip("`").strip()
        if source.lower().startswith("json"):
            source = source[4:].strip()
    try:
        parsed = json.loads(source)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    start = source.find("{")
    end = source.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(source[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


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
