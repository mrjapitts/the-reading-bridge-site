#!/usr/bin/env python3
"""Create or verify a policy-attested QA approval for one integration SHA.

The JSON is an operational handoff artifact, not a signature. It proves exact-SHA
matching and records a policy assertion; it does not cryptographically prove the
human/profile identity of its creator.
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "nichola.qa-approval/v1"
MINERVA_ROOT = Path("E:/2_nichola-worktrees/minerva_qa")
MINERVA_BRANCH = "validation/nichola-minerva"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ApprovalFailure(RuntimeError):
    pass


def _normal(path):
    return os.path.normcase(os.path.abspath(os.fspath(path))).replace("\\", "/")


def validate_sha(sha):
    if not SHA_RE.fullmatch(sha):
        raise ApprovalFailure("integration SHA must be a lowercase 40-character Git SHA")


def enforce_generation_authority(repo_root, branch):
    if _normal(repo_root) != _normal(MINERVA_ROOT) or branch != MINERVA_BRANCH:
        raise ApprovalFailure(
            "only Minerva may generate approval, from its designated validation worktree"
        )


def _is_within_repo(repo_root, path):
    root = _normal(repo_root).rstrip("/")
    candidate = _normal(path)
    return candidate == root or candidate.startswith(root + "/")


def enforce_safe_output_location(repo_root, output_path, ignored):
    if _is_within_repo(repo_root, output_path) and not ignored:
        raise ApprovalFailure(
            "approval output must remain outside tracked history (external or Git-ignored)"
        )


def check_approval(path, expected_sha):
    validate_sha(expected_sha)
    path = Path(path)
    if not path.is_file():
        raise ApprovalFailure("QA approval is missing: %s" % path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ApprovalFailure("QA approval is not valid UTF-8 JSON: %s" % exc) from exc
    required = {
        "schema",
        "integration_sha",
        "issuer_profile",
        "decision",
        "evidence",
        "issued_at_utc",
        "identity_assurance",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ApprovalFailure("QA approval is missing fields: %s" % ", ".join(missing))
    if payload["schema"] != SCHEMA:
        raise ApprovalFailure("unsupported QA approval schema")
    if payload["issuer_profile"] != "minerva_qa":
        raise ApprovalFailure("QA approval issuer must be Minerva")
    if payload["decision"] != "approved":
        raise ApprovalFailure("QA decision is not approved")
    if payload["identity_assurance"] != "policy-attestation-only":
        raise ApprovalFailure("identity assurance must disclose policy-attestation-only")
    if not isinstance(payload["evidence"], list) or not payload["evidence"]:
        raise ApprovalFailure("QA approval evidence must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in payload["evidence"]):
        raise ApprovalFailure("QA approval evidence items must be non-empty strings")
    issued_at_utc = payload["issued_at_utc"]
    if not isinstance(issued_at_utc, str) or not UTC_TIMESTAMP_RE.fullmatch(issued_at_utc):
        raise ApprovalFailure(
            "QA approval issued_at_utc must use canonical YYYY-MM-DDTHH:MM:SSZ format"
        )
    try:
        dt.datetime.strptime(issued_at_utc, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ApprovalFailure("QA approval issued_at_utc is not a real UTC timestamp") from exc
    validate_sha(payload["integration_sha"])
    if payload["integration_sha"] != expected_sha:
        raise ApprovalFailure(
            "QA approval does not match the exact integration SHA "
            "(expected %s, found %s)" % (expected_sha, payload["integration_sha"])
        )
    return payload


def _git(*args):
    return subprocess.run(
        ["git", *args], check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def create_approval(path, integration_sha, evidence):
    validate_sha(integration_sha)
    root = Path(_git("rev-parse", "--show-toplevel"))
    branch = _git("branch", "--show-current")
    enforce_generation_authority(root, branch)
    if _git("rev-parse", "HEAD") != integration_sha:
        raise ApprovalFailure("Minerva HEAD must equal the exact integration SHA being approved")
    path = Path(path).absolute()
    ignored = False
    if _is_within_repo(root, path):
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", os.fspath(path)], cwd=root, check=False
        ).returncode == 0
    enforce_safe_output_location(root, path, ignored)
    payload = {
        "schema": SCHEMA,
        "integration_sha": integration_sha,
        "issuer_profile": "minerva_qa",
        "decision": "approved",
        "evidence": evidence,
        "issued_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "identity_assurance": "policy-attestation-only",
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--sha", required=True)
    check.add_argument("--approval", required=True, type=Path)
    create = sub.add_parser("create")
    create.add_argument("--sha", required=True)
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--evidence", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            payload = check_approval(args.approval, args.sha)
            print("QA-APPROVAL: PASSED — exact integration SHA %s" % payload["integration_sha"])
        else:
            create_approval(args.output, args.sha, args.evidence)
            print("QA-APPROVAL: CREATED — %s" % args.output)
            print("IDENTITY: policy attestation only; no cryptographic identity proof")
        return 0
    except (ApprovalFailure, subprocess.CalledProcessError) as exc:
        print("QA-APPROVAL: FAILED — %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
