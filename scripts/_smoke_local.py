import httpx

base = "http://127.0.0.1:8001"

r = httpx.get(f"{base}/health", timeout=10)
print("health", r.status_code, r.json().get("data", {}).get("status"))

r = httpx.post(
    f"{base}/api/auth/login",
    data={"username": "admin", "password": "admin123"},
    timeout=10,
)
body = r.json()
print("login", r.status_code, body.get("code"), list((body.get("data") or {}).keys()))
assert body.get("code") == 0, body
token = body["data"]["access_token"]
user = body["data"]["user"]
print("user.role", user.get("role"), user.get("role_name"))
h = {"Authorization": f"Bearer {token}"}

r = httpx.get(f"{base}/api/auth/me", headers=h, timeout=10)
print("me", r.status_code, r.json().get("code"), r.json().get("data", {}).get("role"))

r = httpx.get(f"{base}/api/system/branding", timeout=10)
print("branding", r.status_code, r.json().get("code"))

r = httpx.get(f"{base}/api/knowledge-bases", headers=h, timeout=10)
print("kbs", r.status_code, r.json().get("code"), "count", len(r.json().get("data") or []))

r = httpx.get(f"{base}/api/dashboard/stats", headers=h, timeout=10)
print("dashboard", r.status_code, r.json().get("code"), r.json().get("data"))

try:
    r = httpx.get("http://127.0.0.1:8000/api/v2/heartbeat", timeout=5)
    print("chroma", r.status_code)
except Exception as e:
    print("chroma err", e)

r = httpx.get("http://127.0.0.1:5173/", timeout=10)
print("frontend", r.status_code)
print("SMOKE_OK")
