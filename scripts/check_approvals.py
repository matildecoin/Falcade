"""Require a currently approved GitHub reviewer from every configured family."""
import json
import sys
from pathlib import Path

from build import read_json


def check_approvals(config, reviews, head_sha):
    states = {}
    for review in sorted(reviews, key=lambda item: item.get("submitted_at", "")):
        if review.get("commit_id") != head_sha:
            continue
        user = review.get("user") or {}
        login = user.get("login")
        if login:
            states[login.casefold()] = review.get("state", "").upper()

    errors = []
    seen = set()
    for family in config.get("famiglie", []):
        users = family.get("approval_users", [])
        if not users:
            errors.append(f"{family['name']}: configure at least one approval_users GitHub login")
            continue
        overlap = [user for user in users if user.casefold() in seen]
        if overlap:
            errors.append(f"{family['name']}: approver logins must be unique across families")
        seen.update(user.casefold() for user in users)
        if not any(states.get(user.casefold()) == "APPROVED" for user in users):
            errors.append(f"{family['name']}: waiting for an approval from a configured family member")
    return errors


def main():
    if len(sys.argv) != 3:
        print("Usage: check_approvals.py <reviews.json> <pull-request-head-sha>", file=sys.stderr)
        return 2
    try:
        config = read_json(Path("families.json"))
        reviews = read_json(Path(sys.argv[1]))
        if isinstance(reviews, list) and all(isinstance(page, list) for page in reviews):
            reviews = [review for page in reviews for review in page]
        if not isinstance(reviews, list):
            raise ValueError("review list must be a JSON array")
        errors = check_approvals(config, reviews, sys.argv[2])
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"Cannot verify family approvals: {error}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Every family nucleus has an approving reviewer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
