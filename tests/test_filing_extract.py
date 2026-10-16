"""Unit tests for pure filing extraction logic.

Phase: INGEST-1 (D-086).
Tests page classification, unit detection, column header resolution,
number token parsing, and candidate row extraction on synthetic texts.
"""

from __future__ import annotations

from decimal import Decimal
import unittest

from thesis_data.filing_extract import (
    PageInput,
    classify_pages,
    detect_column_headers,
    detect_unit,
    extract_amount_columns_from_line,
    extract_amounts_from_pipe_line,
    extract_candidates_from_pages,
    fold,
    is_pipe_form,
    is_table_of_contents,
    parse_number_token,
    unit_to_multiplier,
)


class TestFilingExtractPure(unittest.TestCase):
    def test_fold_vietnamese(self) -> None:
        self.assertEqual(fold("Báo cáo tình hình tài chính"), "bao cao tinh hinh tai chinh")
        self.assertEqual(fold("Đơn vị tính: Triệu đồng"), "don vi tinh  trieu dong")
        self.assertEqual(fold("Nợ nhóm 3 - Dưới tiêu chuẩn"), "no nhom 3   duoi tieu chuan")
        self.assertEqual(fold(""), "")

    def test_is_table_of_contents(self) -> None:
        toc_text = "MỤC LỤC BÁO CÁO TÀI CHÍNH\n1. Báo cáo tình hình tài chính..... trang 5\n2. Thuyết minh.... trang 10"
        self.assertTrue(is_table_of_contents(fold(toc_text)))

        normal_text = "BÁO CÁO TÌNH HÌNH TÀI CHÍNH\nTổng tài sản: 1.000.000 triệu đồng"
        self.assertFalse(is_table_of_contents(fold(normal_text)))

    def test_detect_unit(self) -> None:
        self.assertEqual(detect_unit("Đơn vị tính: triệu đồng"), "million_vnd")
        self.assertEqual(detect_unit("Đơn vị: Triệu VND"), "million_vnd")
        self.assertEqual(detect_unit("Đơn vị: nghìn đồng"), "thousand_vnd")
        self.assertEqual(detect_unit("Đơn vị: VND"), "vnd")
        self.assertEqual(detect_unit("Đơn vị: tỷ đồng"), "billion_vnd")
        self.assertIsNone(detect_unit("Không có thông tin đơn vị ở đây"))

        self.assertEqual(unit_to_multiplier("million_vnd"), Decimal("0.001"))
        self.assertEqual(unit_to_multiplier("billion_vnd"), Decimal("1.0"))
        self.assertEqual(unit_to_multiplier("vnd"), Decimal("0.000000001"))

    def test_parse_number_token(self) -> None:
        self.assertEqual(parse_number_token("1.025.850.127"), Decimal("1025850127"))
        self.assertEqual(parse_number_token("(3.914.077)"), Decimal("-3914077"))
        self.assertEqual(parse_number_token("764,791"), Decimal("764791"))
        self.assertEqual(parse_number_token("-"), Decimal("0"))
        self.assertEqual(parse_number_token("—"), Decimal("0"))
        self.assertEqual(parse_number_token("0"), Decimal("0"))
        self.assertIsNone(parse_number_token("abc"))

    def test_extract_amount_columns_from_line(self) -> None:
        # Line with amounts and percentages: Amount 2025, % 2025, Amount 2024, % 2024
        line = "Nợ dưới tiêu chuẩn 4.473.881 0,19 3.666.965 0,18"
        amounts = extract_amount_columns_from_line(line)
        self.assertEqual(len(amounts), 2)
        self.assertEqual(amounts[0], Decimal("4473881"))
        self.assertEqual(amounts[1], Decimal("3666965"))

        # Line with note reference and 2 amounts
        line2 = "1 Thu nhập lãi thuần 22 58.755.829 50.902.749"
        amounts2 = extract_amount_columns_from_line(line2)
        self.assertIn(Decimal("58755829"), amounts2)
        self.assertIn(Decimal("50902749"), amounts2)

    def test_column_headers_detection(self) -> None:
        lines = [
            "BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
            "Tại ngày 31.12.2025 và 31.12.2024",
            "Đơn vị: Triệu VND",
            "Chỉ tiêu Thuyết minh 31/12/2025 31/12/2024",
        ]
        info = detect_column_headers(lines, 2025)
        self.assertTrue(info.has_target_header)
        self.assertTrue(info.has_prior_header)
        self.assertFalse(info.period_mismatch)

        # Mismatched year
        lines_mismatch = [
            "BÁO CÁO TÀI CHÍNH NĂM 2022",
            "Chỉ tiêu 31/12/2022 31/12/2021",
        ]
        info_mismatch = detect_column_headers(lines_mismatch, 2025)
        self.assertTrue(info_mismatch.period_mismatch)

    def test_page_classification(self) -> None:
        pages = [
            PageInput(page_number=1, text="MỤC LỤC\nBáo cáo..... trang 1"),
            PageInput(
                page_number=2,
                text=(
                    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT\n"
                    "Tại ngày 31.12.2025\n"
                    "Đơn vị: triệu đồng\n"
                    "TỔNG TÀI SẢN 1.000.000 800.000\n"
                    "TỔNG NỢ PHẢI TRẢ 900.000 720.000\n"
                    "TỔNG VỐN CHỦ SỞ HỮU 100.000 80.000"
                ),
            ),
            PageInput(
                page_number=3,
                text=(
                    "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT\n"
                    "Năm 2025 Năm 2024\n"
                    "Thu nhập lãi thuần 30.000 25.000\n"
                    "LỢI NHUẬN SAU THUẾ 15.000 12.000\n"
                    "Cổ đông của Ngân hàng 14.500 11.500"
                ),
            ),
            PageInput(
                page_number=4,
                text=(
                    "THUYẾT MINH BÁO CÁO TÀI CHINH\n"
                    "9.3 Phân tích chất lượng nợ cho vay\n"
                    "31.12.2025 31.12.2024\n"
                    "Nhóm 1 - Nợ đủ tiêu chuẩn 500.000 400.000\n"
                    "Nhóm 2 - Nợ cần chú ý 10.000 8.000\n"
                    "Nhóm 3 - Nợ dưới tiêu chuẩn 3.000 2.500\n"
                    "Nhóm 4 - Nợ nghi ngờ 4.000 3.500\n"
                    "Nhóm 5 - Nợ có khả năng mất vốn 5.000 4.000\n"
                    "Tổng cộng 522.000 418.000"
                ),
            ),
        ]
        stmt = classify_pages(pages)
        self.assertIn(2, stmt.balance_sheet)
        self.assertIn(3, stmt.income_statement)
        self.assertIn(4, stmt.loan_quality_note)

    def test_candidate_extraction_synthetic(self) -> None:
        pages = [
            PageInput(
                page_number=1,
                text=(
                    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT\n"
                    "Tại ngày 31.12.2025 và 31.12.2024\n"
                    "Đơn vị tính: triệu đồng\n"
                    "1. Cho vay khách hàng 600.000.000 500.000.000\n"
                    "2. Dự phòng rủi ro cho vay khách hàng (7.000.000) (6.000.000)\n"
                    "TỔNG CỘNG TÀI SẢN 1.000.000.000 800.000.000\n"
                    "TỔNG VỐN CHỦ SỞ HỮU 100.000.000 80.000.000\n"
                    "Lợi ích của cổ đông không kiểm soát 1.000.000 800.000\n"
                ),
            ),
            PageInput(
                page_number=2,
                text=(
                    "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT\n"
                    "Năm 2025 Năm 2024\n"
                    "Đơn vị tính: triệu đồng\n"
                    "Thu nhập lãi thuần 30.000.000 25.000.000\n"
                    "LỢI NHUẬN SAU THUẾ 15.000.000 12.000.000\n"
                    "Cổ đông của Ngân hàng 14.000.000 11.200.000\n"
                ),
            ),
            PageInput(
                page_number=3,
                text=(
                    "THUYẾT MINH BÁO CÁO TÀI CHÍNH\n"
                    "Theo chất lượng nợ cho vay\n"
                    "31.12.2025 31.12.2024\n"
                    "Đơn vị: triệu đồng\n"
                    "Nhóm 1 - Nợ đủ tiêu chuẩn 580.000.000 480.000.000\n"
                    "Nhóm 2 - Nợ cần chú ý 8.000.000 8.000.000\n"
                    "Nhóm 3 - Nợ dưới tiêu chuẩn 3.000.000 2.500.000\n"
                    "Nhóm 4 - Nợ nghi ngờ 4.000.000 3.500.000\n"
                    "Nhóm 5 - Nợ có khả năng mất vốn 5.000.000 6.000.000\n"
                    "Tổng nhóm 1-5 600.000.000 500.000.000\n"
                ),
            ),
        ]

        result = extract_candidates_from_pages(
            pages,
            entity_id="XYZ",
            fiscal_year=2025,
            reporting_scope="consolidated",
            display_name="Ngân hàng XYZ",
        )

        self.assertEqual(result.entity_id, "XYZ")
        self.assertEqual(result.fiscal_year, 2025)
        self.assertEqual(result.page_count, 3)
        self.assertEqual(result.unit_detected, "million_vnd")

        # Check that 20 rows are created (10 metrics * 2 periods)
        self.assertEqual(len(result.rows), 20)

        # Lookup by metric and period role
        rows_by_key = {(r.metric_id, r.period_role): r for r in result.rows}

        # Check total assets: 1.000.000.000 million VND = 1.000.000 billion VND
        ta_target = rows_by_key[("bank.input.total_assets", "target")]
        self.assertEqual(ta_target.value_billion_vnd, "1000000.000")
        self.assertEqual(ta_target.status, "candidate")

        ta_prior = rows_by_key[("bank.input.total_assets", "prior")]
        self.assertEqual(ta_prior.value_billion_vnd, "800000.000")
        self.assertEqual(ta_prior.status, "candidate")

        # Check total equity: 100.000.000 million = 100.000 billion
        eq_target = rows_by_key[("bank.input.total_equity", "target")]
        self.assertEqual(eq_target.value_billion_vnd, "100000.000")

        # Check profit after tax: 15.000.000 million = 15.000 billion
        pat_target = rows_by_key[("bank.input.profit_after_tax", "target")]
        self.assertEqual(pat_target.value_billion_vnd, "15000.000")

        # Check parent attributable profit: 14.000.000 million = 14.000 billion
        parent_target = rows_by_key[("bank.input.parent_attributable_profit", "target")]
        self.assertEqual(parent_target.value_billion_vnd, "14000.000")

        # Check NPL group 3: 3.000.000 million = 3.000 billion
        g3_target = rows_by_key[("bank.input.npl_group_3_balance", "target")]
        self.assertEqual(g3_target.value_billion_vnd, "3000.000")

        # Check provisions: 7.000.000 million = 7.000 billion (positive)
        prov_target = rows_by_key[("bank.input.loan_loss_provisions", "target")]
        self.assertEqual(prov_target.value_billion_vnd, "7000.000")


