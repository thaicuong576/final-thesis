import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { FilingWizard } from '@/features/ingest/components/FilingWizard';
import {
  filingClean,
  filingWithIssues,
  filingProcessing,
  filingFailed,
  FILING_SAMPLES,
} from '@/test/fixtures/filingFixtures';
import * as filingService from '@/features/ingest/api/filingService';

// Mock the filingService
vi.mock('@/features/ingest/api/filingService', () => ({
  createFiling: vi.fn(),
  getFiling: vi.fn(),
  listFilings: vi.fn(),
  updateRow: vi.fn(),
  confirmFiling: vi.fn(),
  listFilingSamples: vi.fn(),
  openFilingSample: vi.fn(),
  filingPageImageUrl: vi.fn((filingId: string, page: number) => `/api/onboarding/filings/${filingId}/pages/${page}.png`),
}));

describe('FilingWizard (INGEST-3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(filingService.listFilingSamples).mockResolvedValue(FILING_SAMPLES);
  });

  it('renders Step 1 (Upload) initially with all required controls', () => {
    render(
      <MemoryRouter>
        <FilingWizard />
      </MemoryRouter>
    );

    expect(screen.getByText('Thêm ngân hàng từ báo cáo tài chính PDF')).toBeInTheDocument();
    expect(screen.getByText('Bước 1: Tải lên tài liệu PDF')).toBeInTheDocument();
    expect(screen.getByText(/Chọn hoặc kéo thả báo cáo tài chính/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Mã ngân hàng/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Năm tài chính/)).toBeInTheDocument();
    expect(screen.getByText(/Phạm vi lập báo cáo/)).toBeInTheDocument();
    expect(screen.getByText('Báo cáo hợp nhất')).toBeInTheDocument();
    expect(screen.getByText('Báo cáo riêng lẻ')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Dùng bộ mẫu dựng sẵn/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bắt đầu đọc và trích xuất PDF' })).toBeDisabled();
  });

  it('validates mandatory reporting scope and entity code before upload', async () => {
    render(
      <MemoryRouter>
        <FilingWizard />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: 'Bắt đầu đọc và trích xuất PDF' });
    expect(submitBtn).toBeDisabled();

    // Select a file
    const file = new File(['%PDF-1.4 dummy'], 'ACB_FY2025.pdf', { type: 'application/pdf' });
    const fileInput = screen.getByLabelText('Tải lên tệp PDF');
    await userEvent.upload(fileInput, file);

    // Entity ID auto-extracted as "ACB", but scope not selected yet -> still disabled
    expect(submitBtn).toBeDisabled();

    // Select reporting scope
    const consolidatedRadio = screen.getByRole('radio', { name: /Báo cáo hợp nhất/ });
    await userEvent.click(consolidatedRadio);

    // Now enabled
    expect(submitBtn).toBeEnabled();
  });

  it('displays processing state with progress bar when status is processing', () => {
    render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingProcessing} />
      </MemoryRouter>
    );

    expect(screen.getByText('Bước 2: Đang đọc và quét OCR')).toBeInTheDocument();
    expect(screen.getByText('Đang đọc và trích xuất báo cáo tài chính')).toBeInTheDocument();
    expect(screen.getByText('Đang đọc trang 37/120')).toBeInTheDocument();

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '31');
  });

  it('displays failed state with error message and resolution advice', () => {
    render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingFailed} />
      </MemoryRouter>
    );

    expect(screen.getByTestId('processing-failed')).toBeInTheDocument();
    expect(screen.getByText(/Máy chủ chưa cài công cụ OCR/)).toBeInTheDocument();
    expect(screen.getByText(/Hướng xử lý khuyến nghị:/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Dùng bộ mẫu dựng sẵn để trình diễn/ })).toBeInTheDocument();
  });

  it('renders ready filing with statement pages, extracted rows table, and validation panel', () => {
    render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingClean} />
      </MemoryRouter>
    );

    // Step 2: Statement pages
    expect(screen.getByText(/Các trang báo cáo nhận diện được/)).toBeInTheDocument();
    expect(screen.getByText('Bảng cân đối kế toán:')).toBeInTheDocument();
    expect(screen.getByText('Kết quả kinh doanh:')).toBeInTheDocument();
    expect(screen.getByText('Thuyết minh chất lượng nợ:')).toBeInTheDocument();

    // Step 3: Extracted rows table
    expect(screen.getByTestId('extracted-rows-section')).toBeInTheDocument();
    expect(screen.getAllByText('Nợ nhóm 3')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Nợ nhóm 4')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Nợ nhóm 5')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Dư nợ cho vay gộp')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Tổng tài sản')[0]).toBeInTheDocument();

    // Step 4: Validation panel
    expect(screen.getByTestId('validation-panel')).toBeInTheDocument();
    expect(screen.getByText('Đạt chuẩn xác nhận')).toBeInTheDocument();

    // Step 5: Confirmation
    expect(screen.getByTestId('ready-to-confirm-box')).toBeInTheDocument();
    const confirmBtn = screen.getByTestId('confirm-filing-button');
    expect(confirmBtn).toBeEnabled();
  });

  it('disables confirmation button and shows blocking reasons when filing has issues', () => {
    render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingWithIssues} />
      </MemoryRouter>
    );

    const confirmBtn = screen.getByTestId('confirm-filing-button');
    expect(confirmBtn).toBeDisabled();

    expect(screen.getByText('Chưa đủ điều kiện xác nhận')).toBeInTheDocument();
    expect(screen.getByText('Lý do chưa thể nhập vào hệ thống:')).toBeInTheDocument();
    expect(screen.getByText('Còn 1 dòng thiếu cần nhập thủ công.')).toBeInTheDocument();
  });

  it('allows editing a row value and shows "Đã sửa" badge with original value', async () => {
    const updatedRow = {
      ...filingWithIssues.rows[0],
      value_billion_vnd: '800.000',
      edited: true,
      confirmed: true,
      extracted_value_billion_vnd: '764.791',
    };

    vi.mocked(filingService.updateRow).mockResolvedValue({
      row: updatedRow,
      validation: {
        ...filingWithIssues.validation,
        ready_to_confirm: false,
      },
    });

    render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingWithIssues} />
      </MemoryRouter>
    );

    // Find the edit button for the first target cell (use getAllBy because of desktop table + mobile card responsive views)
    const editBtns = screen.getAllByLabelText(`Sửa giá trị ${filingWithIssues.rows[0].row_id}`);
    await userEvent.click(editBtns[0]);

    const inputs = screen.getAllByLabelText('Nhập số tiền tỷ đồng');
    await userEvent.clear(inputs[0]);
    await userEvent.type(inputs[0], '800.000');

    const saveBtns = screen.getAllByTitle('Lưu');
    await userEvent.click(saveBtns[0]);

    expect(filingService.updateRow).toHaveBeenCalledWith(
      filingWithIssues.filing_id,
      filingWithIssues.rows[0].row_id,
      { value_billion_vnd: '800.000', confirmed: true }
    );
  });

  it('allows confirming a filing and renders recomputed metrics result', async () => {
    const confirmResult = {
      upload_id: 'up-acb2025001',
      entity_id: 'ACB',
      display_name: 'Ngân hàng Á Châu (ACB)',
      status: 'accepted' as const,
      period_id: '2025_Q4',
      metrics: [
        { metric_id: 'bank.npl_g35', computed_value: 0.99, reported_value: 0.99, status: 'matched' },
        { metric_id: 'bank.llr_coverage', computed_value: 112.5, reported_value: 112.5, status: 'matched' },
        { metric_id: 'bank.roa', computed_value: 1.65, reported_value: 1.65, status: 'matched' },
        { metric_id: 'bank.roe', computed_value: 17.58, reported_value: 17.58, status: 'matched' },
      ],
      row_issues: [],
      limitations_vi: 'Ngân hàng tải lên không được tính vào trung vị nhóm.',
    };

    vi.mocked(filingService.confirmFiling).mockResolvedValue(confirmResult);

    render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingClean} />
      </MemoryRouter>
    );

    const confirmBtn = screen.getByTestId('confirm-filing-button');
    expect(confirmBtn).toBeEnabled();
    await userEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByTestId('confirmation-result-card')).toBeInTheDocument();
    });

    expect(screen.getByText(/Đã nhập thành công vào cơ sở dữ liệu: ACB/)).toBeInTheDocument();
    expect(screen.getAllByText('Tỷ lệ nợ xấu (NPL nhóm 3–5)')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Tỷ lệ bao phủ nợ xấu (LLR)')[0]).toBeInTheDocument();
    expect(screen.getByTestId('ask-about-bank-button')).toBeInTheDocument();
  });

  it('allows opening sample modal and selecting a pre-built sample', async () => {
    vi.mocked(filingService.openFilingSample).mockResolvedValue(filingClean);

    render(
      <MemoryRouter>
        <FilingWizard />
      </MemoryRouter>
    );

    const openSampleBtn = screen.getAllByRole('button', { name: /Dùng bộ mẫu dựng sẵn/ })[0];
    await userEvent.click(openSampleBtn);

    expect(screen.getByTestId('sample-selector-modal')).toBeInTheDocument();
    expect(screen.getByText('ACB 2025 — đọc sạch (mẫu)')).toBeInTheDocument();

    const selectBtns = screen.getAllByRole('button', { name: /Mở mẫu/ });
    await userEvent.click(selectBtns[0]);

    await waitFor(() => {
      expect(screen.queryByTestId('sample-selector-modal')).not.toBeInTheDocument();
    });

    expect(screen.getByTestId('extracted-rows-section')).toBeInTheDocument();
  });

  it('scans rendered DOM text of every wizard step to ensure no snake_case or machine periods leak to readers', async () => {
    const SNAKE_CASE_REGEX = /[a-z]+_[a-z0-9_]+/;
    const MACHINE_PERIOD_REGEX = /\b\d{4}_Q\d\b/;

    const confirmResult = {
      upload_id: 'up-acb2025q4-01',
      entity_id: 'ACB',
      display_name: 'Ngân hàng Á Châu',
      status: 'accepted' as const,
      period_id: '2025_Q4',
      metrics: [
        { metric_id: 'bank.npl_g35', computed_value: 0.99, reported_value: 0.99, status: 'matched' },
        { metric_id: 'bank.llr_coverage', computed_value: 112.5, reported_value: 112.5, status: 'matched' },
        { metric_id: 'bank.roa', computed_value: 1.65, reported_value: 1.65, status: 'matched' },
        { metric_id: 'bank.roe', computed_value: 17.58, reported_value: 17.58, status: 'matched' },
      ],
      row_issues: [],
      limitations_vi: 'Ngân hàng tải lên không được tính vào trung vị nhóm.',
    };

    // Step 1: Upload (initial)
    const { container: c1, unmount: u1 } = render(
      <MemoryRouter>
        <FilingWizard />
      </MemoryRouter>
    );
    expect(c1.textContent).not.toMatch(SNAKE_CASE_REGEX);
    expect(c1.textContent).not.toMatch(MACHINE_PERIOD_REGEX);
    u1();

    // Step 2: Processing
    const { container: c2, unmount: u2 } = render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingProcessing} />
      </MemoryRouter>
    );
    expect(c2.textContent).not.toMatch(SNAKE_CASE_REGEX);
    expect(c2.textContent).not.toMatch(MACHINE_PERIOD_REGEX);
    u2();

    // Step 3: Failed
    const { container: c3, unmount: u3 } = render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingFailed} />
      </MemoryRouter>
    );
    expect(c3.textContent).not.toMatch(SNAKE_CASE_REGEX);
    expect(c3.textContent).not.toMatch(MACHINE_PERIOD_REGEX);
    u3();

    // Step 4: Extracted rows with issues & validation errors
    const { container: c4, unmount: u4 } = render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingWithIssues} />
      </MemoryRouter>
    );
    expect(c4.textContent).not.toMatch(SNAKE_CASE_REGEX);
    expect(c4.textContent).not.toMatch(MACHINE_PERIOD_REGEX);
    u4();

    // Step 5: Clean ready to confirm
    const { container: c5, unmount: u5 } = render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingClean} />
      </MemoryRouter>
    );
    expect(c5.textContent).not.toMatch(SNAKE_CASE_REGEX);
    expect(c5.textContent).not.toMatch(MACHINE_PERIOD_REGEX);
    u5();

    // Step 6: Confirmed result
    vi.mocked(filingService.confirmFiling).mockResolvedValue(confirmResult);
    const { container: c6 } = render(
      <MemoryRouter>
        <FilingWizard initialFiling={filingClean} />
      </MemoryRouter>
    );
    const confirmBtn = screen.getByTestId('confirm-filing-button');
    await userEvent.click(confirmBtn);
    await waitFor(() => {
      expect(screen.getByTestId('confirmation-result-card')).toBeInTheDocument();
    });
    expect(c6.textContent).not.toMatch(SNAKE_CASE_REGEX);
    expect(c6.textContent).not.toMatch(MACHINE_PERIOD_REGEX);
  });
});
