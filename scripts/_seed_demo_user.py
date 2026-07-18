"""Create a demo normal user for local testing (idempotent)."""
import httpx

base = "http://127.0.0.1:8001"

login = httpx.post(
    f"{base}/api/auth/login",
    data={"username": "admin", "password": "admin123"},
    timeout=15,
).json()
assert login.get("code") == 0, login
token = login["data"]["access_token"]
h = {"Authorization": f"Bearer {token}"}

roles = httpx.get(f"{base}/api/roles", headers=h, timeout=15).json()
role_list = roles.get("data") or []
user_role = next((r for r in role_list if r.get("name") == "user"), None)
assert user_role, roles

users = httpx.get(f"{base}/api/users", headers=h, timeout=15).json()
existing = [u for u in (users.get("data") or []) if u.get("username") == "demo"]
if existing:
    print("demo user already exists", existing[0].get("id"))
else:
    created = httpx.post(
        f"{base}/api/users",
        headers=h,
        json={
            "username": "demo",
            "password": "demo123",
            "display_name": "演示普通用户",
            "role_id": user_role["id"],
            "status": "启用",
        },
        timeout=15,
    ).json()
    print("create demo", created.get("code"), created.get("msg") or created.get("data"))

# ensure a user group + kb for isolation demo (optional soft)
print("DONE")
print("accounts:")
print("  admin / admin123  (role=admin)")
print("  demo  / demo123   (role=user)")
