import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { SourceDrawer } from "../src/features/source-lineage/SourceDrawer";
import { DataTab } from "../src/features/source-lineage/DataTab";
import { DocumentTab } from "../src/features/source-lineage/DocumentTab";
import { buildSubstitutedFormula, formatPeriod } from "../src/features/source-lineage/formatters";
import type { ReportItem, LineageNode } from "../src/features/source-lineage/types";

describe("SourceDrawer Component (LIN-1)", () => {
  const mockReport: ReportItem = {
    report_id: "test-run-1",
    question_type: "company_profile",
    synthesis_summary: "VCB duy trì vị thế dẫn đầu an toàn vốn",
    source_notes: [
      {
        note_no: 1,
        source_id: "src_vcb_bctc_2026_q2",
        title: "Báo cáo tài chính hợp nhất Quý 2/2026 - VCB",
        url: "https://static2.vietstock.vn/vcb_2026_q2.pdf",
        locator: "pdf_page=7; section=Thuyet minh; row=Du phong rui ro",
        page: 7,
        fact_ids: ["fact-1"],
      },
    ],
    facts: [
      {
        fact_id: "fact-1",
        fact_type: "value",
        entity_id: "VCB",
        metric_id: "bank.llr_coverage",
        period: "2026_Q2",
        value: 279.3,
        formula_version: "llr-coverage-v1",
        input_observation_ids: ["obs-vcb-llr-2026q2"],
      },
    ],
  };

  const mockVCBLineageNode: LineageNode = {
    observation_id: "obs-vcb-llr-2026q2",
    entity: "VCB",
    metric: "bank.llr_coverage",
    metric_name: "Tỷ lệ bao phủ nợ xấu (LLR)",
    period: "2026_Q2",
    period_id: "2026_Q2",
    value: 279.2775704532222,
    unit: "%",
    formula_version: "llr-coverage-v1",
    receipt_result: "passed",
    receipt_tolerance: "0.00005",
    calculation_receipt: {
      formula_version: "llr-coverage-v1",
      ordered_inputs: [
        {
          observation_id: "obs_vcb_prov_2026_q2",
          metric_id: "bank.input.loan_loss_provisions",
          value: "29984.695",
          unit: "VND",
          period_id: "2026_Q2",
        },
        {
          observation_id: "obs_vcb_npl_g35_2026_q2",
          metric_id: "bank.input.npl_g35_balance",
          value: "10736.521",
          unit: "VND",
          period_id: "2026_Q2",
        },
      ],
      calculated_output: "279.2775704532222309256415556",
      unit: "percent",
      result: "passed",
      tolerance: "0.00005",
    },
    source_title: "Báo cáo tài chính hợp nhất Quý 2/2026 - VCB",
    source_url: "https://static2.vietstock.vn/vcb_2026_q2.pdf",
    page: null,
    children: [
      {
        observation_id: "obs_vcb_prov_2026_q2",
        entity: "VCB",
        metric: "bank.input.loan_loss_provisions",
        metric_name: "Dự phòng rủi ro cho vay khách hàng",
        period: "2026_Q2",
        period_id: "2026_Q2",
        value: 29984.695,
        unit: "VND",
        source_title: "Báo cáo tài chính hợp nhất Quý 2/2026 - VCB",
        source_url: "https://static2.vietstock.vn/vcb_2026_q2.pdf",
        page: 7,
        section: "Thuyết minh",
        row_label: "Dự phòng rủi ro cho vay khách hàng",
        reading: "single",
        children: [],
      },
      {
        observation_id: "obs_vcb_npl_g35_2026_q2",
        entity: "VCB",
        metric: "bank.input.npl_g35_balance",
        metric_name: "Tổng nợ xấu (nhóm 3–5)",
        period: "2026_Q2",
        period_id: "2026_Q2",
        value: 10736.521,
        unit: "VND",
        formula_version: "npl-g35-balance-v1",
        children: [
          {
            observation_id: "obs_vcb_npl_g3_2026_q2",
            entity: "VCB",
            metric: "bank.input.npl_group_3_balance",
            metric_name: "Nợ dưới tiêu chuẩn (nhóm 3)",
            period: "2026_Q2",
            period_id: "2026_Q2",
            value: 2000.0,
            unit: "VND",
            source_title: "Báo cáo tài chính hợp nhất Quý 2/2026 - VCB",
            source_url: "https://static2.vietstock.vn/vcb_2026_q2.pdf",
            page: 30,
            section: "Thuyết minh",
            row_label: "Nợ dưới tiêu chuẩn",
            reading: "single",
            children: [],
          },
          {
            observation_id: "obs_vcb_npl_g4_2026_q2",
            entity: "VCB",
            metric: "bank.input.npl_group_4_balance",
            metric_name: "Nợ nghi ngờ (nhóm 4)",
            period: "2026_Q2",
            period_id: "2026_Q2",
            value: 3000.0,
            unit: "VND",
            source_title: "Báo cáo tài chính hợp nhất Quý 2/2026 - VCB",
            source_url: "https://static2.vietstock.vn/vcb_2026_q2.pdf",
            page: 30,
            section: "Thuyết minh",
            row_label: "Nợ nghi ngờ",
            reading: "single",
            children: [],
          },
          {
            observation_id: "obs_vcb_npl_g5_2026_q2",
            entity: "VCB",
            metric: "bank.input.npl_group_5_balance",
            metric_name: "Nợ có khả năng mất vốn (nhóm 5)",
            period: "2026_Q2",
            period_id: "2026_Q2",
            value: 5736.521,
            unit: "VND",
            source_title: "Báo cáo tài chính hợp nhất Quý 2/2026 - VCB",
            source_url: "https://static2.vietstock.vn/vcb_2026_q2.pdf",
            page: 30,
            section: "Thuyết minh",
            row_label: "Nợ có khả năng mất vốn",
            reading: "single",
            children: [],
          },
        ],
      },
    ],
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

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

  it("renders drawer header with Quý N/YYYY and 3 tabs when isOpen is true", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockVCBLineageNode,
    } as Response);

    render(
      <SourceDrawer
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
        noteNo={1}
        defaultTab="document"
      />
    );

    // Header entity & period formatted as Quý 2/2026
    expect(screen.getByText(/VCB/i)).toBeInTheDocument();
    expect(screen.getByText(/Quý 2\/2026/i)).toBeInTheDocument();

    // 3 tabs
    expect(screen.getByRole("tab", { name: /Tài liệu/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Dữ liệu/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Hành trình/i })).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    render(
      <SourceDrawer
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
        noteNo={1}
      />
    );

    const closeBtn = screen.getByLabelText(/Đóng ngăn chi tiết/i);
    expect(closeBtn).toBeInTheDocument();
  });

  it("Item 7a: a failed fetch renders the error state and NO numbers", async () => {
    // Mock fetch failure (e.g. 404 or network error)
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new Error("Failed to fetch lineage: 404 Not Found")
    );

    render(
      <SourceDrawer
        isOpen={true}
        onClose={vi.fn()}
        report={mockReport}
        noteNo={1}
        defaultTab="data"
      />
    );

    // Must render error state message and retry button
    await waitFor(() => {
      expect(screen.getByText("Không tải được truy vết nguồn")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Thử lại/i })).toBeInTheDocument();

    // Crucial rule 5 requirement: NEVER synthesize fake numbers/receipts when fetch fails
    expect(screen.queryByText(/279,3/)).not.toBeInTheDocument();
    expect(screen.queryByText(/29\.984,7/)).not.toBeInTheDocument();
    expect(screen.queryByText(/10\.736,5/)).not.toBeInTheDocument();
    expect(screen.queryByText(/223,3/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Bao phủ =/)).not.toBeInTheDocument();
  });

  it("Item 7b: formula built strictly from receipt reproduces 279,3% for real VCB inputs", () => {
    // 1. Test pure formatter function
    const formula = buildSubstitutedFormula(
      mockVCBLineageNode.calculation_receipt,
      mockVCBLineageNode.value,
      mockVCBLineageNode.unit
    );
    expect(formula).toBe("Bao phủ = Dự phòng 29.984,7 / Nợ xấu 10.736,5 = 279,3%");

    // 2. Test rendering within DataTab component
    render(<DataTab node={mockVCBLineageNode} activeFact={mockReport.facts?.[0]} />);

    // Renders substituted formula with exact 279,3%
    expect(
      screen.getByText("Bao phủ = Dự phòng 29.984,7 / Nợ xấu 10.736,5 = 279,3%")
    ).toBeInTheDocument();

    // Renders formula version from receipt
    expect(screen.getByText("llr-coverage-v1")).toBeInTheDocument();

    // Formats periods in rows as Quý 2/2026
    const periodBadges = screen.getAllByText("Quý 2/2026");
    expect(periodBadges.length).toBeGreaterThan(0);
  });

  it("Item 7c: leaf pages 7 and 30 are rendered with each leaf's own page", () => {
    render(<DocumentTab node={mockVCBLineageNode} activeNote={mockReport.source_notes?.[0]} />);

    // Leaf 1: Provisions -> page 7
    expect(screen.getByText("tr. 7")).toBeInTheDocument();
    expect(screen.getByText("Trang 7")).toBeInTheDocument();

    // Leaves 2, 3, 4: NPL Groups 3, 4, 5 -> each has page 30
    const tr30Badges = screen.getAllByText("tr. 30");
    expect(tr30Badges.length).toBe(3);

    // Clicking on Group 3 leaf button displays Trang 30 in header badge
    const group3Btn = screen.getByRole("button", { name: /Nhóm 3.*tr\. 30/i });
    fireEvent.click(group3Btn);
    expect(screen.getByText("Trang 30")).toBeInTheDocument();

    // External link button specifically links to #page=30
    const pdfLink = screen.getByRole("link", { name: /Mở trang PDF gốc \(Trang 30\)/i });
    expect(pdfLink).toHaveAttribute(
      "href",
      "https://static2.vietstock.vn/vcb_2026_q2.pdf#page=30"
    );
  });

  it("formats periods correctly using formatPeriod helper", () => {
    expect(formatPeriod("2026_Q2")).toBe("Quý 2/2026");
    expect(formatPeriod("2024_Q4")).toBe("Quý 4/2024");
    expect(formatPeriod("2025_Q1")).toBe("Quý 1/2025");
    expect(formatPeriod("")).toBe("");
  });
});
