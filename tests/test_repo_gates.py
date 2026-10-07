import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts import qa_approval, repo_gate


class WorktreeSafetyTests(unittest.TestCase):
    def test_approved_vulcan_mapping_passes(self):
        repo_gate.enforce_worktree_safety(
            Path("E:/2_nichola-worktrees/vulcan_pycraft"),
            "task/nichola-vulcan-gates",
            dirty=False,
        )

    def test_protected_checkout_is_rejected(self):
        with self.assertRaisesRegex(repo_gate.GateFailure, "protected"):
            repo_gate.enforce_worktree_safety(
                Path("E:/2_nichola/site"), "main", dirty=False
            )

    def test_main_branch_is_rejected_outside_protected_checkout(self):
        with self.assertRaisesRegex(repo_gate.GateFailure, "main"):
            repo_gate.enforce_worktree_safety(Path("E:/tmp/copy"), "main", dirty=False)

    def test_wrong_branch_path_mapping_is_rejected(self):
        with self.assertRaisesRegex(repo_gate.GateFailure, "mapping"):
            repo_gate.enforce_worktree_safety(
                Path("E:/2_nichola-worktrees/atlas_operations"),
                "task/nichola-vulcan-gates",
                dirty=False,
            )

    def test_dirty_pre_state_is_rejected(self):
        with self.assertRaisesRegex(repo_gate.GateFailure, "dirty"):
            repo_gate.enforce_worktree_safety(
                Path("E:/2_nichola-worktrees/vulcan_pycraft"),
                "task/nichola-vulcan-gates",
                dirty=True,
            )


