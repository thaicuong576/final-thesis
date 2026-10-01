"""Provider-reported cost is captured per call and written only to an opt-in local log."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from thesis_api.cost_tracker import LLMUsageTracker, _extract_cost
from thesis_api.service import _append_local_cost_log


class LocalCostLogTest(unittest.TestCase):
    def test_cost_is_read_from_usage_and_never_estimated(self) -> None:
        self.assertEqual(_extract_cost(SimpleNamespace(usage=SimpleNamespace(cost=1e-05))), 1e-05)
        self.assertEqual(_extract_cost({"usage": {"cost": 0.002}}), 0.002)
        self.assertIsNone(_extract_cost(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10))))
        self.assertIsNone(_extract_cost(SimpleNamespace()))

    def test_log_is_written_only_when_enabled(self) -> None:
        tracker = LLMUsageTracker()
        tracker.record_call("writer", 100, 10, 5, cost=0.001)
        tracker.record_call("critic", 200, 20, 6, cost=0.002)
        tracker.record_call("writer", 50, 3, 1)
        self.assertAlmostEqual(tracker.total_cost, 0.003)
        tmp = Path(tempfile.mkdtemp())
        try:
            log = tmp / "costs.jsonl"
            with mock.patch.dict(os.environ, {"LLM_COST_LOG_PATH": ""}):
                _append_local_cost_log(run_id="r0", created_at="t", query="q", model="m", tracker=tracker)
            self.assertFalse(log.exists())
            with mock.patch.dict(os.environ, {"LLM_COST_LOG_PATH": str(log)}):
                _append_local_cost_log(run_id="r1", created_at="t", query="q", model="m", tracker=tracker)
            row = json.loads(log.read_text(encoding="utf-8").strip())
            self.assertEqual(row["run_id"], "r1")
            self.assertAlmostEqual(row["provider_cost"], 0.003)
            self.assertEqual(len(row["calls"]), 3)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
