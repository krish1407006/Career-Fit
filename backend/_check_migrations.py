import glob, io

out = []
files = glob.glob(r"D:\Career Fit\backend\apps\accounts\migrations\*.py")
for m in sorted(files):
    text = open(m, "r", encoding="utf-8").read()
    hits = [l for l in text.splitlines() if "updated_at" in l or "updated_at" in l]
    if hits:
        out.append("== " + m.split("migrations\\")[-1])
        for l in hits:
            out.append("  " + l.strip())
    out.append("--- " + m.split("migrations\\")[-1] + " name= baseline: " + str("updated_at" in text))

open(r"C:\Users\Krish\AppData\Local\Temp\cf_mig2.txt", "w", encoding="utf-8").write("\n".join(out))
print("files checked:", len(files))
