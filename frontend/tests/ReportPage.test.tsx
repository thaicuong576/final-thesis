import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReportPage } from '../src/pages/reports/ReportPage';
import { ReportsListPage } from '../src/pages/reports/ReportsListPage';
import {
  mockPeerComparisonReport,
  mockCompanyOnlyReport,
  mockFullHierarchicalReport
} from '../src/features/analysis-report';
import { OrchestratorThread } from '../src/features/analysis-session/components/OrchestratorThread';

// Unicode Regex detecting all common emojis (Zero Emoji Policy guard)
const EMOJI_REGEX =
  /[\u{1F300}-\u{1F9FF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F1E6}-\u{1F1FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FAFF}]/u;

function renderReportPage(initialRoute = '/reports/acb-tcb-peer', reportOverride = mockPeerComparisonReport) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <QueryClientProvider client={client}>
        <Routes>
          <Route path="/reports" element={<ReportsListPage />} />
          <Route path="/reports/:id" element={<ReportPage report={reportOverride} />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe('Screen 3 - Financial Analysis Report Artifact Page (Clean-Room)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // 1. FULL REPORT: VERIFY RENDERING OF ALL REPORT LAYERS
  // =========================================================================
  it('renders all report layers with full peer comparison mock data', () => {
    const { container } = renderReportPage();

    // Layer 1: Report Sticky Header Bar
    expect(screen.getAllByRole('link', { name: /Thư viện báo cáo/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Mẫu 1: ACB')).toBeInTheDocument();
    expect(screen.getByText('Mẫu 2: ACB vs TCB')).toBeInTheDocument();
    expect(screen.getByText('Mẫu 3: Đa tầng Vĩ mô')).toBeInTheDocument();

    expect(screen.getAllByText('Kiểm tra số học: Đạt').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Phản biện logic: Đạt').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Dữ liệu Q4/2024')).toBeInTheDocument();
    expect(screen.getByText(/Mục tiêu: ACB/i)).toBeInTheDocument();
    expect(screen.getByText(/Đối chuẩn: TCB/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sao chép liên kết/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xuất báo cáo/i })).toBeInTheDocument();

    // Layer 2: Analysis Plan & Capability Banner
    expect(screen.getByText('Kế hoạch phân tích')).toBeInTheDocument();
    expect(screen.getByText(/Phân tích sức khỏe tài chính doanh nghiệp/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Đối chuẩn trung vị ngành/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Đối chuẩn nhóm ngân hàng tương đồng/i)).toBeInTheDocument();

    // Layer 3: Macro Policy Context (SBV 4.5%, credit growth 15.08%, source citation)
    expect(screen.getByText('Bối cảnh chính sách tiền tệ')).toBeInTheDocument();
    expect(screen.getByText('4.5%')).toBeInTheDocument();
    expect(screen.getByText('15.08%')).toBeInTheDocument();
    expect(screen.getByText(/Định hướng điều hành NHNN 2024/i)).toBeInTheDocument();

    // Layer 4: Sector Benchmark Comparison Matrix (ROE, NIM, NPL, CIR, CASA, CAR, LDR)
    expect(screen.getByText('Đối chuẩn trung vị ngành ngân hàng')).toBeInTheDocument();
    const benchmarkSection = screen.getByText('Đối chuẩn trung vị ngành ngân hàng').closest('section')!;
    expect(within(benchmarkSection).getByText('ROE')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('NIM')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('NPL')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('CIR')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('CASA')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('CAR')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('LDR')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('18.20%')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('3.65%')).toBeInTheDocument();
    expect(within(benchmarkSection).getByText('1.62%')).toBeInTheDocument();

    // Layer 5: Company CAMEL In-depth Breakdown (5 pillars & narratives)
    expect(screen.getByText('Phân tích sức khỏe tài chính 5 trụ cột')).toBeInTheDocument();
    expect(screen.getByText(/Mức độ an toàn vốn/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Chất lượng tài sản/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Hiệu quả quản trị & Vận hành/i)).toBeInTheDocument();
    expect(screen.getByText(/Chất lượng sinh lời/i)).toBeInTheDocument();
    expect(screen.getByText(/Thanh khoản & Cấu trúc vốn/i)).toBeInTheDocument();
    expect(screen.getByText(/ACB đạt tỷ suất ROE 21.4%/i)).toBeInTheDocument();
    expect(screen.getByText(/TCB vượt trội về NIM/i)).toBeInTheDocument();

    // Layer 6: Semantic Critique & Claim Graph
    expect(screen.getByText('Luận điểm phân tích và phản biện')).toBeInTheDocument();
    expect(screen.getByText(/Đánh đổi ROE và Chi phí Hoạt động/i)).toBeInTheDocument();
    expect(screen.getByText(/ROE của ACB năm 2024 đạt 21.4%/i)).toBeInTheDocument();
    expect(screen.getByText(/NIM của TCB năm 2024 đạt 4.15%/i)).toBeInTheDocument();
    expect(screen.getAllByText('#ev-acb-roe-2024').length).toBeGreaterThanOrEqual(1);

    // Layer 7: Evidence Trail & Source Provenance Table
    expect(screen.getByText('Tra cứu bằng chứng và nguồn gốc số liệu')).toBeInTheDocument();
    expect(screen.getByText('ev-acb-roe-2024')).toBeInTheDocument();
    expect(screen.getByText('hash-acb-pl-2024')).toBeInTheDocument();
    expect(screen.getByText('ev-tcb-nim-2024')).toBeInTheDocument();
    expect(screen.getByText('hash-tcb-nim-2024')).toBeInTheDocument();

    // Zero Emoji policy verification
    expect(EMOJI_REGEX.test(container.textContent || '')).toBe(false);
  });

  // =========================================================================
  // 2. QUERY-ADAPTIVE HIDING: MACRO & SECTOR OMITTED WHEN NULL
  // =========================================================================
  it('correctly applies query-adaptive hiding: Macro and Sector sections are completely omitted when null in company-only scenario', () => {
    const { container } = renderReportPage(
      '/reports/acb-solo',
      mockCompanyOnlyReport
    );

    expect(screen.getByText(/Mục tiêu: ACB/i)).toBeInTheDocument();
    expect(screen.queryByText(/Đối chuẩn: TCB/i)).not.toBeInTheDocument();

    // Layer 3 (Macro Context) MUST NOT exist in the DOM
    expect(screen.queryByText('Bối cảnh chính sách tiền tệ')).not.toBeInTheDocument();
    expect(screen.queryByText('MACRO CONTEXT')).not.toBeInTheDocument();

    // Layer 4 (Sector Benchmark Matrix) MUST NOT exist in the DOM
    expect(screen.queryByText('Đối chuẩn trung vị ngành ngân hàng')).not.toBeInTheDocument();
    expect(screen.queryByText('SECTOR BENCHMARK')).not.toBeInTheDocument();

    // Cross-level critique is empty in company-only, so critique header must not appear
    expect(screen.queryByText('Phát hiện phản biện tương quan liên tầng')).not.toBeInTheDocument();

    // Limitations should be visible
    expect(screen.getByText(/Không đối sánh với trung vị ngành vì yêu cầu phân tích độc lập/i)).toBeInTheDocument();

    // Company CAMEL breakdown and Evidence Trail must still be rendered
    expect(screen.getByText('Phân tích sức khỏe tài chính 5 trụ cột')).toBeInTheDocument();
    expect(screen.getByText('Tra cứu bằng chứng và nguồn gốc số liệu')).toBeInTheDocument();
    expect(screen.getByText('ev-acb-npl-2024')).toBeInTheDocument();

    // Zero Emoji policy verification
    expect(EMOJI_REGEX.test(container.textContent || '')).toBe(false);
  });

  // =========================================================================
  // 3. SAMPLE 3: FULL HIERARCHICAL REPORT WITH REVISION STATUS
  // =========================================================================
  it('renders Sample 3 (full hierarchical) with revision indicators and policy transmission claims', () => {
    const { container } = renderReportPage(
      '/reports/full-hierarchical',
      mockFullHierarchicalReport
    );

    expect(screen.getByText('Mẫu 3: Đa tầng Vĩ mô')).toBeInTheDocument();
    expect(screen.getAllByText('Phản biện logic: Đã hiệu đính').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Bối cảnh chính sách tiền tệ')).toBeInTheDocument();
    expect(screen.getByText('Đối chuẩn trung vị ngành ngân hàng')).toBeInTheDocument();
    expect(screen.getByText('Phân tích sức khỏe tài chính 5 trụ cột')).toBeInTheDocument();
    expect(screen.getByText('Luận điểm phân tích và phản biện')).toBeInTheDocument();
    expect(screen.getByText('Tra cứu bằng chứng và nguồn gốc số liệu')).toBeInTheDocument();

    expect(EMOJI_REGEX.test(container.textContent || '')).toBe(false);
  });

  // =========================================================================
  // 4. REPORTS LIST PAGE: TABLE OF 3 SAMPLES AT /reports
  // =========================================================================
  it('renders ReportsListPage with all 3 sample reports in table view', () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <MemoryRouter initialEntries={['/reports']}>
        <QueryClientProvider client={client}>
          <Routes>
            <Route path="/reports" element={<ReportsListPage />} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('THƯ VIỆN BÁO CÁO')).toBeInTheDocument();
    expect(screen.getAllByText('Mẫu 1: ACB độc lập').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Mẫu 2: ACB vs TCB').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Mẫu 3: Đa tầng Vĩ mô kèm hiệu đính').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /Xem báo cáo/i }).length).toBeGreaterThanOrEqual(3);

    expect(EMOJI_REGEX.test(container.textContent || '')).toBe(false);
  });

  // =========================================================================
  // 5. ZERO EMOJI POLICY AUDIT
  // =========================================================================
  it('strictly adheres to Zero Emoji Policy across all rendered text surfaces', () => {
    const { container: fullContainer } = renderReportPage('/reports/acb-tcb-peer', mockPeerComparisonReport);
    expect(EMOJI_REGEX.test(fullContainer.innerHTML)).toBe(false);

    const { container: soloContainer } = renderReportPage('/reports/acb-solo', mockCompanyOnlyReport);
    expect(EMOJI_REGEX.test(soloContainer.innerHTML)).toBe(false);

    const { container: hierContainer } = renderReportPage('/reports/full-hierarchical', mockFullHierarchicalReport);
    expect(EMOJI_REGEX.test(hierContainer.innerHTML)).toBe(false);
  });

  // =========================================================================
  // 6. INTERACTION: COPY LINK AND EXPORT REPORT
  // =========================================================================
  it('supports quick actions: copy link with feedback and export report', async () => {
    const user = userEvent.setup();
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: writeTextMock
      },
      writable: true,
      configurable: true
    });

    renderReportPage();

    const copyBtn = screen.getByRole('button', { name: /Sao chép liên kết/i });
    await user.click(copyBtn);

    expect(writeTextMock).toHaveBeenCalled();
    expect(await screen.findByText('Đã sao chép')).toBeInTheDocument();

    const exportBtn = screen.getByRole('button', { name: /Xuất báo cáo/i });
    expect(exportBtn).toBeInTheDocument();
    await user.click(exportBtn);
  });

  // =========================================================================
  // 7. INTERACTION: EVIDENCE HIGHLIGHT & SEARCH FILTERING
  // =========================================================================
  it('highlights corresponding evidence item when clicking on an evidence ref pill in claim graph and filters table', async () => {
    const user = userEvent.setup();
    renderReportPage();

    // Click evidence pill #ev-acb-roe-2024
    const evidencePill = screen.getByRole('button', { name: '#ev-acb-roe-2024' });
    await user.click(evidencePill);

    // Banner indicates evidence item is in focus
    expect(screen.getByText(/Đang tiêu điểm bằng chứng:/i)).toBeInTheDocument();
    expect(screen.getAllByText('#ev-acb-roe-2024').length).toBeGreaterThanOrEqual(1);

    // Clear focus button
    const clearBtn = screen.getByRole('button', { name: /Xóa chọn/i });
    await user.click(clearBtn);
    expect(screen.queryByText(/Đang tiêu điểm bằng chứng:/i)).not.toBeInTheDocument();

    // Test search filter
    const searchInput = screen.getByPlaceholderText(/Tìm theo chỉ tiêu, tài liệu, mã bằng chứng, hash.../i);
    await user.type(searchInput, 'TCB');

    // Should filter table to show TCB items
    expect(screen.getByText('ev-tcb-nim-2024')).toBeInTheDocument();
    expect(screen.queryByText('ev-acb-roe-2024')).not.toBeInTheDocument();
  });

  // =========================================================================
  // 8. NAVIGATION WIRE: SCREEN 2 CTA ROUTES TO SCREEN 3
  // =========================================================================
  it('wires navigation: clicking "Xem báo cáo phân tích" in OrchestratorThread navigates to /reports/mock-session-2024-acb-tcb', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/analysis']}>
        <Routes>
          <Route
            path="/analysis"
            element={
              <OrchestratorThread
                threadItems={[
                  {
                    id: 'ready-item-1',
                    type: 'REPORT_READY_ACTION',
                    message: 'Báo cáo đã sẵn sàng',
                    occurredAtMs: 1000
                  }
                ]}
                specialistSessions={{}}
                onSelectSpecialist={() => {}}
              />
            }
          />
          <Route
            path="/reports/mock-session-2024-acb-tcb"
            element={<div data-testid="report-page-target">Trang Báo Cáo Phân Tích Chuyên Sâu</div>}
          />
        </Routes>
      </MemoryRouter>
    );

    const ctaButton = screen.getByRole('button', { name: /Xem báo cáo phân tích/i });
    expect(ctaButton).toBeInTheDocument();

    await user.click(ctaButton);

    expect(await screen.findByTestId('report-page-target')).toBeInTheDocument();
  });
});
