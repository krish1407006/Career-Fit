import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.apps import apps
from django.db import connection



TABLES = ["accounts_user", "accounts_studentprofile", "accounts_recruiterprofile"]

out = []


def db_columns(table):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT column_name, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
            [table],
        )
        return {r[0]: {"nullable": r[1], "default": r[2]} for r in cur.fetchall()}


def model_fields(table):
    for m in apps.get_models():
        if m._meta.db_table == table:
            return {
                f.name: {
                    "null": f.null,
                    "auto_now": bool(getattr(f, "auto_now", False)),
                    "has_default": f.has_default(),
                    "auto_created": f.auto_created,
                }
                for f in m._meta.fields
            }
    return {}


for t in TABLES:
    dc = db_columns(t)
    mc = model_fields(t)
    if not mc:
        out.append(f"=== {t}: MODEL NOT FOUND ===")
        continue
    out.append(f"=== {t} ===")
    only_db = sorted(set(dc) - set(mc) - {"_state"})
    only_model = sorted(set(mc) - set(dc))
    out.append(f"DB-only columns : {only_db}")
    out.append(f"Model-only fields: {only_model}")
    for name in sorted(set(dc) & set(mc)):
        d = dc[name]
        m = mc[name]
        if d["nullable"] == "NO" and not d["default"] and (m["null"] or m["has_default"]):
            out.append(
                f"  DRIFT {name}: DB NOT NULL w/o default, model null={m['null']} has_default={m['has_default']} auto_now={m['auto_now']}"
            )
        if m["auto_now"] and d["nullable"] != "NO":
            out.append(f"  DRIFT {name}: model auto_now but DB column nullable")

open(r"C:\Users\Krish\AppData\Local\Temp\cf_drift3.txt", "w", encoding="utf-8").write(
    "\n".join(out)
)
print("\n".join(out))
