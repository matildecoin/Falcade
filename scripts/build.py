"""Validate bookings and build docs/data.json. Use --check to validate only.
A booking's `end` is the departure day (nights = start .. end-1)."""
import json, glob, sys, datetime as dt
fam = json.load(open("families.json"))
cap = fam["beds"]
who = {m for f in fam["families"] for m in f["members"]}
bookings, errs, used = [], [], {}
for p in sorted(glob.glob("bookings/*.json")):
    try:
        b = json.load(open(p))
        s, e = dt.date.fromisoformat(b["start"]), dt.date.fromisoformat(b["end"])
        n = int(b["beds"])
        if b["member"] not in who: errs.append(f"{p}: unknown member {b['member']}")
        if e <= s: errs.append(f"{p}: end must be after start")
        if not 1 <= n <= cap: errs.append(f"{p}: beds must be 1-{cap}")
    except Exception as x:
        errs.append(f"{p}: invalid file ({x})"); continue
    bookings.append({"member": b["member"], "start": b["start"], "end": b["end"], "beds": n})
    d = s
    while d < e:
        used[d] = used.get(d, 0) + n
        if used[d] > cap: errs.append(f"{p}: only {cap - (used[d] - n)} bed(s) left on {d}")
        d += dt.timedelta(days=1)
if errs:
    print("\n".join(sorted(set(errs)))); sys.exit(1)
if "--check" not in sys.argv:
    json.dump({"beds": cap, "families": fam["families"], "bookings": bookings}, open("docs/data.json", "w"))
    print(f"{len(bookings)} bookings built")
