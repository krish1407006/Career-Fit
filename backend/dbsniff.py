"""Compare DB schema vs Django model state for accounts_user/user_profile tables."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from django.apps import apps

TABLES = ["accounts_user", "accounts_studentprofile", "accounts_recruiterprofile"]

def db_columns(table):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT column_name, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
            [table],
        )
        return {r[0]: (r[1], r[2]) for r in cur.fetchall()}

def model_fields(table):
    model = {k: v for k, v in apps.get_models() if v._meta.db_table == table}
    if not model:
        return {}
    m = next(iter(model))
    return {f.name: {"null": f.null, "auto_now": f.auto_now, "has_default": f.has_default()} for f in m._meta.fields}

out = []
for t in TABLES:
    dbc = db_columns(t)
    mf = model_fields(t)
    out.append(f"\n=== {t} ===")
    out.append("DB-only columns: %s" % sorted(set(dbc) - set(mf)))
    out.append("Model-only fields: %s" % sorted(set(mf) - set(dbc)))
    drift = []
    for name in sorted(set(dbc) & set(mf)):
        d = dbc[name]
        mo = mf[name]
        # if DB says NOT NULL and no default, a nullable/defaulted model field is a mismatch
        if d[0] == "NO" and not d[1] and (mo["null"] or mo["has_default"]):
            drift.append(f"{name}: db-not-null-no-default vs model null={mo['null']}")
        if mo["auto_now"] and (d[0] != "NO"):
            drift.append(f"{name}: auto_now but db nullable")
    if drift:
        out.append("DRIFT:")
        out.extend("  " + x for x in drift)

open(r"C:\Users\Krish\AppData\Local\Temp\cf_drift2.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
