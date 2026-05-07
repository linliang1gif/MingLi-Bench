"""SSE 流式对话冒烟脚本。"""

from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"


def stream_chat(subject_id: int, message: str, session_id: int | None = None) -> None:
    body = json.dumps(
        {"subject_id": subject_id, "message": message, "session_id": session_id}
    ).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/api/chat/stream",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )

    start = time.time()
    first_delta_at: float | None = None
    full_text = ""
    print(f"--- streaming chat (subject={subject_id}, msg={message!r}) ---", flush=True)
    with urllib.request.urlopen(req, timeout=240) as resp:
        buf = ""
        for chunk in iter(lambda: resp.read1(1024), b""):
            buf += chunk.decode("utf-8", errors="replace")
            while "\n\n" in buf:
                evt_blk, buf = buf.split("\n\n", 1)
                event = "message"
                data_lines = []
                for line in evt_blk.splitlines():
                    if line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                try:
                    data = json.loads("".join(data_lines)) if data_lines else None
                except Exception:
                    data = None
                if event == "delta":
                    if first_delta_at is None:
                        first_delta_at = time.time() - start
                        print(f"[{first_delta_at:.2f}s] first delta", flush=True)
                    piece = (data or {}).get("content", "")
                    full_text += piece
                    sys.stdout.write(piece)
                    sys.stdout.flush()
                elif event == "meta":
                    print(f"\n[meta] {data}", flush=True)
                elif event == "done":
                    elapsed = time.time() - start
                    print(f"\n[done] in {elapsed:.2f}s, msg_id={(data or {}).get('message_id')}, len={len(full_text)}", flush=True)
                elif event == "title":
                    print(f"\n[title] -> {data}", flush=True)
                elif event == "error":
                    print(f"\n[error] {data}", flush=True)


if __name__ == "__main__":
    sid = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    msg = sys.argv[2] if len(sys.argv) > 2 else "我适合换工作吗？最近犹豫不决"
    stream_chat(sid, msg)
