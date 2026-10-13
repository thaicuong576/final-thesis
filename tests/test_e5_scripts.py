"""Unit tests for E5 OCR and naive extraction scripts on synthetic data.

Runs without external PDF or OCR dependencies.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.e5_ocr_measure import candidates, classify_text_match
from scripts.e5_naive_extract import (
    classify_extracted_value,
    find_best_row_match,
    fold,
)


class TestE5Scripts(unittest.TestCase):
    def test_candidates_formatting(self) -> None:
        mil, cands = candidates("1234.567")
        self.assertEqual(mil, 1234567)
        self.assertIn("1,234,567", cands)
        self.assertIn("1.234.567", cands)
        self.assertIn("1 234 567", cands)

        # Negative and zero cases
        mil_neg, cands_neg = candidates("-45.6")
        self.assertEqual(mil_neg, -45600)
        self.assertIn("45,600", cands_neg)

        mil_zero, cands_zero = candidates("0")
        self.assertEqual(mil_zero, 0)
        self.assertIn("0", cands_zero)

    def test_classify_text_match_exact_and_space_fix(self) -> None:
        # Exact with comma
        txt_comma = "Du no cho vay khach hang: 1,234,567 trieu dong."
        self.assertEqual(classify_text_match(txt_comma, "1234.567"), "exact_on_page")

        # Exact with dot
        txt_dot = "Du no cho vay khach hang: 1.234.567 trieu dong."
        self.assertEqual(classify_text_match(txt_dot, "1234.567"), "exact_on_page")

        # Space fix: spaced out digits
        txt_spaced = "Du no: 1 234 567"
        self.assertEqual(classify_text_match(txt_spaced, "1234.567"), "exact_on_page")

        txt_separated = "Du no: 1, 234, 567 trieu"
        self.assertEqual(classify_text_match(txt_separated, "1234.567"), "exact_after_space_fix")

    def test_classify_text_match_digits_only(self) -> None:
        # Number appears broken by non-digit characters (e.g. hyphens or parentheses)
        txt_raw = "RefID#1-234-567-XYZ"
        self.assertEqual(classify_text_match(txt_raw, "1234.567"), "digits_only")

    def test_classify_text_match_near_miss_and_not_found(self) -> None:
        # Near miss: <= 2 digits different (1,234,569 vs 1,234,567)
        txt_near = "Du no: 1,234,569 trieu dong"
        self.assertEqual(classify_text_match(txt_near, "1234.567"), "near_miss_misread")

        # Not found: completely different numbers
        txt_other = "Tong tai san: 9,876,543 trieu dong"
        self.assertEqual(classify_text_match(txt_other, "1234.567"), "not_found")

    def test_fold_vietnamese_text(self) -> None:
        self.assertEqual(fold("Lợi nhuận sau thuế TNDN"), "loi nhuan sau thue tndn")
        self.assertEqual(fold("Cho vay khách hàng"), "cho vay khach hang")
        self.assertEqual(fold("Dự phòng rủi ro tín dụng"), "du phong rui ro tin dung")
        self.assertEqual(fold("Đầu tư chứng khoán"), "dau tu chung khoan")

    def test_find_best_row_match(self) -> None:
        lines = [
            "BÁO CÁO TÀI CHÍNH HỢP NHẤT",
            "1. Cho vay khách hàng 1,234,567 1,100,000",
            "2. Dự phòng rủi ro (12,345) (10,000)",
            "Tổng cộng tài sản 55,000,000 50,000,000",
        ]
        nums, score = find_best_row_match(lines, "Cho vay khách hàng")
        self.assertIsNotNone(nums)
        self.assertGreaterEqual(score, 0.6)
        self.assertEqual(nums, ["1,234,567", "1,100,000"])

        # Unmatched row
        nums_miss, score_miss = find_best_row_match(lines, "Tiền gửi của tổ chức tín dụng khác")
        self.assertLess(score_miss, 0.6)

    def test_classify_extracted_value(self) -> None:
        nums = ["1,234,567", "1,100,000"]

        # Current column (index 0)
        self.assertEqual(
            classify_extracted_value(nums, 0.9, "1234.567", col_label="Năm nay"),
            "correct",
        )

        # Comparative column (index 1)
        self.assertEqual(
            classify_extracted_value(nums, 0.9, "1100.0", col_label="So sánh"),
            "correct",
        )

        # Wrong value
        self.assertEqual(
            classify_extracted_value(nums, 0.9, "999.0", col_label="Năm nay"),
            "wrong_value",
        )

        # Row not found
        self.assertEqual(
            classify_extracted_value(None, 0.3, "1234.567"),
            "row_not_found",
        )

        # Column missing: requested comparative column (index 1) but only 1 number present
        self.assertEqual(
            classify_extracted_value(["1,234,567"], 0.9, "1100.0", col_label="So sánh"),
            "column_missing",
        )

    def test_e5_ocr_pages_lazy_import(self) -> None:
        # Verifies scripts.e5_ocr_pages can be imported cleanly
        import scripts.e5_ocr_pages as ocr_pages
        self.assertTrue(callable(ocr_pages.extract_pages_for_pdf))


if __name__ == "__main__":
    unittest.main()
