import os
import requests
from datetime import date, datetime, timedelta


GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

GRAPHQL_URL = "https://api.github.com/graphql"


def github_query(from_date, to_date):
    query = """
    query(
        $username: String!,
        $from: DateTime!,
        $to: DateTime!
    ) {
        user(login: $username) {
            contributionsCollection(
                from: $from,
                to: $to
            ) {
                contributionCalendar {
                    weeks {
                        contributionDays {
                            date
                            contributionCount
                        }
                    }
                }
            }
        }
    }
    """

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    variables = {
        "username": GITHUB_USERNAME,
        "from": from_date,
        "to": to_date
    }

    response = requests.post(
        GRAPHQL_URL,
        json={
            "query": query,
            "variables": variables
        },
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if "errors" in result:
        raise Exception(
            "GitHub GraphQL error: "
            + str(result["errors"])
        )

    if not result.get("data", {}).get("user"):
        raise Exception(
            f"GitHub user '{GITHUB_USERNAME}' not found."
        )

    return result["data"]["user"][
        "contributionsCollection"
    ]["contributionCalendar"]["weeks"]


def get_all_contributions():
    """
    Fetch contribution data year-by-year.

    GitHub limits contributionsCollection to
    a maximum one-year time range, so we query
    each year separately.
    """

    contributions = {}

    current_year = date.today().year

    # GitHub was launched in 2008.
    # Starting from 2008 is enough for all normal accounts.
    for year in range(2008, current_year + 1):

        from_date = f"{year}-01-01T00:00:00Z"

        if year == current_year:
            to_date = datetime.utcnow().strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        else:
            to_date = f"{year}-12-31T23:59:59Z"

        print(
            f"Fetching contributions for {year}..."
        )

        weeks = github_query(
            from_date,
            to_date
        )

        for week in weeks:
            for day in week["contributionDays"]:

                contribution_date = day["date"]
                contribution_count = day[
                    "contributionCount"
                ]

                # Store the maximum in case overlapping
                # calendar boundaries return the same date.
                if contribution_date not in contributions:
                    contributions[
                        contribution_date
                    ] = contribution_count
                else:
                    contributions[
                        contribution_date
                    ] = max(
                        contributions[contribution_date],
                        contribution_count
                    )

    return contributions


def calculate_highest_streak(contributions):
    """
    Calculate the longest consecutive sequence
    of days having at least one contribution.
    """

    active_days = sorted(
        date.fromisoformat(day)
        for day, count in contributions.items()
        if count > 0
    )

    if not active_days:
        return 0

    highest_streak = 1
    current_streak = 1

    for i in range(1, len(active_days)):

        difference = (
            active_days[i] - active_days[i - 1]
        ).days

        if difference == 1:
            current_streak += 1

            highest_streak = max(
                highest_streak,
                current_streak
            )

        else:
            current_streak = 1

    return highest_streak


def calculate_current_streak(contributions):
    """
    Calculate the current consecutive streak.

    GitHub streak convention:
    - If today has a contribution, count from today.
    - Otherwise, if yesterday has a contribution,
      the current streak is still active.
    - Otherwise, current streak = 0.
    """

    active_days = {
        date.fromisoformat(day)
        for day, count in contributions.items()
        if count > 0
    }

    today = date.today()
    yesterday = today - timedelta(days=1)

    # No contribution today or yesterday.
    if today not in active_days and yesterday not in active_days:
        return 0

    if today in active_days:
        current_day = today
    else:
        current_day = yesterday

    streak = 0

    while current_day in active_days:
        streak += 1
        current_day -= timedelta(days=1)

    return streak


def update_readme(
    current_streak,
    highest_streak
):

    readme_path = "README.md"

    with open(
        readme_path,
        "r",
        encoding="utf-8"
    ) as file:
        content = file.read()

    start_marker = "<!-- STREAK_START -->"
    end_marker = "<!-- STREAK_END -->"

    if start_marker not in content:
        raise Exception(
            "STREAK_START marker not found in README.md"
        )

    if end_marker not in content:
        raise Exception(
            "STREAK_END marker not found in README.md"
        )

    start_index = content.index(
        start_marker
    )

    end_index = content.index(
        end_marker
    ) + len(end_marker)

    new_section = f"""<!-- STREAK_START -->
🔥 **Current Streak:** {current_streak} days

🏆 **Highest Streak:** {highest_streak} days
<!-- STREAK_END -->"""

    updated_content = (
        content[:start_index]
        + new_section
        + content[end_index:]
    )

    with open(
        readme_path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(updated_content)


def main():

    print(
        f"Calculating GitHub streak for "
        f"{GITHUB_USERNAME}"
    )

    contributions = get_all_contributions()

    current_streak = calculate_current_streak(
        contributions
    )

    highest_streak = calculate_highest_streak(
        contributions
    )

    print()
    print(
        f"🔥 Current streak: "
        f"{current_streak} days"
    )

    print(
        f"🏆 Highest streak: "
        f"{highest_streak} days"
    )

    update_readme(
        current_streak,
        highest_streak
    )

    print()
    print("README updated successfully.")


if __name__ == "__main__":
    main()