import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { DataPage } from '../src/pages/data/DataPage';

function renderDataPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MemoryRouter initialEntries={['/data']}><QueryClientProvider client={client}><DataPage /></QueryClientProvider></MemoryRouter>);
}

describe('DataPage', () => {
  it('shows the active validated dataset and distinct source groups', async () => {
    renderDataPage();

    expect(await screen.findByRole('heading', { name: 'Dữ liệu phân tích' })).toBeInTheDocument();
    expect(screen.getByText('Ngân hàng Việt Nam 2024')).toBeInTheDocument();
    expect(screen.getByText('Sẵn sàng')).toBeInTheDocument();
    expect(screen.getByText('Dữ liệu tài chính ngân hàng')).toBeInTheDocument();
    expect(screen.getByText('Báo cáo & tài liệu nguồn')).toBeInTheDocument();
    expect(document.body).toHaveTextContent('17 tài liệu');
  });

  it('opens and completes the four-step add-source prototype flow', async () => {
    const user = userEvent.setup();
    renderDataPage();

    await user.click(await screen.findByRole('button', { name: /Thêm nguồn dữ liệu/ }));
    expect(screen.getByRole('dialog', { name: 'Thêm nguồn dữ liệu' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Chọn loại nguồn dữ liệu' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Tiếp tục/ }));
    expect(screen.getByRole('heading', { name: 'Nhận diện dữ liệu' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Điều chỉnh mapping' }));
    expect(screen.getByLabelText('Điều chỉnh mapping cho Unnamed_12')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Tiếp tục/ }));
    expect(screen.getByRole('heading', { name: 'Kiểm tra dữ liệu' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Tìm hiểu 4 cảnh báo' }));
    expect(screen.getByText('4 giá trị thiếu chưa được điền tự động.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Tiếp tục/ }));
    expect(screen.getByRole('heading', { name: 'Xác nhận bộ dữ liệu' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Tạo bộ dữ liệu' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Đã tạo bộ dữ liệu');
  });
});