class IsolationTests(unittest.TestCase):
    def test_deployment_environment_is_removed(self):
        original = {
            "PATH": "safe",
            "NETLIFY_AUTH_TOKEN": "secret",
            "NETLIFY_SITE_ID": "site",
            "GITHUB_TOKEN": "secret",
            "GITHUB_SHA": "sha",
            "DEPLOY_URL": "https://production.invalid",
            "URL": "https://production.invalid",
            "KOALENDAR_TOKEN": "secret",
        }
        clean = repo_gate.isolated_environment(original)
        self.assertEqual(clean, {"PATH": "safe"})


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.approval = Path(self.tmp.name) / "approval.json"

    def write_approval(
        self,
        sha="a" * 40,
        issuer="minerva_qa",
        issued_at_utc="2026-10-08T10:00:00Z",
        evidence=None,
    ):
        if evidence is None:
            evidence = ["python scripts/repo_gate.py: PASS"]
        self.approval.write_text(
            json.dumps(
                {
                    "schema": "nichola.qa-approval/v1",
                    "integration_sha": sha,
                    "issuer_profile": issuer,
                    "decision": "approved",
                    "evidence": evidence,
                    "issued_at_utc": issued_at_utc,
                    "identity_assurance": "policy-attestation-only",
                }
            ),
            encoding="utf-8",
        )

    def test_missing_approval_fails(self):
        with self.assertRaisesRegex(qa_approval.ApprovalFailure, "missing"):
            qa_approval.check_approval(self.approval, "a" * 40)

    def test_old_sha_fails(self):
        self.write_approval(sha="b" * 40)
        with self.assertRaisesRegex(qa_approval.ApprovalFailure, "exact"):
            qa_approval.check_approval(self.approval, "a" * 40)

    def test_exact_sha_passes(self):
        self.write_approval()
        result = qa_approval.check_approval(self.approval, "a" * 40)
        self.assertEqual(result["identity_assurance"], "policy-attestation-only")

    def test_canonical_rfc3339_utc_timestamp_passes(self):
        self.write_approval(issued_at_utc="2024-02-29T23:59:59Z")
        result = qa_approval.check_approval(self.approval, "a" * 40)
        self.assertEqual(result["issued_at_utc"], "2024-02-29T23:59:59Z")

    def test_noncanonical_or_invalid_timestamp_fails(self):
        invalid_timestamps = (
            "2026-02-29T10:00:00Z",
            "2026-10-08T10:00:00+00:00",
            "2026-10-08T10:00:00.000Z",
            "2026-10-08 10:00:00Z",
        )
        for timestamp in invalid_timestamps:
            with self.subTest(timestamp=timestamp):
                self.write_approval(issued_at_utc=timestamp)
                with self.assertRaisesRegex(qa_approval.ApprovalFailure, "issued_at_utc"):
                    qa_approval.check_approval(self.approval, "a" * 40)

    def test_evidence_items_must_be_nonempty_trimmed_strings(self):
        for evidence in ([""], ["   "], [123], ["pass", None]):
            with self.subTest(evidence=evidence):
                self.write_approval(evidence=evidence)
                with self.assertRaisesRegex(qa_approval.ApprovalFailure, "evidence"):
                    qa_approval.check_approval(self.approval, "a" * 40)

    def test_non_minerva_issuer_fails(self):
        self.write_approval(issuer="atlas_operations")
        with self.assertRaisesRegex(qa_approval.ApprovalFailure, "Minerva"):
            qa_approval.check_approval(self.approval, "a" * 40)

    def test_generation_requires_minerva_worktree_mapping(self):
        with self.assertRaisesRegex(qa_approval.ApprovalFailure, "Minerva"):
            qa_approval.enforce_generation_authority(
                Path("E:/2_nichola-worktrees/atlas_operations"),
                "integration/nichola",
            )
        qa_approval.enforce_generation_authority(
            Path("E:/2_nichola-worktrees/minerva_qa"),
            "validation/nichola-minerva",
        )

    def test_malformed_sha_is_rejected(self):
        self.write_approval()
        with self.assertRaisesRegex(qa_approval.ApprovalFailure, "40-character"):
            qa_approval.check_approval(self.approval, "abc")

    def test_tracked_output_location_is_rejected(self):
        with self.assertRaisesRegex(qa_approval.ApprovalFailure, "outside tracked history"):
            qa_approval.enforce_safe_output_location(
                Path("E:/2_nichola-worktrees/minerva_qa"),
                Path("E:/2_nichola-worktrees/minerva_qa/approval.json"),
                ignored=False,
            )

    def test_external_or_ignored_output_location_passes(self):
        qa_approval.enforce_safe_output_location(
            Path("E:/2_nichola-worktrees/minerva_qa"),
            Path("E:/2_nichola-handoff/qa-approvals/approval.json"),
            ignored=False,
        )
        qa_approval.enforce_safe_output_location(
            Path("E:/2_nichola-worktrees/minerva_qa"),
            Path("E:/2_nichola-worktrees/minerva_qa/.nichola-state/approval.json"),
            ignored=True,
        )

    def test_external_creation_does_not_invoke_git_check_ignore(self):
        repo = Path(self.tmp.name) / "repo"
        output = Path(self.tmp.name) / "handoff" / "approval.json"
        repo.mkdir()
        sha = "a" * 40
        with (
            mock.patch.object(qa_approval, "MINERVA_ROOT", repo),
            mock.patch.object(
                qa_approval,
                "_git",
                side_effect=(str(repo), qa_approval.MINERVA_BRANCH, sha),
            ),
            mock.patch.object(qa_approval.subprocess, "run") as run_mock,
        ):
            qa_approval.create_approval(output, sha, ["gate: PASS"])
        run_mock.assert_not_called()
        self.assertTrue(output.is_file())

    def test_ignored_in_repo_creation_invokes_git_check_ignore(self):
        repo = Path(self.tmp.name) / "repo"
        output = repo / ".nichola-state" / "approval.json"
        repo.mkdir()
        sha = "a" * 40
        with (
            mock.patch.object(qa_approval, "MINERVA_ROOT", repo),
            mock.patch.object(
                qa_approval,
                "_git",
                side_effect=(str(repo), qa_approval.MINERVA_BRANCH, sha),
            ),
            mock.patch.object(
                qa_approval.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0),
            ) as run_mock,
        ):
            qa_approval.create_approval(output, sha, ["gate: PASS"])
        run_mock.assert_called_once()
        self.assertTrue(output.is_file())


class RepositoryGateMainTests(unittest.TestCase):
    def test_approval_failures_are_reported_once_without_traceback(self):
        root = Path.cwd()
        for message in (
            "QA approval is missing: MISSING",
            "QA approval does not match the exact integration SHA",
        ):
            with self.subTest(message=message):
                stderr = io.StringIO()
                with (
                    mock.patch.object(
                        repo_gate.subprocess,
                        "run",
                        return_value=SimpleNamespace(stdout=str(root)),
                    ),
                    mock.patch.object(
                        repo_gate,
                        "repository_gate",
                        side_effect=qa_approval.ApprovalFailure(message),
                    ),
                    contextlib.redirect_stderr(stderr),
                ):
                    result = repo_gate.main(["--promotion-approval", "approval.json"])
                self.assertEqual(result, 1)
                self.assertEqual(
                    stderr.getvalue(),
                    "REPOSITORY-GATE: FAILED — %s\n" % message,
                )
                self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
