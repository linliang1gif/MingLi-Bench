"""明理 AI · 后端冒烟脚本

校验：
1. /api/health 返回 200 且 db_ready=true
2. POST /api/subjects 能创建命主
3. GET /api/subjects 能拉到列表
4. POST /api/subjects/{id}/chart 能生成命盘
5. POST /api/chat 能持久化用户消息（即使 LLM 不可用，也不应崩）
6. POST /api/reports/generate 能落库（含降级文案）
7. /api/history 能聚合
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def _req(method: str, path: str, body: dict | None = None, timeout: int = 90):
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "null")


def _check(name: str, ok: bool, info: str = "") -> None:
    print(("[ OK ]" if ok else "[FAIL]"), name, "-", info)
    if not ok:
        global FAILED
        FAILED += 1


FAILED = 0


def main() -> int:
    global FAILED

    # 1. health
    code, body = _req("GET", "/api/health")
    _check("health 200", code == 200, str(body))
    _check("db_ready", bool(body and body.get("db_ready")), "")
    llm_available = bool(body and body.get("llm", {}).get("available"))

    # 2. create subject
    code, body = _req("POST", "/api/subjects", {
        "nickname": "测试命主A",
        "gender": "男",
        "birth_date": "1990-05-12",
        "birth_time": "14:30",
        "birth_place": "北京",
        "calendar_type": "solar",
        "focus_topics": ["财运", "事业"],
    })
    _check("create subject 201", code == 201, str(body)[:140])
    sid = body and body.get("id")

    # 3. list subjects
    code, body = _req("GET", "/api/subjects")
    _check("list subjects 200", code == 200 and isinstance(body, list) and len(body) >= 1, "")

    # 4. chart generate
    if sid:
        code, body = _req("POST", f"/api/subjects/{sid}/chart")
        _check("chart create 200", code == 200, "")
        _check("chart pillars present", bool(body and body.get("pillars", {}).get("year", {}).get("stem")),
               json.dumps(body and body.get("pillars"), ensure_ascii=False)[:160])

    # 5. chat
    if sid:
        code, body = _req("POST", "/api/chat", {
            "subject_id": sid,
            "message": "今年财运如何？",
        }, timeout=180)
        _check("chat 200", code == 200, "")
        if body:
            disclaimer_ok = "免责声明" in (body.get("reply") or "") or "仅供参考" in (body.get("reply") or "")
            _check("chat reply has disclaimer", disclaimer_ok, "(LLM available: %s)" % llm_available)
            _check("chat session_id present", bool(body.get("session_id")), "")

    # 6. report generate
    if sid:
        code, body = _req("POST", "/api/reports/generate", {
            "subject_id": sid,
            "report_type": "general",
        }, timeout=180)
        _check("report generate 200", code == 200, "")
        _check("report has content", bool(body and body.get("content")), "")

    # 7. history
    code, body = _req("GET", "/api/history")
    _check("history 200", code == 200 and isinstance(body, list), "")

    print()
    print("FAILED:", FAILED)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
