"""Validate house records and build the JSON consumed by the GitHub Pages app."""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path


def read_json(path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def iso_date(value, field, path, errors):
    if not isinstance(value, str):
        errors.append(f"{path}: {field} must be a YYYY-MM-DD date")
        return None
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{path}: {field} must be a YYYY-MM-DD date")
        return None
    if parsed.isoformat() != value:
        errors.append(f"{path}: {field} must be a YYYY-MM-DD date")
        return None
    return parsed


def build_data(root=Path("."), today=None):
    root = Path(root)
    today = today or dt.date.today()
    errors = []
    try:
        config = read_json(root / "families.json")
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"families.json: cannot read configuration ({error})") from error

    rooms = config.get("rooms")
    families = config.get("famiglie")
    if not isinstance(rooms, list) or not rooms:
        raise ValueError("families.json: rooms must be a non-empty list")
    if not isinstance(families, list) or not families:
        raise ValueError("families.json: famiglie must be a non-empty list")

    room_by_id = {}
    for room in rooms:
        if not isinstance(room, dict):
            errors.append("families.json: every room must be an object")
            continue
        room_id, name, capacity = room.get("id"), room.get("name"), room.get("spots")
        if (not isinstance(room_id, str) or not re.fullmatch(r"[a-z0-9-]+", room_id)
                or not isinstance(name, str) or not name.strip()
                or type(capacity) is not int or capacity < 1):
            errors.append(f"families.json: invalid room {room!r}")
            continue
        if room_id in room_by_id:
            errors.append(f"families.json: duplicate room id {room_id}")
        room_by_id[room_id] = room

    family_by_id = {}
    members = {}
    configured_approvers = set()
    for family in families:
        if not isinstance(family, dict):
            errors.append("families.json: every family must be an object")
            continue
        family_id, name = family.get("id"), family.get("name")
        household = family.get("members")
        approvers = family.get("approval_users", [])
        if (not isinstance(family_id, str) or not family_id
                or not isinstance(name, str) or not name.strip()
                or not isinstance(family.get("color"), str)
                or not re.fullmatch(r"#[0-9a-fA-F]{6}", family.get("color", ""))
                or not isinstance(household, list) or not household
                or any(not isinstance(member, str) or not member.strip() for member in household)
                or len(set(household)) != len(household)
                or not isinstance(approvers, list)
                or any(not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9-]+", user)
                       for user in approvers)):
            errors.append(f"families.json: invalid family {family!r}")
            continue
        if family_id in family_by_id:
            errors.append(f"families.json: duplicate family id {family_id}")
        family_by_id[family_id] = family
        for member in household:
            if member in members:
                errors.append(f"families.json: member {member} belongs to more than one family")
            members[member] = family_id
        for user in approvers:
            login = user.casefold()
            if login in configured_approvers:
                errors.append(f"families.json: approval login {user} is assigned to multiple families")
            configured_approvers.add(login)

    bookings = []
    used = {}
    for path in sorted((root / "bookings").glob("*.json")):
        try:
            booking = read_json(path)
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path}: invalid file ({error})")
            continue
        if not isinstance(booking, dict):
            errors.append(f"{path}: booking must be an object")
            continue
        family_id = booking.get("family_id")
        family = family_by_id.get(family_id) if isinstance(family_id, str) else None
        member = booking.get("member")
        if family is None:
            errors.append(f"{path}: unknown family {family_id}")
        if family and member not in family["members"]:
            errors.append(f"{path}: {member} is not a member of family {family_id}")
        start = iso_date(booking.get("start"), "start", path, errors)
        end = iso_date(booking.get("end"), "end", path, errors)
        allocations = booking.get("rooms")
        if not isinstance(allocations, dict) or not allocations:
            errors.append(f"{path}: rooms must contain at least one room allocation")
            continue
        valid_allocations = {}
        for room_id, spots in allocations.items():
            room = room_by_id.get(room_id)
            if room is None:
                errors.append(f"{path}: unknown room {room_id}")
            if type(spots) is not int or spots < 1:
                errors.append(f"{path}: spots for {room_id} must be a positive whole number")
            elif room and spots > room["spots"]:
                errors.append(f"{path}: {room_id} has only {room['spots']} spots")
            else:
                valid_allocations[room_id] = spots
        if start is None or end is None or end <= start:
            if start is not None and end is not None and end <= start:
                errors.append(f"{path}: end must be after start")
            continue
        bookings.append({
            "family_id": family_id, "member": member, "start": booking["start"],
            "end": booking["end"], "rooms": valid_allocations
        })
        day = start
        while day < end:
            for room_id, spots in valid_allocations.items():
                key = (day, room_id)
                used[key] = used.get(key, 0) + spots
                capacity = room_by_id[room_id]["spots"]
                if used[key] > capacity:
                    errors.append(
                        f"{path}: {room_id} is over capacity on {day} "
                        f"({used[key]} requested, {capacity} available)"
                    )
            day += dt.timedelta(days=1)

    presences = []
    seen_presence_dates = set()
    for path in sorted((root / "presences").glob("*.json")):
        try:
            presence = read_json(path)
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path}: invalid file ({error})")
            continue
        if not isinstance(presence, dict):
            errors.append(f"{path}: presence must be an object")
            continue
        family_id = presence.get("family_id")
        family = family_by_id.get(family_id) if isinstance(family_id, str) else None
        member = presence.get("member")
        if family is None:
            errors.append(f"{path}: unknown family {family_id}")
        if family and member not in family["members"]:
            errors.append(f"{path}: {member} is not a member of family {family_id}")
        day = iso_date(presence.get("date"), "date", path, errors)
        if day and day > today:
            errors.append(f"{path}: presence date cannot be in the future")
        members_present = presence.get("members_present")
        guests = presence.get("guests")
        if type(members_present) is not int or members_present < 0:
            errors.append(f"{path}: members_present must be a non-negative whole number")
        elif family and members_present > len(family["members"]):
            errors.append(f"{path}: members_present exceeds the size of family {family_id}")
        if type(guests) is not int or guests < 0:
            errors.append(f"{path}: guests must be a non-negative whole number")
        if (type(members_present) is int and members_present >= 0
                and type(guests) is int and guests >= 0
                and members_present + guests == 0):
            errors.append(f"{path}: record at least one person")
        if day and isinstance(family_id, str) and family_id in family_by_id:
            key = (day, family_id)
            if key in seen_presence_dates:
                errors.append(f"{path}: family {family_id} already has a presence record for {day}")
            seen_presence_dates.add(key)
        presences.append({
            "family_id": family_id, "member": member, "date": presence.get("date"),
            "members_present": members_present, "guests": guests
        })

    if errors:
        raise ValueError("\n".join(sorted(set(errors))))

    repository = os.environ.get("GITHUB_REPOSITORY", "matildecoin/Falcade")
    return {
        "repository": repository,
        "rooms": rooms,
        "families": [
            {key: family[key] for key in ("id", "name", "color", "members")}
            for family in families
        ],
        "bookings": bookings,
        "presences": presences
    }


def main():
    check_only = "--check" in sys.argv
    try:
        data = build_data()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if not check_only:
        output = Path("docs/data.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(data['bookings'])} bookings and {len(data['presences'])} presence records built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
