"""Convert a GitHub issue from the calendar into one booking or presence record."""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

from build import read_json


def issue_fields(body):
    fields = {}
    matches = list(re.finditer(r"^###\s+(.+?)\s*$", body, re.M))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        key = " ".join(match.group(1).lower().split())
        fields[key] = body[match.end():end].strip()
    return fields


def required(fields, label):
    value = fields.get(label, "").strip()
    if not value or value.lower() in {"_no response_", "yyyy-mm-dd"}:
        raise ValueError(f"{label} is required")
    return value


def whole_number(value, field, minimum):
    if not re.fullmatch(r"\d+", value):
        raise ValueError(f"{field} must be a whole number")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{field} must be at least {minimum}")
    return result


def find_family(config, name):
    family = next((item for item in config["famiglie"]
                   if item["name"] == name or item["id"] == name), None)
    if family is None:
        raise ValueError(f"Unknown family nucleus: {name}")
    return family


def find_member(family, member):
    if member not in family["members"]:
        raise ValueError(f"{member} is not a member of {family['name']}")


def parse_date(value, label):
    try:
        date = dt.date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must use YYYY-MM-DD") from error
    if date.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD")
    return date


def make_booking(body, config):
    fields = issue_fields(body)
    family = find_family(config, required(fields, "family nucleus"))
    member = required(fields, "requesting member")
    find_member(family, member)
    start = parse_date(required(fields, "arrival date (yyyy-mm-dd)"), "Arrival date")
    end = parse_date(required(fields, "departure date (yyyy-mm-dd)"), "Departure date")
    if end <= start:
        raise ValueError("Departure date must be after arrival date")
    requested = whole_number(required(fields, "people-spots requested"), "People-spots requested", 1)

    rooms = {room["id"]: room for room in config["rooms"]}
    allocations = {}
    for line in required(fields, "rooms (room-id: spots)").splitlines():
        match = re.fullmatch(r"\s*([a-z0-9-]+)\s*:\s*(\d+)\s*", line)
        if not match:
            raise ValueError(f"Invalid room allocation: {line}")
        room_id, count_text = match.groups()
        if room_id not in rooms:
            raise ValueError(f"Unknown room: {room_id}")
        count = int(count_text)
        if count < 1:
            raise ValueError(f"{room_id} allocation must be at least 1")
        if count > rooms[room_id]["spots"]:
            raise ValueError(f"{room_id} has only {rooms[room_id]['spots']} spots")
        if room_id in allocations:
            raise ValueError(f"{room_id} is listed more than once")
        allocations[room_id] = count
    if sum(allocations.values()) != requested:
        raise ValueError("Room allocations must add up to the number of people-spots requested")
    return {
        "family_id": family["id"], "member": member, "start": start.isoformat(),
        "end": end.isoformat(), "rooms": allocations
    }


def make_presence(body, config):
    fields = issue_fields(body)
    family = find_family(config, required(fields, "family nucleus"))
    member = required(fields, "reporting member")
    find_member(family, member)
    date = parse_date(required(fields, "date (yyyy-mm-dd)"), "Date")
    if date > dt.date.today():
        raise ValueError("Presence date cannot be in the future")
    members_present = whole_number(
        required(fields, "family members present"), "Family members present", 0
    )
    if members_present > len(family["members"]):
        raise ValueError(f"Family members present cannot exceed {len(family['members'])}")
    guests = whole_number(required(fields, "guests present"), "Guests present", 0)
    if members_present + guests == 0:
        raise ValueError("Record at least one person")
    return {
        "family_id": family["id"], "member": member, "date": date.isoformat(),
        "members_present": members_present, "guests": guests
    }


def main():
    kind = os.environ.get("REQUEST_KIND")
    number = os.environ.get("ISSUE_NUMBER", "")
    if kind not in {"booking", "presence"} or not re.fullmatch(r"\d+", number):
        print("REQUEST_KIND and a numeric ISSUE_NUMBER are required", file=sys.stderr)
        return 1
    try:
        config = read_json(Path("families.json"))
        body = os.environ.get("BODY", "")
        record = make_booking(body, config) if kind == "booking" else make_presence(body, config)
        if kind == "booking":
            folder = Path("bookings")
        else:
            folder = Path("presences")
        folder.mkdir(exist_ok=True)
        path = folder / f"issue-{number}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"Invalid {kind} request: {error}", file=sys.stderr)
        return 1
    print(path.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
