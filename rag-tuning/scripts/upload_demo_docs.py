"""创建调优知识库并上传三篇正式 demo 正文，轮询到 completed。"""

from __future__ import annotations

import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8001"
ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "demo-materials"
FILES = [
    DEMO / "测试文档1-公司考勤制度.md",
    DEMO / "测试文档2-差旅报销标准.md",
    DEMO / "测试文档3-RAG系统架构设计.md",
]


def req_json(method: str, path: str, body=None, token: str | None = None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}


def upload_file(kb_id: str, file_path: Path, token: str):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    filename = file_path.name
    content = file_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/markdown\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    request = urllib.request.Request(
        f"{BASE}/api/knowledge-bases/{kb_id}/documents/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    for f in FILES:
        if not f.exists():
            raise SystemExit(f"缺少文件: {f}")

    st, login = req_json("POST", "/api/auth/login/json", {"username": "admin", "password": "admin123"})
    assert st == 200 and login.get("code") == 0, login
    token = login["data"]["access_token"]
    print("[ok] login")

    st, created = req_json(
        "POST",
        "/api/knowledge-bases",
        {"name": "RAG调优-尚欢欢", "description": "正式三篇demo正文，用于评测基线"},
        token=token,
    )
    print("[create_kb]", st, created)
    if created.get("code") != 0:
        raise SystemExit("创建知识库失败")
    data = created.get("data") or {}
    kb_id = data.get("id") or data.get("kb_id")
    if not kb_id:
        # 有的接口只回 success，再列表取最新
        st, kbs = req_json("GET", "/api/knowledge-bases", token=token)
        items = kbs.get("data") if isinstance(kbs.get("data"), list) else (kbs.get("data") or {}).get("items") or []
        hit = next((x for x in items if x.get("name") == "RAG调优-尚欢欢"), None)
        kb_id = hit["id"] if hit else None
    print("[kb_id]", kb_id)
    if not kb_id:
        raise SystemExit("拿不到 kb_id")

    docs = []
    for f in FILES:
        print(f"[upload] {f.name} ...")
        try:
            body = upload_file(kb_id, f, token)
        except urllib.error.HTTPError as e:
            print("upload http error", e.code, e.read().decode("utf-8", errors="replace"))
            raise
        print(" ", body)
        if body.get("code") != 0:
            raise SystemExit(f"上传失败: {f.name}")
        doc = body.get("data") or {}
        docs.append({"id": doc.get("id"), "filename": f.name})

    print("[wait] 等待 completed ...")
    attendance_doc = None
    for _ in range(60):
        st, listed = req_json("GET", f"/api/knowledge-bases/{kb_id}/documents", token=token)
        items = listed.get("data") if isinstance(listed.get("data"), list) else (listed.get("data") or {}).get("items") or []
        statuses = [(d.get("filename"), d.get("status"), d.get("id"), d.get("chunk_count")) for d in items]
        print(" status:", statuses)
        if items and all(d.get("status") == "completed" for d in items):
            for d in items:
                name = d.get("filename") or ""
                if "考勤" in name:
                    attendance_doc = d.get("id")
            if not attendance_doc and items:
                attendance_doc = items[0].get("id")
            print("==== READY ====")
            print(f"kb_id={kb_id}")
            print(f"attendance_doc_id={attendance_doc}")
            print("下一步命令:")
            print(
                f"python rag-tuning/scripts/run_baseline.py --kb-id {kb_id} --doc-id {attendance_doc}"
            )
            return
        if any(d.get("status") == "failed" for d in items):
            print("有文档 failed，请检查 Chroma / Embedding Key")
            return
        time.sleep(3)

    print("超时仍未全部 completed")


if __name__ == "__main__":
    main()
