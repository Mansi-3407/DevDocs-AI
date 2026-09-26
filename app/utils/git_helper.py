# Interface stub added by Person 4 — do not implement logic here.
# TODO: implement (Person 1)
from __future__ import annotations


def get_changed_files(repo_path: str, base_ref: str = "HEAD~1") -> list[str]:
    """Return list of files changed since base_ref in the given repository.

    Args:
        repo_path: Path to the root of the git repository.
        base_ref:  Git ref to diff against (default: one commit back).

    Returns:
        List of file paths relative to repo_path.
    """
    # TODO: implement (Person 1) — suggested: use gitpython
    return []


def get_diff(repo_path: str, base_ref: str = "HEAD~1") -> str:
    """Return the unified diff between HEAD and base_ref.

    Args:
        repo_path: Path to the root of the git repository.
        base_ref:  Git ref to diff against (default: one commit back).

    Returns:
        Raw unified-diff string.  Empty string if repo has no history.
    """
    # TODO: implement (Person 1) — suggested: use gitpython
    return ""
