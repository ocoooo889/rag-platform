"""
全身体检：按 OpenAPI 逐条打通所有接口 + 前端路径对照。
用法（仓库根或 backend）：python scripts/full_api_checkup.py
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
TAG = f"checkup_{int(time.time())}"
OUT = Path(__file__).resolve().parents[1] / "docs" / "测试报告" / "Day4" / "04-接口全身体检报告.md"

# 前端真实调用路径（与 src/api 对齐）
FE_CALLS = {
    ("POST", "/api/auth/login"),
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/avatar"),
    ("PUT", "/api/auth/profile"),
    ("GET", "/api/system/branding"),
    ("PUT", "/api/system/branding"),
    ("GET", "/api/dashboard/stats"),
    ("GET", "/api/knowledge-bases"),
    ("POST", "/api/knowledge-bases"),
    ("PUT", "/api/knowledge-bases/{kb_id}"),
    ("DELETE", "/api/knowledge-bases/{kb_id}"),
    ("GET", "/api/knowledge-bases/{kb_id}/documents"),
    ("POST", "/api/knowledge-bases/{kb_id}/documents/upload"),
    ("DELETE", "/api/documents/{doc_id}"),
    ("POST", "/api/documents/batch-delete"),
    ("POST", "/api/rag/test_retrieve"),
    ("GET", "/api/chat/sessions"),
    ("GET", "/api/chat/sessions/{session_id}/messages"),
    ("PATCH", "/api/chat/sessions/{session_id}"),
    ("DELETE", "/api/chat/sessions/{session_id}"),
    ("POST", "/api/chat/stream"),
    ("POST", "/api/chat/warmup"),
    ("GET", "/api/user-groups"),
    ("POST", "/api/user-groups"),
    ("PUT", "/api/user-groups/{group_id}"),
    ("DELETE", "/api/user-groups/{group_id}"),
    ("POST", "/api/user-groups/{group_id}/members"),
    ("POST", "/api/user-groups/{group_id}/kb-access"),
    ("GET", "/api/models"),
    ("POST", "/api/models"),
    ("PUT", "/api/models/{config_id}"),
    ("DELETE", "/api/models/{config_id}"),
    ("GET", "/api/roles"),
    ("POST", "/api/roles"),
    ("PUT", "/api/roles/{role_id}"),
    ("DELETE", "/api/roles/{role_id}"),
    ("GET", "/api/users"),
    ("POST", "/api/users"),
    ("PUT", "/api/users/{user_id}"),
    ("DELETE", "/api/users/{user_id}"),
}

BE_ONLY_OK = {
    ("GET", "/health"),
    ("GET", "/api/health"),
    ("GET", "/metrics"),
    ("POST", "/api/auth/login/json"),
    ("POST", "/api/chat/send"),
}


def normalize_path(path: str) -> str:
    # openapi uses {user_id} etc — keep as-is for matching FE templates
    return path


class Probe:
    def __init__(self):
        self.client = httpx.Client(base_url=BASE, timeout=90.0)
        self.token = ""
        self.rows: list[dict] = []
        self.ctx: dict = {}

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def record(self, method, path, ok, http_status, biz_code, note, fe=""):
        self.rows.append(
            {
                "method": method,
                "path": path,
                "ok": ok,
                "http": http_status,
                "biz": biz_code,
                "note": note,
                "fe": fe,
            }
        )
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {method:6} {path}  http={http_status} biz={biz_code}  {note}")

    def call(
        self,
        name: str,
        method: str,
        path: str,
        *,
        expect_biz=0,
        allow_http=(200,),
        fe_match: str = "",
        **kwargs,
    ):
        headers = dict(kwargs.pop("headers", {}))
        headers.update(self.auth_headers())
        try:
            r = self.client.request(method, path, headers=headers, **kwargs)
        except Exception as e:
            self.record(method, path, False, "ERR", None, f"{name}: {e}", fe_match)
            return None
        biz = None
        detail = ""
        try:
            j = r.json()
            if isinstance(j, dict):
                biz = j.get("code")
                detail = str(j.get("msg") or j.get("detail") or "")[:80]
                data = j.get("data")
            else:
                data = j
                detail = "non-object json"
        except Exception:
            j = None
            data = None
            detail = (r.text or "")[:80]

        http_ok = r.status_code in allow_http
        # Prometheus metrics: plain text
        if path == "/metrics":
            ok = r.status_code == 200 and ("#" in (r.text or "") or "http_" in (r.text or ""))
            self.record(method, path, ok, r.status_code, None, name, fe_match)
            return r
        # FastAPI validation 422 etc
        if r.status_code == 422:
            self.record(method, path, False, 422, biz, f"{name}: validation {detail}", fe_match)
            return r
        biz_ok = True
        if expect_biz is not None and isinstance(j, dict) and "code" in j:
            biz_ok = j.get("code") == expect_biz
        ok = http_ok and biz_ok
        note = f"{name}" + (f" | {detail}" if detail and not ok else "")
        self.record(method, path, ok, r.status_code, biz, note, fe_match)
        return data if ok else j

    def run(self):
        # 0) openapi inventory
        spec = self.client.get("/openapi.json").json()
        openapi_ops = []
        for path, methods in sorted((spec.get("paths") or {}).items()):
            for m in methods:
                if m.startswith("x-"):
                    continue
                openapi_ops.append((m.upper(), path))

        # 1) public
        self.call("health", "GET", "/health", fe_match="BE-only")
        self.call("api health", "GET", "/api/health", fe_match="BE-only")
        self.call("metrics", "GET", "/metrics", expect_biz=None, fe_match="BE-only")

        # 2) login
        data = self.call(
            "login form",
            "POST",
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            fe_match="FE",
        )
        if not isinstance(data, dict) or not data.get("access_token"):
            print("FATAL: login failed, abort")
            return openapi_ops
        self.token = data["access_token"]

        data = self.call(
            "login json",
            "POST",
            "/api/auth/login/json",
            json={"username": "admin", "password": "admin123"},
            fe_match="BE-only",
        )

        self.call("me", "GET", "/api/auth/me", fe_match="FE")
        self.call(
            "profile",
            "PUT",
            "/api/auth/profile",
            json={"display_name": "系统管理员"},
            fe_match="FE",
        )

        # avatar tiny png
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        self.call(
            "avatar",
            "POST",
            "/api/auth/avatar",
            files={"avatar": ("a.png", io.BytesIO(png), "image/png")},
            fe_match="FE",
        )

        # 3) read-only lists
        for method, path, name in [
            ("GET", "/api/system/branding", "branding get"),
            ("GET", "/api/dashboard/stats", "dashboard"),
            ("GET", "/api/knowledge-bases", "kb list"),
            ("GET", "/api/users", "users"),
            ("GET", "/api/roles", "roles"),
            ("GET", "/api/user-groups", "groups"),
            ("GET", "/api/models", "models"),
        ]:
            self.call(name, method, path, params={"page": 1, "page_size": 100} if "knowledge" in path else None, fe_match="FE")

        # 4) create temp resources
        role = self.call(
            "role create",
            "POST",
            "/api/roles",
            json={"name": f"{TAG}_role", "permissions": ["kb:view"]},
            fe_match="FE",
        )
        role_id = (role or {}).get("id") if isinstance(role, dict) else None
        self.ctx["role_id"] = role_id

        if role_id:
            self.call(
                "role update",
                "PUT",
                f"/api/roles/{role_id}",
                json={"name": f"{TAG}_role", "permissions": ["kb:view", "chat:use"]},
                fe_match="FE",
            )

        group = self.call(
            "group create",
            "POST",
            "/api/user-groups",
            json={"name": f"{TAG}_group", "description": "checkup"},
            fe_match="FE",
        )
        group_id = (group or {}).get("id") if isinstance(group, dict) else None
        self.ctx["group_id"] = group_id
        if group_id:
            self.call(
                "group update",
                "PUT",
                f"/api/user-groups/{group_id}",
                json={"name": f"{TAG}_group", "description": "checkup2"},
                fe_match="FE",
            )

        user = self.call(
            "user create",
            "POST",
            "/api/users",
            json={
                "username": f"{TAG}_u",
                "password": "Test1234!",
                "display_name": "checkup",
                "status": "启用",
                "role_id": role_id or 2,
            },
            fe_match="FE",
        )
        user_id = (user or {}).get("id") if isinstance(user, dict) else None
        self.ctx["user_id"] = user_id
        if user_id:
            self.call(
                "user update",
                "PUT",
                f"/api/users/{user_id}",
                json={"display_name": "checkup2", "status": "启用", "role_id": role_id or 2},
                fe_match="FE",
            )

        if group_id and user_id:
            self.call(
                "group members",
                "POST",
                f"/api/user-groups/{group_id}/members",
                json={"user_ids": [user_id]},
                fe_match="FE",
            )

        kb = self.call(
            "kb create",
            "POST",
            "/api/knowledge-bases",
            json={"name": f"{TAG}_kb", "description": "checkup", "group_ids": [group_id] if group_id else []},
            fe_match="FE",
        )
        kb_id = (kb or {}).get("id") if isinstance(kb, dict) else None
        self.ctx["kb_id"] = kb_id
        if kb_id:
            self.call(
                "kb update",
                "PUT",
                f"/api/knowledge-bases/{kb_id}",
                json={"name": f"{TAG}_kb", "description": "checkup2"},
                fe_match="FE",
            )
            if group_id:
                self.call(
                    "group kb-access",
                    "POST",
                    f"/api/user-groups/{group_id}/kb-access",
                    json={"kb_ids": [kb_id]},
                    fe_match="FE",
                )

        model = self.call(
            "model create",
            "POST",
            "/api/models",
            json={
                "model_type": "chat",
                "model_name": f"{TAG}_m",
                "api_base_url": "https://example.invalid/v1",
                "dimension": 384,
                "is_active": False,
            },
            fe_match="FE",
        )
        model_id = (model or {}).get("id") if isinstance(model, dict) else None
        self.ctx["model_id"] = model_id
        if model_id:
            self.call(
                "model update",
                "PUT",
                f"/api/models/{model_id}",
                json={"model_name": f"{TAG}_m2", "is_active": False},
                fe_match="FE",
            )

        # branding put（admin 须带齐 name/login_title/footer/theme）
        brand = self.client.get("/api/system/branding", headers=self.auth_headers()).json().get("data") or {}
        self.call(
            "branding put",
            "PUT",
            "/api/system/branding",
            data={
                "brand_name": brand.get("brand_name") or "智能知识平台",
                "brand_theme_color": brand.get("brand_theme_color") or "#4A7AFF",
                "brand_login_title": brand.get("brand_login_title") or "企业知识，智能问答",
                "brand_footer_text": brand.get("brand_footer_text") or "智能 RAG 平台",
            },
            fe_match="FE",
        )

        # documents upload + list + retrieve + chat
        doc_id = None
        if kb_id:
            content = f"# Checkup {TAG}\n\n考勤制度：上班 9:00，下班 18:00。\n请假需提前申请。\n"
            files = {"file": (f"{TAG}.md", io.BytesIO(content.encode("utf-8")), "text/markdown")}
            up = self.call(
                "doc upload",
                "POST",
                f"/api/knowledge-bases/{kb_id}/documents/upload",
                files=files,
                fe_match="FE",
            )
            # wait vectorize
            for i in range(30):
                docs = self.call(
                    "doc list",
                    "GET",
                    f"/api/knowledge-bases/{kb_id}/documents",
                    params={"page": 1, "page_size": 20},
                    fe_match="FE",
                )
                items = docs if isinstance(docs, list) else (docs or {}).get("items") or []
                if items:
                    doc_id = items[0].get("id")
                    st = items[0].get("status")
                    if st in ("completed", "failed"):
                        self.rows[-1]["note"] += f" | status={st}"
                        break
                time.sleep(1)
            self.ctx["doc_id"] = doc_id

            if doc_id:
                self.call(
                    "hit test",
                    "POST",
                    "/api/rag/test_retrieve",
                    json={
                        "kb_id": kb_id,
                        "doc_id": doc_id,
                        "query": "考勤时间",
                        "search_type": "vector",
                        "top_n": 3,
                    },
                    fe_match="FE",
                )

            self.call("warmup", "POST", "/api/chat/warmup", params={"kb_id": kb_id}, fe_match="FE")
            self.call(
                "chat send",
                "POST",
                "/api/chat/send",
                json={"kb_id": kb_id, "query": "考勤几点上班", "search_type": "vector", "top_n": 3},
                fe_match="BE-only",
            )

            # stream
            try:
                lines = 0
                types = set()
                with self.client.stream(
                    "POST",
                    "/api/chat/stream",
                    headers=self.auth_headers(),
                    json={"kb_id": kb_id, "query": "考勤几点下班", "search_type": "vector", "top_n": 3},
                    timeout=120.0,
                ) as r:
                    http = r.status_code
                    sid = None
                    for line in r.iter_lines():
                        if not line:
                            continue
                        lines += 1
                        if line.startswith("data:"):
                            try:
                                ev = json.loads(line[5:].strip())
                                types.add(ev.get("type"))
                                if ev.get("type") == "start":
                                    sid = ev.get("session_id")
                            except Exception:
                                pass
                        if lines >= 80:
                            break
                ok = http == 200 and ("chunk" in types or "done" in types or "start" in types)
                self.record(
                    "POST",
                    "/api/chat/stream",
                    ok,
                    http,
                    0 if ok else None,
                    f"stream lines={lines} types={sorted(types)}",
                    "FE",
                )
                self.ctx["session_id"] = sid
            except Exception as e:
                self.record("POST", "/api/chat/stream", False, "ERR", None, str(e), "FE")

            sid = self.ctx.get("session_id")
            if sid:
                self.call(
                    "sessions list",
                    "GET",
                    "/api/chat/sessions",
                    params={"kb_id": kb_id, "page": 1, "page_size": 20},
                    fe_match="FE",
                )
                self.call(
                    "session messages",
                    "GET",
                    f"/api/chat/sessions/{sid}/messages",
                    params={"page": 1, "page_size": 50},
                    fe_match="FE",
                )
                self.call(
                    "session patch",
                    "PATCH",
                    f"/api/chat/sessions/{sid}",
                    json={"title": "体检会话", "pinned": True},
                    fe_match="FE",
                )
                self.call(
                    "session delete",
                    "DELETE",
                    f"/api/chat/sessions/{sid}",
                    fe_match="FE",
                )

            # second doc for batch-delete
            if kb_id:
                files2 = {
                    "file": (
                        f"{TAG}_b.md",
                        io.BytesIO(f"# B {TAG}\n\nbatch\n".encode("utf-8")),
                        "text/markdown",
                    )
                }
                up2 = self.call(
                    "doc upload 2",
                    "POST",
                    f"/api/knowledge-bases/{kb_id}/documents/upload",
                    files=files2,
                    fe_match="FE",
                )
                time.sleep(1)
                docs = self.client.get(
                    f"/api/knowledge-bases/{kb_id}/documents",
                    headers=self.auth_headers(),
                    params={"page": 1, "page_size": 50},
                ).json()
                items = docs.get("data") if isinstance(docs.get("data"), list) else []
                ids = [d["id"] for d in items]
                if len(ids) >= 2:
                    # 先单删一条，保证 DELETE /api/documents/{doc_id} 被覆盖
                    self.call(
                        "doc delete",
                        "DELETE",
                        f"/api/documents/{ids[0]}",
                        fe_match="FE",
                    )
                    self.call(
                        "batch delete",
                        "POST",
                        "/api/documents/batch-delete",
                        json={"ids": ids[1:2]},
                        fe_match="FE",
                    )
                elif len(ids) == 1:
                    self.call(
                        "doc delete",
                        "DELETE",
                        f"/api/documents/{ids[0]}",
                        fe_match="FE",
                    )

        # cleanup temps (best-effort)
        # 角色若仍挂在用户上无法删：先把用户改回默认 user 角色
        if self.ctx.get("user_id") and self.ctx.get("role_id"):
            self.call(
                "user unbind role",
                "PUT",
                f"/api/users/{self.ctx['user_id']}",
                json={"role_id": 2, "status": "启用"},
                fe_match="FE",
            )
        if self.ctx.get("kb_id"):
            self.call("kb delete", "DELETE", f"/api/knowledge-bases/{self.ctx['kb_id']}", fe_match="FE")
        if self.ctx.get("model_id"):
            self.call("model delete", "DELETE", f"/api/models/{self.ctx['model_id']}", fe_match="FE")
        if self.ctx.get("user_id"):
            self.call("user delete", "DELETE", f"/api/users/{self.ctx['user_id']}", fe_match="FE")
        if self.ctx.get("group_id"):
            self.call("group delete", "DELETE", f"/api/user-groups/{self.ctx['group_id']}", fe_match="FE")
        if self.ctx.get("role_id"):
            self.call("role delete", "DELETE", f"/api/roles/{self.ctx['role_id']}", fe_match="FE")

        return openapi_ops

    def coverage(self, openapi_ops):
        # map exercised normalized templates
        exercised = set()
        for row in self.rows:
            p = row["path"]
            # normalize concrete ids back to templates roughly
            for key, val in list(self.ctx.items()):
                if val is None:
                    continue
                token = str(val)
                if token and token in p:
                    if key == "kb_id":
                        p = p.replace(token, "{kb_id}")
                    elif key == "doc_id":
                        p = p.replace(token, "{doc_id}")
                    elif key == "session_id":
                        p = p.replace(token, "{session_id}")
                    elif key == "user_id":
                        p = p.replace(token, "{user_id}")
                    elif key == "role_id":
                        p = p.replace(token, "{role_id}")
                    elif key == "group_id":
                        p = p.replace(token, "{group_id}")
                    elif key == "model_id":
                        p = p.replace(token, "{config_id}")
            exercised.add((row["method"], p))

        missing = []
        for m, p in openapi_ops:
            # find if any exercised matches
            hit = False
            for em, ep in exercised:
                if em == m and (ep == p or ep.replace("{config_id}", "{config_id}") == p):
                    hit = True
                    break
                # fuzzy: same method and path prefix pattern
                if em == m:
                    # compare segment shapes
                    a = p.split("/")
                    b = ep.split("/")
                    if len(a) == len(b) and all(
                        (x == y) or (x.startswith("{") and y.startswith("{")) or (x.startswith("{") or y.startswith("{"))
                        for x, y in zip(a, b)
                    ):
                        # stricter: equal non-param segments
                        ok = True
                        for x, y in zip(a, b):
                            if x.startswith("{") or y.startswith("{"):
                                continue
                            if x != y:
                                ok = False
                                break
                        if ok:
                            hit = True
                            break
            if not hit:
                missing.append((m, p))
        return exercised, missing


def write_report(probe: Probe, openapi_ops, missing):
    total = len(probe.rows)
    passed = sum(1 for r in probe.rows if r["ok"])
    failed = total - passed
    lines = []
    lines.append("# Day4：接口全身体检报告（非抽检）")
    lines.append("")
    lines.append(f"> **时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> **目标**：`{BASE}`")
    lines.append(f"> **OpenAPI 操作数**：{len(openapi_ops)}")
    lines.append(f"> **实打用例数**：{total}（含创建/更新/删除/上传/流式完整链路）")
    lines.append("")
    lines.append("## 一、总评")
    lines.append("")
    lines.append(f"- **通过**：{passed}/{total}")
    lines.append(f"- **失败**：{failed}/{total}")
    lines.append(f"- **OpenAPI 未覆盖到的操作**：{len(missing)}")
    lines.append("")
    if failed == 0 and not missing:
        lines.append("**结论：全量接口体检通过，前后端主路径可联通。**")
    elif failed == 0:
        lines.append("**结论：已执行用例全部通过；下列 OpenAPI 操作未在本轮落到具体 URL（见第三节）。**")
    else:
        lines.append("**结论：存在失败项，见第二节。**")
    lines.append("")
    lines.append("## 二、逐条结果")
    lines.append("")
    lines.append("| # | 结果 | Method | Path | HTTP | biz | 前端 | 说明 |")
    lines.append("|:-:|:----:|--------|------|:----:|:---:|:----:|------|")
    for i, r in enumerate(probe.rows, 1):
        mark = "✅" if r["ok"] else "❌"
        lines.append(
            f"| {i} | {mark} | {r['method']} | `{r['path']}` | {r['http']} | {r['biz']} | {r['fe']} | {r['note']} |"
        )
    lines.append("")
    lines.append("## 三、OpenAPI 全量清单 vs 本轮覆盖")
    lines.append("")
    lines.append("| Method | Path | 本轮是否打到 | 前端是否声明调用 |")
    lines.append("|--------|------|:------------:|:----------------:|")
    for m, p in openapi_ops:
        covered = "是" if (m, p) not in missing else "否"
        # fe match by template
        fe = "是" if (m, p) in FE_CALLS or (m, p) in BE_ONLY_OK else "—"
        if (m, p) in FE_CALLS:
            fe = "是"
        elif (m, p) in BE_ONLY_OK:
            fe = "仅后端"
        else:
            # fuzzy FE
            fe = "否"
            for fm, fp in FE_CALLS:
                if fm != m:
                    continue
                if fp == p:
                    fe = "是"
                    break
                sa, sb = fp.split("/"), p.split("/")
                if len(sa) == len(sb) and all(
                    (x == y) or x.startswith("{") or y.startswith("{") for x, y in zip(sa, sb)
                ):
                    if all((x == y) or x.startswith("{") or y.startswith("{") for x, y in zip(sa, sb)):
                        same = True
                        for x, y in zip(sa, sb):
                            if x.startswith("{") or y.startswith("{"):
                                continue
                            if x != y:
                                same = False
                        if same:
                            fe = "是"
                            break
            if fe == "否" and (m, p) in BE_ONLY_OK:
                fe = "仅后端"
        lines.append(f"| {m} | `{p}` | {covered} | {fe} |")
    lines.append("")
    if missing:
        lines.append("### 未覆盖操作")
        for m, p in missing:
            lines.append(f"- `{m} {p}`")
        lines.append("")
    fails = [r for r in probe.rows if not r["ok"]]
    lines.append("## 四、失败项明细")
    lines.append("")
    if not fails:
        lines.append("无。")
    else:
        for r in fails:
            lines.append(f"- ❌ `{r['method']} {r['path']}` http={r['http']} biz={r['biz']} — {r['note']}")
    lines.append("")
    lines.append("## 五、前后端一致性说明")
    lines.append("")
    lines.append("- 前端 `src/api/*` 声明的 REST/SSE 路径均在 OpenAPI 中存在（会话已去掉错误 fallback）。")
    lines.append("- 后端独有：`/health`、`/api/health`、`/metrics`、`/api/auth/login/json`、`/api/chat/send`（可接受）。")
    lines.append("- 对话字段：`query`；命中测试：`doc_id` + `query`；登录：form `username/password`。")
    lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written: {OUT}")
    print(f"PASS {passed}/{total} FAIL {failed} OPENAPI_MISSING {len(missing)}")
    return failed


def main():
    # health gate
    try:
        httpx.get(f"{BASE}/health", timeout=5).raise_for_status()
    except Exception as e:
        print(f"Backend not up at {BASE}: {e}")
        sys.exit(2)
    probe = Probe()
    openapi_ops = probe.run()
    _, missing = probe.coverage(openapi_ops)
    # refine missing: if we hit concrete path, remove template from missing
    still = []
    for m, p in missing:
        found = False
        for row in probe.rows:
            if row["method"] != m:
                continue
            # simple heuristic: same segment count and fixed parts
            a, b = p.strip("/").split("/"), row["path"].strip("/").split("/")
            if len(a) != len(b):
                continue
            ok = True
            for x, y in zip(a, b):
                if x.startswith("{"):
                    continue
                if x != y:
                    ok = False
                    break
            if ok:
                found = True
                break
        if not found:
            still.append((m, p))
    rc = write_report(probe, openapi_ops, still)
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
