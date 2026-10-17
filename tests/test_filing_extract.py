"""Unit tests for pure filing extraction logic.

Phase: INGEST-1 (D-086).
Tests page classification, unit detection, column header resolution,
number token parsing, and candidate row extraction on synthetic texts.
"""

from __future__ import annotations

from decimal import Decimal
import re
import unittest

from thesis_data.filing_extract import (
    INPUT_METRICS,
    METRIC_LABELS_VI,
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

        # OCR-garbled headers (from Tesseract -l eng on scanned bank filings)
        self.assertEqual(detect_unit("Triéu VND"), "million_vnd")
        self.assertEqual(detect_unit("Tr. VND"), "million_vnd")
        self.assertEqual(detect_unit("TRIỆU ĐỒNG"), "million_vnd")
        self.assertEqual(detect_unit("Don vi: trieu dong"), "million_vnd")
        self.assertEqual(detect_unit("minh Triu VND Triu VND"), "million_vnd")
        self.assertEqual(detect_unit("minh TriguVND ~_Triu VND"), "million_vnd")
        self.assertEqual(detect_unit("Bon vi: Trigu VND"), "million_vnd")
        self.assertEqual(detect_unit("minh triéu déng triéu déng"), "million_vnd")
        self.assertEqual(detect_unit("Chỉ tiêu 31/12/2025 Triệu VND 31/12/2024 Triệu VND"), "million_vnd")

        # Bare VND/dong with no multiplier word MUST return None
        self.assertIsNone(detect_unit("VND"))
        self.assertIsNone(detect_unit("dong"))
        self.assertIsNone(detect_unit("Báo cáo tài chính hợp nhất (VND)"))
        self.assertIsNone(detect_unit("Kính gửi: Các cổ đông của Ngân hàng"))

        # nghìn đồng and tỷ đồng
        self.assertEqual(detect_unit("Đơn vị: nghìn đồng"), "thousand_vnd")
        self.assertEqual(detect_unit("Thuyết minh nghìn VND"), "thousand_vnd")
        self.assertEqual(detect_unit("Đơn vị: tỷ đồng"), "billion_vnd")
        self.assertEqual(detect_unit("Số liệu tính theo tỷ VND"), "billion_vnd")

        # unit_to_multiplier requires explicit valid unit
        self.assertEqual(unit_to_multiplier("million_vnd"), Decimal("0.001"))
        self.assertEqual(unit_to_multiplier("billion_vnd"), Decimal("1.0"))
        self.assertEqual(unit_to_multiplier("thousand_vnd"), Decimal("0.000001"))
        self.assertEqual(unit_to_multiplier("vnd"), Decimal("0.000000001"))
        with self.assertRaises(ValueError):
            unit_to_multiplier(None)
        with self.assertRaises(ValueError):
            unit_to_multiplier("unknown_unit")

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


class TestMissingRowMessagesHumanized(unittest.TestCase):
    """Test that missing-row issue messages use human-readable Vietnamese labels without raw IDs."""

    def test_missing_row_issues_contain_no_raw_ids_or_snake_case(self) -> None:
        # Minimal page with no NPL notes
        pages = [
            PageInput(
                page_number=1,
                source="ocr",
                text="BÁO CÁO TÀI CHÍNH\n31.12.2025\nĐơn vị: tỷ đồng\nTổng tài sản 1000 900",
            )
        ]
        res = extract_candidates_from_pages(
            pages,
            entity_id="TEST",
            fiscal_year=2025,
            reporting_scope="consolidated",
        )
        missing_rows = [r for r in res.rows if r.status == "missing"]
        self.assertGreater(len(missing_rows), 0)

        snake_case_re = re.compile(r"\b[a-z]+_[a-z0-9_]+\b")
        period_code_re = re.compile(r"\b\d{4}_Q\d\b")

        for r in missing_rows:
            for iss in r.issues:
                # Must not contain bank.input
                self.assertNotIn("bank.input", iss.message_vi)
                # Must not contain snake_case identifiers in user-facing message
                self.assertIsNone(
                    snake_case_re.search(iss.message_vi),
                    f"Found snake_case in message_vi: '{iss.message_vi}'",
                )
                # Must not contain raw period code 2025_Q4
                self.assertIsNone(
                    period_code_re.search(iss.message_vi),
                    f"Found raw period code in message_vi: '{iss.message_vi}'",
                )
                # Must contain the Vietnamese label
                expected_label = METRIC_LABELS_VI[r.metric_id]
                self.assertIn(expected_label, iss.message_vi)


class TestFilingExtractLegalAndUnit(unittest.TestCase):
    """Targeted regression tests for PDFFIX-1:
    - Billion VND false positives from company narrative text
    - Proper VND unit detection from statement headers
    - Skipping legal citation lines (Circular 31, Decree 86, Article 10, days past due)
    - Full synthetic reproduction of multi-page filing with notes and legal citations
    """

    def test_detect_unit_false_positives_billion_vnd(self) -> None:
        """Phrases containing 'công ty đang', 'công ty đồng' must NOT trigger billion_vnd."""
        self.assertIsNone(detect_unit("Công ty đang hoạt động bình thường"))
        self.assertIsNone(detect_unit("Công ty đồng kiểm soát"))
        self.assertIsNone(detect_unit("Công ty đứng tên tài sản"))
        self.assertIsNone(detect_unit("Công ty dùng vốn vay đúng mục đích"))
        self.assertIsNone(detect_unit("Công ty đúng hạn trả nợ"))

    def test_detect_unit_table_header_vnd(self) -> None:
        """Table headers containing dates and VND must detect unit as 'vnd'."""
        self.assertEqual(detect_unit("Thuyết minh | 31/12/2025 VND | 31/12/2024 VND"), "vnd")
        self.assertEqual(detect_unit("| Thuyết minh | 31/12/2025 | 31/12/2024 |\n| | VND | VND |"), "vnd")
        self.assertEqual(detect_unit("Thuyết minh 31/12/2025 VND 31/12/2024 VND"), "vnd")

    def test_skip_legal_citation_lines_and_day_counts(self) -> None:
        """Legal citation lines and narrative day counts must return empty amount list."""
        legal1 = (
            "Việc phân loại nợ cho các khoản tiền gửi tại các tổ chức tín dụng khác "
            "được thực hiện theo quy định tại Điều 10 của Thông tư số 31/2024/TT-NHNN "
            "ngày 30 tháng 6 năm 2024 do NHNNVN ban hành"
        )
        self.assertEqual(extract_amount_columns_from_line(legal1), [])

        legal2 = (
            "Theo quy định của Nghị định số 86/2024/NĐ-CP ngày 11 tháng 7 năm 2024 "
            "do Chính phủ ban hành quy định về mức trích, phương pháp trích lập dự phòng"
        )
        self.assertEqual(extract_amount_columns_from_line(legal2), [])

        legal3 = "Theo Luật các Tổ chức tín dụng số 47/2010/QH12 do Quốc hội ban hành"
        self.assertEqual(extract_amount_columns_from_line(legal3), [])

        day_count = "- Nhóm 5 – Nợ có khả năng mất vốn: quá hạn từ 90 ngày trở lên."
        self.assertEqual(extract_amount_columns_from_line(day_count), [])

        # Real table row with thousands-separated amounts must NOT be skipped
        real_table1 = "Dự phòng theo Thông tư 11 | 1.000.000 | 800.000"
        self.assertEqual(
            extract_amount_columns_from_line(real_table1),
            [Decimal("1000000"), Decimal("800000")],
        )

        real_table2 = "Dự phòng theo Thông tư 11 1.000.000 800.000"
        self.assertEqual(
            extract_amount_columns_from_line(real_table2),
            [Decimal("1000000"), Decimal("800000")],
        )

    def test_candidate_extraction_ocb_style_synthetic(self) -> None:
        """Multi-page synthetic extraction simulating OCB filing:
        - Balance sheet in VND with date headers
        - Notes containing narrative circular/decree citations and 'tỷ đồng' text
        - Loan quality note table with real multi-billion VND balances
        Must detect unit as 'vnd' and extract amounts divided by 10^9 without capturing legal citations.
        """
        pages = [
            PageInput(
                page_number=1,
                text=(
                    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT\n"
                    "Tại ngày 31 tháng 12 năm 2025\n"
                    "Thuyết minh | 31/12/2025 VND | 31/12/2024 VND\n"
                    "TỔNG TÀI SẢN | 322.949.479.567.113 | 276.486.854.526.261\n"
                    "TỔNG VỐN CHỦ SỞ HỮU | 33.924.677.884.591 | 31.671.045.433.324\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=2,
                text=(
                    "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT\n"
                    "Năm 2025 Năm 2024\n"
                    "Thuyết minh | 2025 VND | 2024 VND\n"
                    "LỢI NHUẬN SAU THUẾ | 4.010.081.000.000 | 3.173.423.000.000\n"
                    "Cổ đông công ty mẹ | 4.010.081.000.000 | 3.173.423.000.000\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=3,
                text=(
                    "THUYẾT MINH BÁO CÁO TÀI CHÍNH\n"
                    "Chính sách phân loại nợ\n"
                    "Việc phân loại nợ được thực hiện theo quy định tại Điều 10 của "
                    "Thông tư số 31/2024/TT-NHNN ngày 30 tháng 6 năm 2024 do NHNNVN ban hành.\n"
                    "Công ty đang hoạt động với vốn điều lệ 20.000 tỷ đồng và công ty đồng kiểm soát.\n"
                    "- Nhóm 3 – Nợ dưới tiêu chuẩn: quá hạn dưới 30 ngày;\n"
                    "- Nhóm 4 – Nợ nghi ngờ: quá hạn từ 30 ngày đến dưới 90 ngày;\n"
                    "- Nhóm 5 – Nợ có khả năng mất vốn: quá hạn từ 90 ngày trở lên.\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=4,
                text=(
                    "THUYẾT MINH BÁO CÁO TÀI CHÍNH\n"
                    "Phân tích chất lượng nợ cho vay khách hàng\n"
                    "Thuyết minh | 31/12/2025 VND | 31/12/2024 VND\n"
                    "Nhóm 3 - Nợ dưới tiêu chuẩn | 797.210.239.597 | 1.075.776.805.310\n"
                    "Nhóm 4 - Nợ nghi ngờ | 1.715.658.267.794 | 1.710.943.603.143\n"
                    "Nhóm 5 - Nợ có khả năng mất vốn | 3.832.608.212.238 | 2.621.403.037.774\n"
                    "Cho vay khách hàng | 198.764.945.826.810 | 170.844.469.638.663\n"
                    "Dự phòng rủi ro cho vay khách hàng | (3.574.058.101.292) | (2.549.323.810.977)\n"
                ),
                source="llamaparse",
            ),
        ]

        result = extract_candidates_from_pages(
            pages,
            entity_id="OCB",
            fiscal_year=2025,
            reporting_scope="consolidated",
            display_name="Ngân hàng OCB",
        )

        # 1. Unit must be detected as 'vnd' from Balance Sheet, not 'billion_vnd'
        self.assertEqual(result.unit_detected, "vnd")

        rows_by_key = {(r.metric_id, r.period_role): r for r in result.rows}

        # 2. Total assets: 322.949.479.567.113 VND -> 322949.480 billion VND (divided by 10^9)
        ta_target = rows_by_key[("bank.input.total_assets", "target")]
        self.assertEqual(ta_target.value_billion_vnd, "322949.480")
        self.assertEqual(ta_target.page, 1)

        # 3. NPL Group 3: 797.210.239.597 VND -> 797.210 billion VND (NOT 2024 or 31)
        g3_target = rows_by_key[("bank.input.npl_group_3_balance", "target")]
        self.assertEqual(g3_target.value_billion_vnd, "797.210")
        self.assertEqual(g3_target.page, 4)

        # 4. NPL Group 4: 1.715.658.267.794 VND -> 1715.658 billion VND (NOT 2024 or 31)
        g4_target = rows_by_key[("bank.input.npl_group_4_balance", "target")]
        self.assertEqual(g4_target.value_billion_vnd, "1715.658")
        self.assertEqual(g4_target.page, 4)

        # 5. NPL Group 5: 3.832.608.212.238 VND -> 3832.608 billion VND (NOT 5 or 90)
        g5_target = rows_by_key[("bank.input.npl_group_5_balance", "target")]
        self.assertEqual(g5_target.value_billion_vnd, "3832.608")
        self.assertEqual(g5_target.page, 4)

        # 6. Gross customer loans: 198.764.945.826.810 VND -> 198764.946 billion VND (NOT 2024 or 0.010)
        gcl_target = rows_by_key[("bank.input.gross_customer_loans", "target")]
        self.assertEqual(gcl_target.value_billion_vnd, "198764.946")
        self.assertEqual(gcl_target.page, 4)

    def test_ocb_multi_page_classification_and_profit_extraction(self) -> None:
        """Synthetic test for OCB: B03 income statement vs B05 notes, and profit extraction."""
        pages = [
            PageInput(
                page_number=9,
                text=(
                    "NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN PHƯƠNG ĐÔNG\n"
                    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT\n"
                    "Tại ngày 31 tháng 12 năm 2025\n"
                    "Mẫu B02/TCTD-HN\n"
                    "Đơn vị tính: VND\n"
                    "TỔNG TÀI SẢN | 322.949.479.567.113 | 280.000.000.000.000\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=10,
                text=(
                    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT (tiếp theo)\n"
                    "Tiền gửi của khách hàng | 180.000.000.000.000 | 160.000.000.000.000\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=11,
                text=(
                    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT (tiếp theo)\n"
                    "VỐN CHỦ SỞ HỮU | 35.000.000.000.000 | 30.000.000.000.000\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=12,
                text=(
                    "NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN PHƯƠNG ĐÔNG\n"
                    "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT\n"
                    "Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025\n"
                    "Mẫu B03/TCTD-HN\n"
                    "Đơn vị tính: VND\n"
                    "I. Thu nhập lãi và các khoản thu nhập tương tự | 15.000.000.000.000 | 13.000.000.000.000\n"
                    "II. Chi phí lãi và các chi phí tương tự | (8.000.000.000.000) | (7.000.000.000.000)\n"
                    "Thu nhập lãi thuần | 7.000.000.000.000 | 6.000.000.000.000\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=13,
                text=(
                    "NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN PHƯƠNG ĐÔNG\n"
                    "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT (tiếp theo)\n"
                    "Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025\n"
                    "Mẫu B03/TCTD-HN\n"
                    "Đơn vị tính: VND\n"
                    "VIII. Lợi nhuận thuần từ HĐKD trước trích lập | 6.000.000.000.000 | 5.000.000.000.000\n"
                    "IX. Chi phí dự phòng rủi ro tín dụng | (1.000.000.000.000) | (1.000.000.000.000)\n"
                    "X. Tổng lợi nhuận trước thuế | 5.000.000.000.000 | 4.000.000.000.000\n"
                    "XI. Chi phí thuế TNDN | (989.918.885.975) | (826.576.773.232)\n"
                    "XIII. Lợi nhuận sau thuế | 4.010.081.114.025 | 3.173.423.226.768\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=33,
                text=(
                    "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT\n"
                    "Mẫu B05/TCTD-HN\n"
                    "Chính sách kế toán chủ yếu\n"
                    "Báo cáo kết quả hoạt động hợp nhất phản ánh các khoản thu nhập và chi phí phát sinh.\n"
                    "Lợi nhuận phân bổ cho các cổ đông của ngân hàng được xác định theo quy định.\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=35,
                text=(
                    "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT\n"
                    "Mẫu B05/TCTD-HN\n"
                    "Hoạt động dịch vụ và thu nhập khác\n"
                    "Thu nhập lãi và thu nhập thuần khác của ngân hàng trong năm.\n"
                ),
                source="llamaparse",
            ),
        ]

        # 1. Page classification verification
        stmt_pages = classify_pages(pages)
        self.assertEqual(stmt_pages.balance_sheet, [9, 10, 11])
        self.assertEqual(stmt_pages.income_statement, [12, 13])
        self.assertNotIn(33, stmt_pages.income_statement)
        self.assertNotIn(35, stmt_pages.income_statement)

        # 2. Extract candidates and verify profit rows
        result = extract_candidates_from_pages(
            pages,
            entity_id="OCB",
            fiscal_year=2025,
            reporting_scope="consolidated",
            display_name="Ngân hàng TMCP Phương Đông",
        )

        rows_by_key = {(r.metric_id, r.period_role): r for r in result.rows}

        # Verify profit_after_tax
        pat_target = rows_by_key.get(("bank.input.profit_after_tax", "target"))
        self.assertIsNotNone(pat_target, "profit_after_tax:target should be extracted")
        self.assertEqual(pat_target.value_billion_vnd, "4010.081")
        self.assertEqual(pat_target.page, 13)

        pat_prior = rows_by_key.get(("bank.input.profit_after_tax", "prior"))
        self.assertIsNotNone(pat_prior, "profit_after_tax:prior should be extracted")
        self.assertEqual(pat_prior.value_billion_vnd, "3173.423")
        self.assertEqual(pat_prior.page, 13)

        # Verify parent_attributable_profit: when page does not have a separate line for parent profit,
        # it must be missing (no inference from profit_after_tax)
        pap_target = rows_by_key.get(("bank.input.parent_attributable_profit", "target"))
        self.assertIsNotNone(pap_target)
        self.assertEqual(pap_target.status, "missing")
        self.assertIsNone(pap_target.value_billion_vnd)

        pap_prior = rows_by_key.get(("bank.input.parent_attributable_profit", "prior"))
        self.assertIsNotNone(pap_prior)
        self.assertEqual(pap_prior.status, "missing")
        self.assertIsNone(pap_prior.value_billion_vnd)

    def test_comparison_line_on_unrelated_page_not_used_for_prior(self) -> None:
        """When an unrelated page contains a line with the exact same label as target,
        it must NOT be picked as prior if it is outside the classified section cluster.
        """
        pages = [
            PageInput(
                page_number=1,
                text=(
                    "BÁO CÁO TÌNH HÌNH TÀI CHÍNH\n"
                    "Mẫu B02/TCTD\n"
                    "Đơn vị: Triệu VND\n"
                    "Tổng tài sản | 500.000.000\n"
                ),
                source="llamaparse",
            ),
            PageInput(
                page_number=50,
                text=(
                    "THUYẾT MINH KHÁC\n"
                    "Mẫu B05/TCTD\n"
                    "Tổng tài sản | 300.000.000\n"
                ),
                source="llamaparse",
            ),
        ]
        res = extract_candidates_from_pages(
            pages,
            entity_id="TEST",
            fiscal_year=2025,
            reporting_scope="consolidated",
        )
        rows_by_key = {(r.metric_id, r.period_role): r for r in res.rows}
        ta_target = rows_by_key[("bank.input.total_assets", "target")]
        ta_prior = rows_by_key[("bank.input.total_assets", "prior")]

        self.assertEqual(ta_target.value_billion_vnd, "500000.000")
        # Must be missing, NOT 300000.000 from page 50
        self.assertEqual(ta_prior.status, "missing")
        self.assertIsNone(ta_prior.value_billion_vnd)


if __name__ == "__main__":
    unittest.main()
