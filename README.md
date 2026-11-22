# Mountain house calendar

The calendar is a static GitHub Pages site, with bookings and presence records stored as JSON in this repository. It needs no database, API keys, or third-party account. The configured family nuclei and members are kept in `families.json`; room capacity is defined there as well.

## How the family uses it

- **Bookings:** choose arrival/departure dates, the number of people-spots, and room allocations in the calendar. The request opens a prefilled GitHub issue; an action validates it and opens a pull request. The booking appears as confirmed only after one configured reviewer from each of the four family nuclei approves it and the PR is merged.
- **Presences:** submit the family members and guests present for today or a past date. The action opens a pull request, and the record is counted after it is reviewed and merged. The yearly table counts each family member and guest once for each recorded date.
- **Sharing:** “Share in WhatsApp” opens a prefilled message for the user to choose a chat and send. Nothing is sent automatically. GitHub can email collaborators about requests and reviews when they enable notifications; direct email or automatic WhatsApp delivery would need a separate service and credentials.

Requests and records are GitHub issues/PRs, so people need access to this repository and a GitHub account to submit or review them. Repository visibility controls who can see family names and stay records; choose a private repository if the information should not be public.

## One-time setup

1. In `families.json`, fill each family's `approval_users` with the real GitHub login(s) allowed to approve bookings for that nucleus. Leave no family unconfigured, and do not assign one login to multiple families. No user identities are assumed by this project.
2. Invite the family members who need to submit requests or review pull requests to the repository. Enable email notifications for the relevant collaborators if they want email reminders.
3. Create the repository labels `booking` and `presence` so the issue templates can label incoming requests.
4. In **Settings → Actions → General**, allow GitHub Actions to create pull requests using `GITHUB_TOKEN`.
5. In **Settings → Branches**, protect `main`: require pull requests, require branches to be up to date, require the `calendar-guard` status check, and dismiss stale approvals when new commits are pushed. Do not allow routine bypass of this check. Booking PRs remain blocked until the status confirms valid room capacity and one approval from every family; presence records are checked for valid dates and counts.
6. In **Settings → Pages**, choose **GitHub Actions** as the source. The deploy workflow builds `docs/data.json` and publishes the calendar after changes reach `main`.

The checks and record builder use only Python's standard library. Run them locally with:

```sh
python -m unittest discover -s tests
python scripts/build.py --check
```
