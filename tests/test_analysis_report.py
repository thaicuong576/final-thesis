import unittest

from scripts.render_analysis_report_v2 import render_markdown
from thesis_data.analysis_report import build_analysis_report
from thesis_data.analysis_report_validation import validate_analysis_report


METRICS = [
    ("bank.npl_g35", "NPL nhóm 3–5"),
    ("bank.llr_coverage", "Tỷ lệ bao phủ nợ xấu"),
    ("bank.roa", "ROA"),
    ("bank.roe", "ROE"),
]


def _view() -> dict:
    values = {
        ("ACB", "2024_Q1"): [1.1, 100.0, 2.0, 20.0],
        ("ACB", "2024_Q4"): [1.2, 110.0, 2.1, 22.0],
        ("MBB", "2024_Q1"): [2.5, 70.0, 2.2, 21.0],
        ("MBB", "2024_Q4"): [2.0, 60.0, 2.4, 21.5],
    }
    matrix = []
    for (ticker, period), row_values in values.items():
        matrix.append(
            {
                "ticker": ticker,
                "period": period,
                "status": "success",
                "metrics": [
                    {
                        "metric_id": metric_id,
                        "label": label,
                        "value": value,
                        "display_value": f"{value:.4f}%",
                        "unit": "%",
                        "period_basis": "ttm",
                        "status": "valid",
                        "observation_id": f"obs-{ticker}-{period}-{metric_id}",
                        "source_id": f"src-{ticker}",
                        "source_locator": f"page:{index + 1}",
                        "evidence_ids": [f"ev-{ticker}-{period}-{metric_id}"],
                        "evidence": [
                            {
                                "evidence_id": f"ev-{ticker}-{period}-{metric_id}",
                                "source_id": f"src-{ticker}",
                                "source_document": f"{ticker}.pdf",
                                "page_number": index + 1,
                                "section_name": label,
                                "period": period,
                                "ticker": ticker,
                                "quote": f"{label}: {value}%",
                            }
                        ],
                    }
                    for index, ((metric_id, label), value) in enumerate(zip(METRICS, row_values))
                ],
            }
        )
    return {
        "contract_version": "report-view-v1",
        "run": {
            "status": "success",
            "snapshot_id": "gold-test",
            "arm": "single_agent",
            "model_id": "test",
            "telemetry": {
                "call_count": 1,
                "tool_calls": 1,
                "input_tokens": 1,
                "output_tokens": 1,
                "cost_estimate_usd": 0.0,
                "wall_clock_latency_ms": 1,
            },
        },
        "scope": {
            "issuers": ["ACB", "MBB"],
            "periods": ["2024_Q1", "2024_Q4"],
            "metrics": [{"metric_id": metric_id, "label": label, "unit": "%"} for metric_id, label in METRICS],
        },
        "summary": {"total_cells": 16, "valid_cells": 16, "missing_or_unaccepted_cells": 0},
        "matrix": matrix,
        "missing_cells": [],
        "analysis": {"findings": []},
    }


class AnalysisReportTests(unittest.TestCase):
    def test_claim_driven_report_has_traceable_claims(self):
        report = build_analysis_report(_view())
        validate_analysis_report(report)
        self.assertEqual(report["contract_version"], "analysis-report-v2")
        self.assertGreaterEqual(len(report["claims"]), 5)
        self.assertTrue(all(claim["interpretation"] and claim["limitation"] for claim in report["claims"]))
        self.assertTrue(any(claim["claim_id"] == "q4-profitability-profile" for claim in report["claims"]))
        self.assertTrue(all(claim["support"] == "evidence_backed" for claim in report["claims"]))

    def test_markdown_leads_with_decision_useful_sections(self):
        report = build_analysis_report(_view())
        markdown = render_markdown(report)
        self.assertIn("## Kết luận nhanh", markdown)
        self.assertIn("## Phân tích theo ngân hàng", markdown)
        self.assertIn("## Nhận định và bằng chứng", markdown)
        self.assertIn("## Giới hạn và dữ liệu thiếu", markdown)

    def test_model_claims_are_normalized_against_gold_matrix(self):
        view = _view()
        view["analysis"]["model_claims"] = [
            {
                "claim_id": "model-q4-roa",
                "claim_type": "comparison",
                "priority": "high",
                "title": "ROA leader",
                "claim": "MBB has the highest ROA in Q4.",
                "interpretation": "This is a profitability signal within the selected peer set.",
                "limitation": "It does not establish causality.",
                "support": "evidence_backed",
                "data_refs": ["MBB|2024_Q4|bank.roa"],
                "evidence_ids": ["ev-MBB-2024_Q4-bank.roa"],
                "source_ids": ["src-MBB"],
            }
        ]
        report = build_analysis_report(view)
        validate_analysis_report(report)
        self.assertEqual(report["data_quality"]["claim_origin"], "model")
        self.assertEqual(report["claims"][0]["origin"], "model")
        self.assertEqual(report["claims"][0]["support"], "evidence_backed")


if __name__ == "__main__":
    unittest.main()
