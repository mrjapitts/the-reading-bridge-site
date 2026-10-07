import json
import os
import tempfile
import unittest
from pathlib import Path

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

    def write_approval(self, sha="a" * 40, issuer="minerva_qa"):
        self.approval.write_text(
            json.dumps(
                {
                    "schema": "nichola.qa-approval/v1",
                    "integration_sha": sha,
                    "issuer_profile": issuer,
                    "decision": "approved",
                    "evidence": ["python scripts/repo_gate.py: PASS"],
                    "issued_at_utc": "2026-10-08T10:00:00Z",
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


if __name__ == "__main__":
    unittest.main()
