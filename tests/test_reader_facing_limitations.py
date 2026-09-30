"""Tests for reader-facing limitation formatting and critic issue sanitation."""

import unittest
from thesis_api.summaries_vi import (
    _format_single_critic_limitation,
    format_critic_limitations,
    clean_reader_facing_limitations,
)
from thesis_data.schema import CritiqueIssue, CritiqueIssueType, CritiqueSeverity, CritiqueIssueStatus, CritiqueAction


class TestReaderFacingLimitations(unittest.TestCase):
    """Verify critic issues are converted into clean, neutral Vietnamese reader-facing limitations."""

    def test_single_obs_peer_median_roe_q4_2024(self) -> None:
        """Exact case from user prompt and screenshot."""
        desc = (
            "Câu sent-company-7 nêu 'ROE của ACB cao hơn trung vị ngành 18,6%'. Tuy nhiên, "
            "trung vị ngành (peer median) cho ROE tại Q4/2024 chỉ được xác định từ 1 quan sát duy nhất "
            "(TCB, 15,5%), nên giá trị trung vị ngành thực chất bằng đúng giá trị của TCB. Việc gọi đây "
            "là 'trung vị ngành' và so sánh ACB với nó có thể gây hiểu nhầm rằng đây là đại diện cho toàn "
            "ngành, trong khi mẫu chỉ có một ngân hàng. Cần bổ sung lưu ý về cỡ mẫu hoặc diễn đạt lại "
            "để tránh khái quát hóa quá mức."
        )
        formatted = _format_single_critic_limitation(desc)
        self.assertEqual(
            formatted,
            "Trung vị ngành cho ROE quý 4/2024 chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo.",
        )

    def test_single_obs_peer_median_npl(self) -> None:
        desc = (
            "So sánh tỷ lệ nợ xấu với trung vị ngành tại quý 4/2024 nhưng trung vị chỉ có 1 quan sát duy nhất."
        )
        formatted = _format_single_critic_limitation(desc)
        self.assertEqual(
            formatted,
            "Trung vị ngành cho tỷ lệ nợ xấu quý 4/2024 chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo.",
        )

    def test_unhandled_critic_issue_converted_to_neutral_summary(self) -> None:
        """Issues containing internal IDs or author directives fallback to neutral summary."""
        issue1 = CritiqueIssue(
            issue_id="issue-1",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            severity=CritiqueSeverity.MINOR,
            description="Câu sent-company-2: Cần bổ sung thêm thông tin về tăng trưởng tín dụng.",
            affected_agent="company",
            resolution_status=CritiqueIssueStatus.OPEN,
            required_action=CritiqueAction.REVISE_CLAIM,
        )
        results = format_critic_limitations([issue1])
        self.assertEqual(results, ["Bộ phản biện còn 1 lưu ý chưa xử lý; xem quá trình phân tích."])

    def test_multiple_unhandled_critic_issues_aggregated(self) -> None:
        """Multiple unhandled issues aggregate into a single count notice."""
        issue1 = CritiqueIssue(
            issue_id="issue-1",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            severity=CritiqueSeverity.MINOR,
            description="Câu sent-company-2: Cần bổ sung giải trình biến động.",
            affected_agent="company",
            resolution_status=CritiqueIssueStatus.OPEN,
            required_action=CritiqueAction.REVISE_CLAIM,
        )
        issue2 = CritiqueIssue(
            issue_id="issue-2",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            severity=CritiqueSeverity.MINOR,
            description="Câu sent-company-3: Cần kiểm tra lại trích dẫn số liệu.",
            affected_agent="company",
            resolution_status=CritiqueIssueStatus.OPEN,
            required_action=CritiqueAction.REVISE_CLAIM,
        )
        results = format_critic_limitations([issue1, issue2])
        self.assertEqual(results, ["Bộ phản biện còn 2 lưu ý chưa xử lý; xem quá trình phân tích."])

    def test_clean_limitation_preserved(self) -> None:
        """Legitimate domain limitations without internal codes or directives are preserved."""
        desc = "Dữ liệu biên lãi thuần (NIM) chưa bao gồm các khoản phí dịch vụ đi kèm."
        formatted = _format_single_critic_limitation(desc)
        self.assertEqual(formatted, "Dữ liệu biên lãi thuần (NIM) chưa bao gồm các khoản phí dịch vụ đi kèm.")

    def test_clean_reader_facing_limitations_sanitizer(self) -> None:
        """The defensive cleaner removes sent-*, fact:*, and raw writer directives."""
        lims = [
            "Các nhận định không có đoạn trích tài liệu đã duyệt theo chỉ tiêu sẽ dựa trên định vị nguồn sơ cấp và mã băm nguồn của quan sát được chấp nhận.",
            "Câu sent-company-7: trung vị ngành (peer median) ROE Q4/2024 chỉ có 1 quan sát. Cần bổ sung lưu ý.",
            "Loại bỏ dữ liệu fact:value:ACB:2024_Q4:bank.npl_g35 do thiếu dữ liệu gốc kiểm định.",
            "Góp ý phản biện chưa xử lý (mức nhẹ): Câu sent-company-3 cần bổ sung bối cảnh.",
        ]
        cleaned = clean_reader_facing_limitations(lims)
        # Verify no sent-*, fact:*, or "Cần bổ sung" leaks
        for item in cleaned:
            self.assertNotIn("sent-", item)
            self.assertNotIn("fact:", item)
            self.assertNotIn("Cần bổ sung", item)
            self.assertNotIn("peer median", item)

        self.assertIn(
            "Trung vị ngành cho ROE quý 4/2024 chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo.",
            cleaned,
        )
        self.assertIn("Bộ phản biện còn 1 lưu ý chưa xử lý; xem quá trình phân tích.", cleaned)
        self.assertIn("Loại bỏ dữ liệu chỉ tiêu do thiếu dữ liệu gốc kiểm định.", cleaned)


if __name__ == "__main__":
    unittest.main()
