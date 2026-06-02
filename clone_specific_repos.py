"""
clone_specific_repos.py
-----------------------
Clones a predefined list of Smlcrm repos into a structured local directory:

    runs/{batch_id}/{org}/{repo_name}/

Batch ID is generated from the current timestamp (YYYYMMDD-HHMMSS).
Uses the `gh` CLI (must be authenticated: `gh auth status`).
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

ORG = "Smlcrm"

REPOS = [
    "web-webapp-portal",
    "training-data-demo",
    "infra-template-bootstrap-cicd",
    "data-mafti-transform-datacontact-poc",
    "data-etl-duckcb-serverless-gcp",
]

RUNS_ROOT = Path(__file__).parent / "runs"

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
    """Abort early if gh CLI is not authenticated."""
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error("gh CLI is not authenticated. Run: gh auth login")
        sys.exit(1)


def clone_repo(org: str, repo: str, dest: Path) -> bool:
    """
    Clone org/repo into dest using gh repo clone.
    Returns True on success, False on failure.
    """
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / repo

    if target.exists():
        log.warning("  SKIP   %s  →  already exists at %s", repo, target)
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
    check_gh_auth()

    batch_id = make_batch_id()
    dest_base = RUNS_ROOT / batch_id / ORG

    log.info("=" * 60)
    log.info("Batch ID : %s", batch_id)
    log.info("Org      : %s", ORG)
    log.info("Repos    : %d", len(REPOS))
    log.info("Output   : %s", dest_base)
    log.info("=" * 60)

    results = {}
    for repo in REPOS:
        results[repo] = clone_repo(ORG, repo, dest_base)

    # ── Summary ────────────────────────────────────────────────────────────────
    success = sum(v for v in results.values())
    failed  = [r for r, ok in results.items() if not ok]

    log.info("=" * 60)
    log.info("Done.  %d/%d cloned successfully.", success, len(REPOS))
    if failed:
        log.warning("Failed repos: %s", ", ".join(failed))
    log.info("Local path: %s", dest_base)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
