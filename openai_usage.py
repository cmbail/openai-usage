# pip install requests
import sys
import subprocess
import requests
from collections import defaultdict
from datetime import datetime, timedelta, timezone

BASE_URL = "https://api.openai.com/v1"
KEYCHAIN_SERVICE = "openai_admin_key"
KEYCHAIN_ACCOUNT = None  # defaults to current macOS user

DAYS_BACK = 30
BUCKET_WIDTH = "1d"
TIMEOUT_SECONDS = 60


def get_keychain_secret(service: str, account: str | None = None) -> str:
    cmd = ["security", "find-generic-password", "-s", service, "-w"]
    if account:
        cmd.extend(["-a", account])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"Could not read secret '{service}' from macOS Keychain. "
            f"stderr: {stderr}"
        )

    secret = result.stdout.strip()
    if not secret:
        raise RuntimeError(f"Keychain secret '{service}' was empty.")

    return secret


ADMIN_KEY = get_keychain_secret(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)

HEADERS = {
    "Authorization": f"Bearer {ADMIN_KEY}",
    "Content-Type": "application/json",
}

end_dt = datetime.now(timezone.utc)
start_dt = end_dt - timedelta(days=DAYS_BACK)
start_time = int(start_dt.timestamp())
end_time = int(end_dt.timestamp())


def get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT_SECONDS)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"Request failed: {r.status_code} {r.text}") from e
    return r.json()


def list_all_projects():
    url = f"{BASE_URL}/organization/projects"
    projects = []
    after = None

    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after

        data = get(url, params=params)
        batch = data.get("data", [])
        projects.extend(batch)

        if not data.get("has_more", False) or not batch:
            break

        after = batch[-1]["id"]

    return {p["id"]: p.get("name", p["id"]) for p in projects}


def fetch_costs():
    url = f"{BASE_URL}/organization/costs"
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": BUCKET_WIDTH,
        "group_by[]": "project_id",
        "limit": 100,
    }

    all_buckets = []
    page = None

    while True:
        p = dict(params)
        if page:
            p["page"] = page

        data = get(url, params=p)
        all_buckets.extend(data.get("data", []))

        if not data.get("has_more", False):
            break
        page = data.get("next_page")
        if not page:
            break

    return {"data": all_buckets}


def extract_project_costs(raw):
    totals = defaultdict(float)

    for bucket in raw.get("data", []):
        for row in bucket.get("results", []):
            project_id = row.get("project_id") or "unknown"
            amount = row.get("amount", {})
            if isinstance(amount, dict):
                value = amount.get("value")
            else:
                value = amount

            if value is None:
                continue

            totals[project_id] += float(value)

    return totals


def main():
    projects = list_all_projects()
    raw_costs = fetch_costs()
    totals = extract_project_costs(raw_costs)

    rows = []
    for project_id, project_name in projects.items():
        rows.append((totals.get(project_id, 0.0), project_name, project_id))

    for project_id, cost in totals.items():
        if project_id not in projects:
            rows.append((cost, f"(unresolved) {project_id}", project_id))

    rows.sort(reverse=True)

    print(f"\nOpenAI API cost by project for last {DAYS_BACK} days\n")
    print(f"{'Project':35} {'Project ID':28} {'Cost (USD)':>12}")
    print("-" * 80)
    for cost, name, pid in rows:
        print(f"{name[:35]:35} {pid[:28]:28} {cost:12.2f}")
    print("-" * 80)
    print(f"{'TOTAL':35} {'':28} {sum(totals.values()):12.2f}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)