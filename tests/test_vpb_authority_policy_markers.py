"""Focused checks for VPB authority scope and shared policy markers."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## D-", start + len(heading))
    return text[start:] if next_heading < 0 else text[start:next_heading]


class VpbAuthorityPolicyMarkerTests(unittest.TestCase):
    def test_decision_and_contract_markers_remain_semantic(self) -> None:
        decisions = (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8")
        d063 = section(decisions, "## D-063:")
        d072 = section(decisions, "## D-072:")
        self.assertIn("parent_attributable_equity", d063)
        self.assertIn("gate is open only because attestation", d063)
        self.assertIn("2b292ddf21bd6be8a550f81fb518fca5dc419efb", d072)
        self.assertIn("eligible comparative gate result alone", d072)
        self.assertIn("five-issuer comparison gate is open", d072)

        contract = (ROOT / "docs/DATA-CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("## Hash modes for repository evidence manifests", contract)
        self.assertIn("canonical_lf_utf8_sha256", contract)
        self.assertIn("raw_file_bytes_sha256", contract)
        self.assertIn("explicit `--evidence-root`", contract)

        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("canonical_lf_utf8_sha256", agents)
        self.assertIn("raw_file_bytes_sha256", agents)
        self.assertIn("explicit `--evidence-root`", agents)

    def test_authority_hashes_only_scoped_controls(self) -> None:
        authority = json.loads(
            (ROOT / "reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json")
            .read_text(encoding="utf-8")
        )
        refs = {item["artifact_ref"] for item in authority["control_artifacts"]}
        forbidden = {
            "AGENTS.md",
            "docs/DATA-CONTRACT.md",
            ".agent/memory/lessons-learned.md",
            "docs/DECISIONS.md",
        }
        self.assertTrue(refs.isdisjoint(forbidden), refs & forbidden)
        self.assertEqual(
            authority["policy_refs"],
            [
                "docs/DECISIONS.md#D-063",
                "docs/DECISIONS.md#D-072",
                "docs/DATA-CONTRACT.md#Hash modes for repository evidence manifests",
                "AGENTS.md#Operating principles 2",
            ],
        )

    def test_comparison_gate_opens_from_the_attestation(self) -> None:
        authority = json.loads(
            (ROOT / "reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json")
            .read_text(encoding="utf-8")
        )
        attestation = authority["independent_review_attestation"]
        gate = authority["five_issuer_comparison_gate"]
        self.assertEqual(gate["status"], "open")
        self.assertEqual(gate["opened_by_attestation_ref"], attestation["artifact_ref"])
        self.assertEqual(gate["reviewed_head_sha"], "2b292ddf21bd6be8a550f81fb518fca5dc419efb")
        self.assertEqual(gate["verdict"], "ACCEPT")
        self.assertEqual(gate["gate_result"], {"eligible": True, "blockers": [], "cells_checked": 80, "valid_cells": 76, "missing_cells": 4})


if __name__ == "__main__":
    unittest.main()
