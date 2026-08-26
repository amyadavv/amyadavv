import os
import requests
from datetime import date, timedelta


USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]


def get_contributions(username):
    url = "https://api.github.com/graphql"

    query = """
    query($username: String!) {
        user(login: $username) {
            contributionsCollection {
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
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        json={
            "query": query,
            "variables": {
                "username": username
            }
        },
        headers=headers
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise Exception(data["errors"])

    weeks = data["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]["weeks"]

    contributions = {}

    for week in weeks:
        for day in week["contributionDays"]:
            contributions[day["date"]] = day["contributionCount"]

    return contributions


def calculate_streaks(contributions):
    contribution_dates = sorted(
        date.fromisoformat(d)
        for d, count in contributions.items()
        if count > 0
    )

    if not contribution_dates:
        return 0, 0

    # Highest streak
    highest_streak = 1
    current_run = 1

    for i in range(1, len(contribution_dates)):
        difference = (
            contribution_dates[i] - contribution_dates[i - 1]
        ).days

        if difference == 1:
            current_run += 1
            highest_streak = max(highest_streak, current_run)
        else:
            current_run = 1

    # Current streak
    today = date.today()

    if today in contribution_dates:
        current_streak = 1
        check_date = today - timedelta(days=1)

    elif (today - timedelta(days=1)) in contribution_dates:
        current_streak = 1
        check_date = today - timedelta(days=2)

    else:
        current_streak = 0
        check_date = None

    if current_streak > 0:
        while check_date in contribution_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    return current_streak, highest_streak


def update_readme(current_streak, highest_streak):
    readme_path = "README.md"

    with open(readme_path, "r", encoding="utf-8") as file:
        content = file.read()

    start_marker = "<!-- STREAK_START -->"
    end_marker = "<!-- STREAK_END -->"

    new_section = f"""<!-- STREAK_START -->
🔥 **Current Streak:** {current_streak} days

🏆 **Highest Streak:** {highest_streak} days
<!-- STREAK_END -->"""

    start = content.find(start_marker)
    end = content.find(end_marker)

    if start == -1 or end == -1:
        print("Streak markers not found in README.md")
        return

    end += len(end_marker)

    content = (
        content[:start]
        + new_section
        + content[end:]
    )

    with open(readme_path, "w", encoding="utf-8") as file:
        file.write(content)


def main():
    print(f"Getting contributions for {USERNAME}...")

    contributions = get_contributions(USERNAME)

    current_streak, highest_streak = calculate_streaks(
        contributions
    )

    print(f"Current streak: {current_streak}")
    print(f"Highest streak: {highest_streak}")

    update_readme(
        current_streak,
        highest_streak
    )

    print("README updated successfully!")


if __name__ == "__main__":
    main()
