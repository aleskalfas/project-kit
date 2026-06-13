"""Tests for project-management's shared membership predicate library.

The library lives at `.pkit/capabilities/project-management/scripts/_lib/membership.py`
— capability-internal. These tests load it via `importlib` so the
kit's pytest run catches regressions in the predicate (which every
mutating pm script will invoke at startup per DEC-021).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MEMBERSHIP_PY = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "membership.py"
)


@pytest.fixture(scope="module")
def mship():
    """Load the capability-internal membership library by file path."""
    module_name = "pm_membership_under_test"
    spec = importlib.util.spec_from_file_location(module_name, MEMBERSHIP_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules so @dataclass can resolve cls.__module__ on Identity / MembershipResult.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- Identity resolution ---------------------------------------------


def test_identity_label_prefers_github_login(mship) -> None:
    ident = mship.Identity(github_login="alice", email="alice@example.com")
    assert ident.label() == "alice"


def test_identity_label_falls_back_to_email(mship) -> None:
    ident = mship.Identity(github_login=None, email="bob@example.com")
    assert ident.label() == "bob@example.com"


def test_identity_label_unresolved_when_neither_surface_known(mship) -> None:
    ident = mship.Identity(github_login=None, email=None)
    assert ident.label() == "<unresolved>"


def test_resolve_identity_uses_env_override_when_set(mship, monkeypatch) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: "fallback-login",
        email_provider=lambda: "ci@example.com",
    )
    assert ident.github_login == "ci-bot"
    assert ident.email == "ci@example.com"


def test_resolve_identity_falls_back_to_gh_login_provider(
    mship, monkeypatch
) -> None:
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: "octocat",
        email_provider=lambda: None,
    )
    assert ident.github_login == "octocat"
    assert ident.email is None


def test_resolve_identity_returns_none_when_providers_yield_none(
    mship, monkeypatch
) -> None:
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: None,
        email_provider=lambda: None,
    )
    assert ident.github_login is None
    assert ident.email is None


# --- Membership predicate --------------------------------------------


def test_open_mode_allows_anyone(mship) -> None:
    invoker = mship.Identity(github_login="random", email="random@example.com")
    result = mship.check_membership([], invoker)
    assert result.allowed is True
    assert result.mode == "open"
    assert result.refusal_message is None


def test_closed_mode_allows_listed_github_login(mship) -> None:
    members = [{"github_login": "alice", "email": "alice@example.com"}]
    invoker = mship.Identity(github_login="alice", email=None)
    result = mship.check_membership(members, invoker)
    assert result.allowed is True
    assert result.mode == "closed"


def test_closed_mode_allows_when_email_matches_even_without_login(mship) -> None:
    members = [{"github_login": "alice", "email": "alice@example.com"}]
    invoker = mship.Identity(github_login=None, email="alice@example.com")
    result = mship.check_membership(members, invoker)
    assert result.allowed is True


def test_closed_mode_refuses_non_member(mship) -> None:
    members = [{"github_login": "alice"}]
    invoker = mship.Identity(github_login="bob", email="bob@example.com")
    result = mship.check_membership(members, invoker)
    assert result.allowed is False
    assert result.mode == "closed"
    assert result.refusal_message is not None
    assert "Membership required" in result.refusal_message
    assert "bob" in result.refusal_message
    assert "add-member" in result.refusal_message


def test_closed_mode_skips_malformed_entries(mship) -> None:
    """Non-dict entries in members list don't break the predicate."""
    members = ["bad-entry", None, {"github_login": "alice"}]
    invoker = mship.Identity(github_login="alice", email=None)
    result = mship.check_membership(members, invoker)
    assert result.allowed is True


def test_refusal_message_includes_canonical_remediation_path(mship) -> None:
    invoker = mship.Identity(github_login="bob", email=None)
    msg = mship.format_refusal(invoker)
    assert "project-management" in msg
    assert "members.yaml" in msg
    assert "add-member" in msg


# --- Capability root resolution --------------------------------------


def test_resolve_capability_root_honours_explicit_path(mship, tmp_path) -> None:
    """An explicit path that exists is returned as-is; nonexistent → None."""
    existing = tmp_path / "cap"
    existing.mkdir()
    assert mship.resolve_capability_root(existing) == existing
    nonexistent = tmp_path / "nope"
    assert mship.resolve_capability_root(nonexistent) is None


def test_resolve_capability_root_walks_up_to_find_pkit_tree(
    mship, tmp_path, monkeypatch
) -> None:
    """CWD-walk fallback locates `.pkit/capabilities/project-management/`."""
    cap_dir = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_dir.mkdir(parents=True)
    nested = tmp_path / "src" / "deep" / "child"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    found = mship.resolve_capability_root(None)
    assert found == cap_dir


def test_resolve_capability_root_returns_none_outside_pkit_tree(
    mship, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert mship.resolve_capability_root(None) is None
