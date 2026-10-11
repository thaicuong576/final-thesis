import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SourceDrawer } from "../src/features/source-lineage/SourceDrawer";
import type { ReportItem } from "../src/features/source-lineage/types";

describe("SourceDrawer Component (LIN-1)", () => {
  const mockReport: ReportItem = {
    report_id: "test-run-1",
    question_type: "company_profile",
    synthesis_summary: "VCB duy trì vị thế dẫn đầu an toàn vốn",
    source_notes: [
      {
        note_no: 1,
        source_id: "src_vcb_bctc_2024_q4",
        title: "Báo cáo tài chính hợp nhất Quý 4/2024 - VCB",
        url: "https://static2.vietstock.vn/vcb_2024_q4.pdf",
        locator: "pdf_page=7; section=Thuyet minh; row=Du phong rui ro",
        page: 7,
        fact_ids: ["fact-1"],
      },
    ],
    facts: [
      {
        fact_id: "fact-1",
        fact_type: "peer_rank",
        entity_id: "VCB",
        metric_id: "bank.llr_coverage",
        period: "2024_Q4",
        value: 1,
        denominator: 5,
        formula_version: "llr-coverage-v1",
        input_observation_ids: ["obs-vcb-llr-2024q4"],
      },
    ],
  };

  it("does not render when isOpen is false", () => {
    const { container } = render(
      <SourceDrawer
        isOpen={false}
        onClose={vi.fn()}
        report={mockReport}
        noteNo={1}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders drawer header and 3 tabs when isOpen is true", () => {
    render(
      <SourceDrawer
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
        noteNo={1}
        defaultTab="document"
      />
    );

    // Header entity
    expect(screen.getByText(/VCB/i)).toBeInTheDocument();
    // 3 tabs
    expect(screen.getByRole("tab", { name: /Tài liệu/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Dữ liệu/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Hành trình/i })).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const handleClose = vi.fn();
    render(
      <SourceDrawer
        isOpen={true}
        onClose={handleClose}
        report={mockReport}
        noteNo={1}
      />
    );

    const closeBtn = screen.getByLabelText(/Đóng ngăn chi tiết/i);
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("switches tabs when tab buttons are clicked", async () => {
    render(
      <SourceDrawer
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
        noteNo={1}
        defaultTab="document"
      />
    );

    // Initial tab: document
    const docTab = screen.getByRole("tab", { name: /Tài liệu/i });
    expect(docTab).toHaveAttribute("aria-selected", "true");

    // Click data tab
    const dataTab = screen.getByRole("tab", { name: /Dữ liệu/i });
    fireEvent.click(dataTab);
    expect(dataTab).toHaveAttribute("aria-selected", "true");

    // Wait for data tab content after async fallback loads
    await waitFor(() => {
      expect(screen.getByText(/Công thức & Số liệu thay thế/i)).toBeInTheDocument();
    });

    // Click journey tab
    const journeyTab = screen.getByRole("tab", { name: /Hành trình/i });
    fireEvent.click(journeyTab);
    expect(journeyTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/Đường dẫn chứng minh liên tục/i)).toBeInTheDocument();
    expect(screen.getByText(/Thẩm định chất lượng \(Verifier\)/i)).toBeInTheDocument();
  });
});
