#!/usr/bin/env python3
"""Offline, repository-scoped quality gate for Nichola."""

import argparse
import json
import os
import posixpath
import subprocess
import sys
import tempfile
import tomllib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from scripts.qa_approval import check_approval
except ModuleNotFoundError:  # Direct execution places scripts/, not repo root, on sys.path.
    from qa_approval import check_approval

APPROVED = {
    "task/nichola-vulcan-gates": Path("E:/2_nichola-worktrees/vulcan_pycraft"),
    "task/nichola-frontend-ui": Path("E:/2_nichola-worktrees/frontend_forge"),
    "integration/nichola": Path("E:/2_nichola-worktrees/atlas_operations"),
    "validation/nichola-minerva": Path("E:/2_nichola-worktrees/minerva_qa"),
}
PROTECTED = Path("E:/2_nichola/site")
DEPLOY_ENV_EXACT = {
    "URL", "DEPLOY_URL", "DEPLOY_PRIME_URL", "CONTEXT", "BRANCH",
    "HEAD", "COMMIT_REF", "CACHED_COMMIT_REF", "PULL_REQUEST",
}
DEPLOY_ENV_PREFIXES = ("NETLIFY_", "GITHUB_", "KOALENDAR_")
EXPECTED_PAGES = {
    "index.html", "services.html", "owner.html", "assessment.html",
    "pricing.html", "faq.html", "area.html", "book.html", "contact.html",
    "policies/privacy.html", "policies/safeguarding.html",
    "policies/cancellations.html", "policies/payment.html",
}


class GateFailure(RuntimeError):
    pass


def _normal(path):
    return os.path.normcase(os.path.abspath(os.fspath(path))).replace("\\", "/")


def enforce_worktree_safety(repo_root, branch, dirty):
    root = _normal(repo_root)
    if root == _normal(PROTECTED):
        raise GateFailure("protected main checkout is never an allowed gate target")
    if branch == "main":
        raise GateFailure("main branch is never an allowed gate target")
    expected = APPROVED.get(branch)
    if expected is None or root != _normal(expected):
        raise GateFailure("branch/path does not match an approved worktree mapping")
    if dirty:
        raise GateFailure("worktree has a dirty pre-state")


def isolated_environment(source=None):
    source = os.environ if source is None else source
    return {
        key: value for key, value in source.items()
        if key not in DEPLOY_ENV_EXACT
        and not key.upper().startswith(DEPLOY_ENV_PREFIXES)
    }


def run(command, root, capture=True, display=True):
    completed = subprocess.run(
        command,
        cwd=root,
        env=isolated_environment(),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if display and capture and completed.stdout:
        print(completed.stdout.rstrip())
    if completed.returncode:
        raise GateFailure("command failed (%d): %s" % (completed.returncode, " ".join(command)))
    return completed.stdout or ""


def git(root, *args):
    return run(["git", *args], root, display=False).strip()


def check_python(root):
    tracked = [p for p in git(root, "ls-files", "*.py").splitlines() if p]
    for rel in tracked:
        source = (root / rel).read_bytes()
        compile(source, rel, "exec", dont_inherit=True)
    print("PYTHON-SYNTAX: PASSED — %d tracked Python files" % len(tracked))
    return len(tracked)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.ids = set()
        self.duplicate_ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        element_id = attrs.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)
        for attribute in ("href", "src"):
            if attrs.get(attribute):
                self.links.append(attrs[attribute])


def _target_for(root, source_rel, raw):
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or raw.startswith(("mailto:", "tel:", "data:", "javascript:")):
        return None, None
    path = unquote(parsed.path)
    if not path:
        return source_rel, parsed.fragment
    if path.startswith("/"):
        candidate = path.lstrip("/")
    else:
        candidate = posixpath.normpath(posixpath.join(posixpath.dirname(source_rel), path))
    if candidate.endswith("/"):
        candidate += "index.html"
    target = root / candidate
    if not target.exists() and not Path(candidate).suffix:
        html_candidate = candidate + ".html"
        if (root / html_candidate).exists():
            candidate = html_candidate
    return candidate, parsed.fragment


