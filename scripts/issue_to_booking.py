"""Turn a booking issue form (env BODY) into bookings/<start>_<member>.json."""
import os, re, json, datetime as dt
parts = re.split(r"^### ", os.environ["BODY"], flags=re.M)[1:]
f = {p.split("\n", 1)[0].strip().lower(): p.split("\n", 1)[1].strip() for p in parts}
b = {"member": f["who are you?"], "start": f["arrival date (yyyy-mm-dd)"],
     "end": f["departure date (yyyy-mm-dd)"], "beds": int(f["beds needed"])}
dt.date.fromisoformat(b["start"]); dt.date.fromisoformat(b["end"])
path = f"bookings/{b['start']}_{b['member']}.json"
json.dump(b, open(path, "w")); print(path)
