# -*- coding: utf-8 -*-
"""A+B 联调冒烟：登录 → 建库 → 上传ingest → 命中 → 对话"""
from __future__ import annotations

import json
import os
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:8001")
ROOT = Path(__file__).resolve().parents[1]


def req(method, path, data=None, token=None, form=False, files=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if form:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif files:
        boundary = "----Boundary" + uuid.uuid4().hex
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        filename, content, ctype = files
        parts = [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {ctype}\r\n\r\n".encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
        body = b"".join(parts)
    elif data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"code": e.code, "msg": raw[:300]}


def main():
    demos = list((ROOT / "demo-materials").glob("*.md"))
    if not demos:
        raise SystemExit("找不到 demo md")
    demo = demos[0]
    print("demo =", demo.name)

    print("\n[1] health")
    print(req("GET", "/health"))

    print("\n[2] login admin/admin123")
    login = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"}, form=True)
    print("login code/msg", login.get("code"), login.get("msg"))
    token = (login.get("data") or {}).get("access_token")
    if not token:
        print("全文", login)
        raise SystemExit("登录失败")

    print("\n[3] create kb")
    kb = req(
        "POST",
        "/api/knowledge-bases",
        {"name": f"联调库-{int(time.time())}", "description": "ab-merge", "group_ids": []},
        token=token,
    )
    print(kb)
    kb_id = (kb.get("data") or {}).get("id")
    if not kb_id:
        raise SystemExit("建库失败")

    print("\n[4] upload + ingest")
    up = req(
        "POST",
        f"/api/knowledge-bases/{kb_id}/documents/upload",
        token=token,
        files=(demo.name, demo.read_bytes(), "text/markdown"),
    )
    print("upload", up.get("code"), up.get("msg"), (up.get("data") or {}).get("status"))
    doc_id = (up.get("data") or {}).get("id")
    if not doc_id:
        print(up)
        raise SystemExit("上传失败")

    print("\n[5] wait completed")
    status = "pending"
    for i in range(30):
        time.sleep(2)
        docs = req("GET", f"/api/knowledge-bases/{kb_id}/documents", token=token)
        items = docs.get("data") or []
        cur = next((d for d in items if d.get("id") == doc_id), None)
        status = (cur or {}).get("status")
        print(f"  poll{i+1} status={status} chunks={(cur or {}).get('chunk_count')}")
        if status in ("completed", "failed"):
            break

    print("\n[6] hit test")
    hit = req(
        "POST",
        "/api/rag/test_retrieve",
        {
            "kb_id": kb_id,
            "doc_id": doc_id,
            "search_type": "hybrid",
            "query": "年假怎么申请",
            "top_n": 3,
        },
        token=token,
    )
    print("hit", hit.get("code"), "total", (hit.get("data") or {}).get("total_hits"), hit.get("msg"))

    print("\n[7] bad search_type")
    bad = req(
        "POST",
        "/api/chat/send",
        {"kb_id": kb_id, "query": "test", "search_type": "invalid"},
        token=token,
    )
    print("bad", bad.get("code"), bad.get("msg"))

    print("\n[8] chat send")
    chat = req(
        "POST",
        "/api/chat/send",
        {"kb_id": kb_id, "query": "年假需要提前几天申请？", "search_type": "hybrid"},
        token=token,
    )
    d = chat.get("data") or {}
    print(
        "chat",
        chat.get("code"),
        "query_field",
        d.get("query"),
        "ans_len",
        len(d.get("answer") or ""),
        "refs",
        len(d.get("references") or []),
    )
    if d.get("answer"):
        print("answer:", (d.get("answer") or "")[:160])

    print("\nALL_STEPS_DONE status=", status)
    print("kb_id=", kb_id)
    print("doc_id=", doc_id)


if __name__ == "__main__":
    main()