class TestPipeFormParsing(unittest.TestCase):
    """Tests for the pipe-separated table-flattened line format (LlamaParse-style).

    Lines have the form:
        label | value_target | value_prior
    Header lines have the form:
        | 31.12.2025 Triệu VND | 31.12.2024 Triệu VND
    """

    def test_is_pipe_form_detection(self) -> None:
        self.assertTrue(is_pipe_form("Nhóm 3 - Nợ dưới tiêu chuẩn | 686.777.352 | 580.686.248"))
        self.assertTrue(is_pipe_form("| 31.12.2025 Triệu VND | 31.12.2024 Triệu VND |"))
        self.assertFalse(is_pipe_form("Nhóm 3 - Nợ dưới tiêu chuẩn 686.777.352 580.686.248"))
        self.assertFalse(is_pipe_form("Nhóm 3 - Nợ dưới tiêu chuẩn | 686.777.352"))  # only 1 separator

    def test_extract_amounts_from_pipe_line_basic(self) -> None:
        # Typical LlamaParse row: label | target_amount | prior_amount
        line = "Nhóm 3 - Nợ dưới tiêu chuẩn | 686.777.352 | 580.686.248"
        amounts = extract_amounts_from_pipe_line(line)
        self.assertEqual(len(amounts), 2)
        self.assertEqual(amounts[0], Decimal("686777352"))
        self.assertEqual(amounts[1], Decimal("580686248"))

    def test_extract_amounts_from_pipe_line_comma_sep(self) -> None:
        # Comma thousands separator variant
        line = "Cho vay khách hàng | 764,791 | 648,320"
        amounts = extract_amounts_from_pipe_line(line)
        self.assertEqual(len(amounts), 2)
        self.assertEqual(amounts[0], Decimal("764791"))
        self.assertEqual(amounts[1], Decimal("648320"))

    def test_extract_amounts_from_pipe_line_negative(self) -> None:
        # Negative amounts in parentheses (e.g. provisions)
        line = "Dự phòng rủi ro cho vay khách hàng | (7.000.000) | (6.000.000)"
        amounts = extract_amounts_from_pipe_line(line)
        self.assertEqual(len(amounts), 2)
        self.assertEqual(amounts[0], Decimal("-7000000"))
        self.assertEqual(amounts[1], Decimal("-6000000"))

    def test_extract_amount_columns_dispatches_to_pipe(self) -> None:
        # extract_amount_columns_from_line should auto-dispatch for pipe lines
        line = "Tổng tài sản | 1.025.850.127 | 864.005.703"
        amounts = extract_amount_columns_from_line(line)
        self.assertEqual(len(amounts), 2)
        self.assertEqual(amounts[0], Decimal("1025850127"))
        self.assertEqual(amounts[1], Decimal("864005703"))

    def test_plain_line_not_affected(self) -> None:
        # Pipe-form guard should not affect plain Tesseract lines
        line = "TONG CONG TAI SAN 1.025.850.127 864.005.703"
        amounts = extract_amount_columns_from_line(line)
        self.assertIn(Decimal("1025850127"), amounts)


if __name__ == "__main__":
    unittest.main()
