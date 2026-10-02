import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BankUploadSection } from '../src/features/onboarding/BankUploadSection';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';

describe('BankUploadSection and Upload Analysis Flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(mockCapabilities);
  });

  it('renders download links and upload dropzone correctly', () => {
    render(
      <MemoryRouter>
        <BankUploadSection />
      </MemoryRouter>
    );

    expect(screen.getByText('Thêm ngân hàng mới từ tệp CSV')).toBeInTheDocument();
    expect(screen.getByText('Tải file mẫu (.csv)')).toHaveAttribute('href', expect.stringContaining('/api/onboarding/template.csv'));
    expect(screen.getByText('Mẫu VIB 2025 hợp lệ')).toHaveAttribute('href', expect.stringContaining('/api/onboarding/samples/vib-2025q4.csv'));
    expect(screen.getByText(/Mẫu VIB có lỗi/)).toHaveAttribute('href', expect.stringContaining('/api/onboarding/samples/vib-2025q4-loi.csv'));
    expect(screen.getByRole('button', { name: 'Kiểm tra và tải lên' })).toBeDisabled();
  });

  it('handles successful CSV upload and displays 4 recomputed metrics table', async () => {
    const mockUploadResponse = {
      upload_id: 'upl-test-12345678',
      entity_id: 'CTG',
      display_name: 'Ngân hàng TMCP Công Thương Việt Nam',
      period_id: '2024_Q4',
      status: 'accepted',
      metrics: [
        { metric_id: 'bank.npl_g35', computed_value: 1.13, reported_value: 1.13, status: 'matched' },
        { metric_id: 'bank.llr_coverage', computed_value: 170.52, reported_value: 170.52, status: 'matched' },
        { metric_id: 'bank.roa', computed_value: 1.34, reported_value: 1.34, status: 'matched' },
        { metric_id: 'bank.roe', computed_value: 16.78, reported_value: 16.78, status: 'matched' },
      ],
      row_issues: [],
      limitations_vi:
        'Số liệu CTG do người dùng cung cấp; hệ thống đã kiểm tra cấu trúc, nguồn và tính lại chỉ tiêu, chưa được duyệt độc lập như bộ Gold.',
      created_at: new Date().toISOString(),
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockUploadResponse,
    } as unknown as Response);

    render(
      <MemoryRouter>
        <BankUploadSection />
      </MemoryRouter>
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const testFile = new File(['dummy,csv,content'], 'ctg-2024q4.csv', { type: 'text/csv' });
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    expect(screen.getByText('ctg-2024q4.csv')).toBeInTheDocument();
    const submitBtn = screen.getByRole('button', { name: 'Kiểm tra và tải lên' });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Đã xác thực và chấp nhận: CTG \(2024_Q4\)/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Tỷ lệ nợ xấu \(NPL nhóm 3–5\)/)).toBeInTheDocument();
    expect(screen.getByText(/Tỷ lệ bao phủ nợ xấu \(LLR\)/)).toBeInTheDocument();
    expect(screen.getByText(/Tỷ suất sinh lời trên tài sản \(ROA\)/)).toBeInTheDocument();
    expect(screen.getByText(/Tỷ suất sinh lời trên vốn CSH \(ROE\)/)).toBeInTheDocument();
    expect(screen.getByText(/Số liệu CTG do người dùng cung cấp/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Hỏi về CTG' })).toBeInTheDocument();
    expect(screen.getByText('Tỷ lệ nợ xấu của CTG quý 4/2024 là bao nhiêu?')).toBeInTheDocument();
  });

  it('renders accepted result with bank name, four metrics, and string limitation without crashing (UPFIX-1)', async () => {
    const vibUploadResponse = {
      upload_id: 'upl-vib-2025q4-staging',
      entity_id: 'VIB',
      display_name: 'Ngân hàng TMCP Quốc tế Việt Nam',
      period_id: '2025_Q4',
      status: 'accepted',
      metrics: [
        { metric_id: 'bank.npl_g35', computed_value: 2.35, reported_value: 2.35, status: 'matched' },
        { metric_id: 'bank.llr_coverage', computed_value: 125.4, reported_value: 125.4, status: 'matched' },
        { metric_id: 'bank.roa', computed_value: 1.82, reported_value: 1.82, status: 'matched' },
        { metric_id: 'bank.roe', computed_value: 19.45, reported_value: 19.45, status: 'matched' },
      ],
      row_issues: [],
      limitations_vi:
        'Dữ liệu VIB 2025_Q4 do người dùng tải lên, chỉ phục vụ mục đích thử nghiệm và so sánh độc lập.',
      created_at: '2026-10-02T08:00:00Z',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => vibUploadResponse,
    } as unknown as Response);

    render(
      <MemoryRouter>
        <BankUploadSection />
      </MemoryRouter>
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const testFile = new File(['dummy,vib,csv'], 'vib-2025q4.csv', { type: 'text/csv' });
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    fireEvent.click(screen.getByRole('button', { name: 'Kiểm tra và tải lên' }));

    await waitFor(() => {
      expect(screen.getByText(/Đã xác thực và chấp nhận: VIB \(2025_Q4\)/)).toBeInTheDocument();
    });

    // Bank name (display_name and entity_id)
    expect(screen.getByText('Ngân hàng TMCP Quốc tế Việt Nam')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Hỏi về VIB' })).toBeInTheDocument();

    // Four metrics
    expect(screen.getByText(/Tỷ lệ nợ xấu \(NPL nhóm 3–5\)/)).toBeInTheDocument();
    expect(screen.getByText(/Tỷ lệ bao phủ nợ xấu \(LLR\)/)).toBeInTheDocument();
    expect(screen.getByText(/Tỷ suất sinh lời trên tài sản \(ROA\)/)).toBeInTheDocument();
    expect(screen.getByText(/Tỷ suất sinh lời trên vốn CSH \(ROE\)/)).toBeInTheDocument();

    // Limitation text
    expect(
      screen.getByText('Dữ liệu VIB 2025_Q4 do người dùng tải lên, chỉ phục vụ mục đích thử nghiệm và so sánh độc lập.')
    ).toBeInTheDocument();
  });

  it('handles rejected CSV upload and renders row issues in Vietnamese', async () => {
    const mockRejectedResponse = {
      upload_id: 'upl-err-87654321',
      entity_id: 'CTG',
      display_name: 'Ngân hàng TMCP Công Thương Việt Nam',
      period_id: '2024_Q4',
      status: 'rejected',
      metrics: [],
      row_issues: [
        { row: 7, field: 'source_locator', message_vi: 'Thiếu thông tin trang hoặc định vị báo cáo tài chính' },
        { row: 12, field: 'unit', message_vi: 'Đơn vị đo VND không hợp lệ cho chỉ tiêu tỷ lệ' },
        { row: 19, field: 'reported_value', message_vi: 'Giá trị công bố 1.50 lệch dung sai so với giá trị tính lại 1.13' },
      ],
      limitations_vi: '',
      created_at: new Date().toISOString(),
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockRejectedResponse,
    } as unknown as Response);

    render(
      <MemoryRouter>
        <BankUploadSection />
      </MemoryRouter>
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const testFile = new File(['err,csv,content'], 'ctg-error.csv', { type: 'text/csv' });
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    fireEvent.click(screen.getByRole('button', { name: 'Kiểm tra và tải lên' }));

    await waitFor(() => {
      expect(screen.getByText(/Từ chối tiếp nhận tệp: CTG/)).toBeInTheDocument();
    });

    expect(screen.getByText('Thiếu thông tin trang hoặc định vị báo cáo tài chính')).toBeInTheDocument();
    expect(screen.getByText('Đơn vị đo VND không hợp lệ cho chỉ tiêu tỷ lệ')).toBeInTheDocument();
    expect(screen.getByText(/Giá trị công bố 1.50 lệch dung sai/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Hỏi về CTG' })).not.toBeInTheDocument();
  });

  it('CreateAnalysisPage renders active upload chip and clears it on dismiss', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter initialEntries={['/analysis?upload_id=upl-test-123&entity=CTG&period=2024_Q4']}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/analysis" element={<CreateAnalysisPage />} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>
    );

    const chip = await screen.findByText(/Đang dùng thêm dữ liệu tải lên:/);
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveTextContent('CTG');
    expect(chip).toHaveTextContent('Q4/2024');
    expect(screen.getByText('Gợi ý cho CTG')).toBeInTheDocument();

    const clearBtn = screen.getByRole('button', { name: 'Bỏ chọn dữ liệu tải lên' });
    fireEvent.click(clearBtn);

    await waitFor(() => {
      expect(screen.queryByText(/Đang dùng thêm dữ liệu tải lên:/)).not.toBeInTheDocument();
    });
  });
});
