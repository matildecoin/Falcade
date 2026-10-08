# Mountain house calendar

Calendar: GitHub Pages site in `docs/`. Bookings: one JSON file each in `bookings/` (`end` = departure day).

## Setup (once)
1. Edit `families.json` (families, colors, members) and the name list in `.github/ISSUE_TEMPLATE/booking.yml`.
2. Edit `.github/CODEOWNERS`: one GitHub username per family.
3. Settings > Pages: Source = **GitHub Actions**.
4. Settings > Actions > General: tick **Allow GitHub Actions to create and approve pull requests**.
5. Settings > Branches: protect `main`: require a pull request, **1 approval**, review from Code Owners, and the "Check bookings" status.
6. Invite everyone as collaborators, and ask them to enable email notifications.

## How it works
Relative > "Request beds" (issue form) > a bot opens a PR if beds are free > a family rep approves and merges > the calendar updates.
Manual bookings: add a JSON file in a PR; `check.yml` blocks overbooking.