def check_static_site(root):
    for rel in ("content/site.json", "content/policies.json"):
        json.loads((root / rel).read_text(encoding="utf-8"))
    config = tomllib.loads((root / "netlify.toml").read_text(encoding="utf-8"))
    build = config.get("build", {})
    if build.get("publish") != "." or build.get("command") != "python3 build/generate.py":
        raise GateFailure("netlify.toml must use the repository-local generator and publish root")
    failures = []
    parsers = {}
    tracked_html = [
        p for p in git(root, "ls-files", "*.html").splitlines()
        if p and not p.startswith("build/templates/")
    ]
    if not EXPECTED_PAGES.issubset(set(tracked_html)):
        raise GateFailure("the complete 13-page generated output is not tracked")
    for rel in tracked_html:
        parser = LinkParser()
        parser.feed((root / rel).read_text(encoding="utf-8"))
        parsers[rel] = parser
        if parser.duplicate_ids:
            failures.append("%s duplicate ids: %s" % (rel, ", ".join(sorted(parser.duplicate_ids))))
    for source_rel, parser in parsers.items():
        for raw in parser.links:
            target_rel, fragment = _target_for(root, source_rel, raw)
            if target_rel is None:
                continue
            target = root / target_rel
            if not target.is_file():
                failures.append("%s -> missing %s" % (source_rel, raw))
                continue
            if fragment and target_rel.endswith(".html"):
                target_parser = parsers.get(target_rel)
                if target_parser is None:
                    target_parser = LinkParser()
                    target_parser.feed(target.read_text(encoding="utf-8"))
                    parsers[target_rel] = target_parser
                if fragment not in target_parser.ids:
                    failures.append("%s -> missing fragment %s" % (source_rel, raw))
    if failures:
        raise GateFailure("static-site validation failed:\n  " + "\n  ".join(failures))
    print("STATIC-SITE: PASSED — JSON, Netlify config, and %d tracked HTML files/links" % len(tracked_html))


def check_generator(root):
    output = run([sys.executable, "build/generate.py", "--check"], root)
    expected = "BYTE-IDENTITY: PASSED — all 13 generated pages are byte-identical"
    if expected not in output:
        raise GateFailure("generator did not confirm byte identity for all 13 pages")


def repository_gate(root, promotion_approval=None):
    branch = git(root, "branch", "--show-current")
    dirty = bool(git(root, "status", "--porcelain", "--untracked-files=all"))
    enforce_worktree_safety(root, branch, dirty)
    print("WORKTREE-SAFETY: PASSED — %s at %s" % (branch, root))
    check_python(root)
    check_static_site(root)
    check_generator(root)
    if promotion_approval:
        sha = git(root, "rev-parse", "HEAD")
        check_approval(promotion_approval, sha)
        print("QA-APPROVAL: PASSED — exact integration SHA %s" % sha)
    post_dirty = bool(git(root, "status", "--porcelain", "--untracked-files=all"))
    if post_dirty:
        raise GateFailure("gate changed the worktree")
    print("TREE-CLEAN: PASSED — gate left the worktree unchanged")
    print("REPOSITORY-GATE: PASSED")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promotion-approval", type=Path)
    args = parser.parse_args(argv)
    try:
        root_text = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            env=isolated_environment(), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=True,
        ).stdout.strip()
        root = Path(root_text)
        if _normal(Path.cwd()) != _normal(root):
            raise GateFailure("run the gate from the repository root")
        repository_gate(root, args.promotion_approval)
        return 0
    except (GateFailure, OSError, UnicodeError, json.JSONDecodeError, tomllib.TOMLDecodeError, subprocess.CalledProcessError) as exc:
        print("REPOSITORY-GATE: FAILED — %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
