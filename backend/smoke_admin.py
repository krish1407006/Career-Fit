import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient
from apps.accounts.models import User

c = APIClient()
admin = User.objects.filter(is_superuser=True).first()
if not admin:
    print("no superuser")
    raise SystemExit(0)

c.force_authenticate(admin)
c.defaults["HTTP_HOST"] = "127.0.0.1"
r = c.get("/api/auth/admin/users/")
print("ADMIN_LIST", r.status_code)
print("COUNT", len(r.data) if isinstance(r.data, list) else r.data)

reg = c.post("/api/auth/register/", {
    "username": "smoke_tmp", "email": "smoke@tmp.com", "password": "Smoke@12345",
    "first_name": "Smoke", "last_name": "Tmp", "role": "student",
})
print("REGISTER", reg.status_code)

tmp = User.objects.filter(username="smoke_tmp").first()
if tmp:
    upd = c.patch(f"/api/auth/admin/users/{tmp.id}/", {"role": "recruiter"}, format="json")
    print("ADMIN_PATCH", upd.status_code, upd.data.get("role") if isinstance(upd.data, dict) else upd.data)
