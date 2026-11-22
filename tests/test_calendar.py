import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build import build_data
from check_approvals import check_approvals
from issue_to_booking import make_booking, make_presence


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "bookings").mkdir()
        (self.root / "presences").mkdir()
        self.config = json.loads((ROOT / "families.json").read_text(encoding="utf-8"))
        (self.root / "families.json").write_text(
            json.dumps(self.config), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_record(self, folder, name, record):
        path = self.root / folder / name
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_capacity_is_tracked_per_room_and_overlaps(self):
        self.write_record("bookings", "first.json", {
            "family_id": "m", "member": "Marina", "start": "2026-12-01",
            "end": "2026-12-03", "rooms": {"room1-ds": 2}
        })
        self.write_record("bookings", "other-room.json", {
            "family_id": "t", "member": "Marta", "start": "2026-12-01",
            "end": "2026-12-03", "rooms": {"room2-ds": 3}
        })
        payload = build_data(self.root, today=dt.date(2026, 11, 1))
        self.assertEqual(len(payload["bookings"]), 2)

        self.write_record("bookings", "overlap.json", {
            "family_id": "s", "member": "Tommy", "start": "2026-12-02",
            "end": "2026-12-04", "rooms": {"room1-ds": 1}
        })
        with self.assertRaisesRegex(ValueError, "over capacity on 2026-12-02"):
            build_data(self.root, today=dt.date(2026, 11, 1))

    def test_presence_totals_and_future_dates(self):
        self.write_record("presences", "day.json", {
            "family_id": "m", "member": "Marina", "date": "2026-05-01",
            "members_present": 3, "guests": 2
        })
        payload = build_data(self.root, today=dt.date(2026, 5, 1))
        self.assertEqual(payload["presences"][0]["members_present"] + payload["presences"][0]["guests"], 5)

        self.write_record("presences", "future.json", {
            "family_id": "t", "member": "Marta", "date": "2026-05-02",
            "members_present": 1, "guests": 0
        })
        with self.assertRaisesRegex(ValueError, "cannot be in the future"):
            build_data(self.root, today=dt.date(2026, 5, 1))

    def test_only_one_presence_record_per_family_and_date(self):
        record = {
            "family_id": "m", "member": "Marina", "date": "2026-05-01",
            "members_present": 1, "guests": 0
        }
        self.write_record("presences", "first.json", record)
        self.write_record("presences", "second.json", record)
        with self.assertRaisesRegex(ValueError, "already has a presence record"):
            build_data(self.root, today=dt.date(2026, 5, 1))

    def test_issue_booking_requires_room_allocations_to_match(self):
        body = """### Family nucleus

Famglia Marina

### Requesting member

Marina

### Arrival date (YYYY-MM-DD)

2026-12-01

### Departure date (YYYY-MM-DD)

2026-12-03

### People-spots requested

2

### Rooms (room-id: spots)

room1-ds: 2"""
        booking = make_booking(body, self.config)
        self.assertEqual(booking["rooms"], {"room1-ds": 2})
        with self.assertRaisesRegex(ValueError, "must add up"):
            make_booking(body.replace("room1-ds: 2", "room1-ds: 1"), self.config)

    def test_presence_issue_allows_guest_only_record_and_validates_family(self):
        today = dt.date.today().isoformat()
        body = f"""### Family nucleus

Famiglia Tommy

### Reporting member

Marta

### Date (YYYY-MM-DD)

{today}

### Family members present

0

### Guests present

2"""
        presence = make_presence(body, self.config)
        self.assertEqual(presence["members_present"], 0)
        self.assertEqual(presence["guests"], 2)

    def test_booking_approvals_require_a_current_approval_per_family(self):
        config = {"famiglie": [
            {"name": f"Family {index}", "approval_users": [f"reviewer-{index}"]}
            for index in range(4)
        ]}
        reviews = [
            {"user": {"login": f"reviewer-{index}"}, "state": "APPROVED",
             "submitted_at": f"2026-01-0{index + 1}T00:00:00Z", "commit_id": "current"}
            for index in range(4)
        ]
        self.assertEqual(check_approvals(config, reviews, "current"), [])
        reviews.append({
            "user": {"login": "reviewer-2"}, "state": "COMMENTED",
            "submitted_at": "2026-02-01T00:00:00Z", "commit_id": "current"
        })
        self.assertIn("Family 2: waiting", "\n".join(check_approvals(config, reviews, "current")))
        reviews = [review for review in reviews if review["user"]["login"] != "reviewer-2"]
        reviews.append({
            "user": {"login": "reviewer-2"}, "state": "APPROVED",
            "submitted_at": "2026-02-01T00:00:00Z", "commit_id": "old"
        })
        self.assertIn("Family 2: waiting", "\n".join(check_approvals(config, reviews, "current")))


if __name__ == "__main__":
    unittest.main()
