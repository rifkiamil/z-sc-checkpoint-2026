"""
clone_all_org_repos.py
----------------------
Discovers ALL repos in a GitHub org and clones each one into:

    runs/{batch_id}/{org}/{repo_name}/

Batch ID is generated from the current timestamp (YYYYMMDD-HHMMSS).
Each run is fully isolated — re-running creates a new batch folder.
Uses the `gh` CLI (must be authenticated: `gh auth login`).

Usage:
    python clone_all_org_repos.py                  # defaults to Smlcrm
    python clone_all_org_repos.py --org Smlcrm
    python clone_all_org_repos.py --org Smlcrm --limit 50
    python clone_all_org_repos.py --dry-run        # list repos only, no clone
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Defaults ───────────────────────────────────────────────────────────────────

DEFAULT_ORG   = "Smlcrm"
DEFAULT_LIMIT = 200          # gh repo list max per call
RUNS_ROOT     = Path(__file__).parent / "runs"

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_batch_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def check_gh_auth() -> None:
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if result.returncode != 0:
        log.error("gh CLI is not authenticated. Run: gh auth login")
        sys.exit(1)


def list_org_repos(org: str, limit: int) -> list[dict]:
    """Return list of {name, visibility} dicts for all repos in the org."""
    log.info("Fetching repo list for org: %s (limit=%d)", org, limit)
    result = subprocess.run(
        ["gh", "repo", "list", org, "--limit", str(limit),
         "--json", "name,visibility"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error("Failed to list repos:\n%s", result.stderr.strip())
        sys.exit(1)

    repos = json.loads(result.stdout)
    log.info("Found %d repos in %s.", len(repos), org)
    return repos


def clone_repo(org: str, repo: str, dest_base: Path) -> bool:
    """Clone org/repo into dest_base/repo. Returns True on success."""
    target = dest_base / repo

    if target.exists():
        log.warning("  SKIP   %s/%s  →  already exists", org, repo)
        return True

    slug = f"{org}/{repo}"
    log.info("  CLONE  %s  →  %s", slug, target)

    result = subprocess.run(
        ["gh", "repo", "clone", slug, str(target)],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        log.info("  OK     %s", slug)
        return True
    else:
        log.error("  FAIL   %s\n%s", slug, result.stderr.strip())
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Clone all repos from a GitHub org.")
    parser.add_argument("--org",     default=DEFAULT_ORG,   help="GitHub org name")
    parser.add_argument("--limit",   default=DEFAULT_LIMIT, type=int, help="Max repos to fetch")
    parser.add_argument("--dry-run", action="store_true",   help="List repos only, do not clone")
    args = parser.parse_args()

    check_gh_auth()

    repos     = list_org_repos(args.org, args.limit)
    batch_id  = make_batch_id()
    dest_base = RUNS_ROOT / batch_id / args.org

    log.info("=" * 60)
    log.info("Batch ID : %s", batch_id)
    log.info("Org      : %s", args.org)
    log.info("Repos    : %d", len(repos))
    log.info("Output   : %s", dest_base)
    if args.dry_run:
        log.info("Mode     : DRY RUN (no cloning)")
    log.info("=" * 60)

    if args.dry_run:
        for r in repos:
            print(f"  [{r['visibility']:8s}]  {args.org}/{r['name']}")
        return

    dest_base.mkdir(parents=True, exist_ok=True)

    results = {}
    for r in repos:
        results[r["name"]] = clone_repo(args.org, r["name"], dest_base)

    # ── Summary ────────────────────────────────────────────────────────────────
    total   = len(results)
    success = sum(v for v in results.values())
    failed  = [name for name, ok in results.items() if not ok]

    log.info("=" * 60)
    log.info("Done.  %d/%d cloned successfully.", success, total)
    if failed:
        log.warning("Failed: %s", ", ".join(failed))
    log.info("Local path: %s", dest_base)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
