import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PageImageViewer } from '@/features/ingest/components/PageImageViewer';
import { clearPageImageCache } from '@/features/ingest/model/pageImageCache';
import * as apiClient from '@/shared/api/apiClient';

describe('PageImageViewer', () => {
  const dummyBlob = new Blob(['dummy-png-data'], { type: 'image/png' });
  let createObjectURLSpy: ReturnType<typeof vi.fn>;
  let revokeObjectURLSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    clearPageImageCache();

    let id = 1;
    createObjectURLSpy = vi.fn(() => `blob:http://localhost/mock-uuid-${id++}`);
    revokeObjectURLSpy = vi.fn();
    window.URL.createObjectURL = createObjectURLSpy as unknown as typeof window.URL.createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURLSpy as unknown as typeof window.URL.revokeObjectURL;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearPageImageCache();
  });

  it('renders placeholder when pageNumber is null', () => {
    render(<PageImageViewer filingId="fl-123" pageNumber={null} />);

    expect(screen.getByText('Chưa chọn trang để xem')).toBeInTheDocument();
    expect(screen.getByText(/Nhấn vào số trang ở bảng số liệu/)).toBeInTheDocument();
  });

  it('fetches image through apiFetch, creates object URL and renders the image on success', async () => {
    const apiFetchSpy = vi.spyOn(apiClient, 'apiFetch').mockResolvedValue(
      new Response(dummyBlob, {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      })
    );

    render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    // Initially shows loading state
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Đang tải ảnh trang 7…')).toBeInTheDocument();

    // After resolution:
    await waitFor(() => {
      const img = screen.getByRole('img', { name: 'Ảnh trang 7 báo cáo tài chính' });
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'blob:http://localhost/mock-uuid-1');
    });

    expect(apiFetchSpy).toHaveBeenCalledTimes(1);
    expect(apiFetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/api/onboarding/filings/fl-123/pages/7.png')
    );
    expect(createObjectURLSpy).toHaveBeenCalledWith(dummyBlob);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows error text with retry button on 401 response and recovers on retry', async () => {
    const apiFetchSpy = vi.spyOn(apiClient, 'apiFetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    await waitFor(() => {
      expect(screen.getByText('Không tải được ảnh trang 7')).toBeInTheDocument();
    });

    expect(screen.getByText(/Tệp ảnh trang có thể chưa được kết xuất hoặc máy chủ đang xử lý/)).toBeInTheDocument();
    const retryBtn = screen.getByRole('button', { name: /Thử tải lại/ });
    expect(retryBtn).toBeInTheDocument();

    // Now make apiFetch succeed on retry
    apiFetchSpy.mockResolvedValueOnce(
      new Response(dummyBlob, {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      })
    );

    await userEvent.click(retryBtn);

    await waitFor(() => {
      const img = screen.getByRole('img', { name: 'Ảnh trang 7 báo cáo tài chính' });
      expect(img).toBeInTheDocument();
    });

    expect(apiFetchSpy).toHaveBeenCalledTimes(2);
  });

  it('shows error text with retry button on 500 server error', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Internal Server Error' }), {
        status: 500,
      })
    );

    render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    await waitFor(() => {
      expect(screen.getByText('Không tải được ảnh trang 7')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Thử tải lại/ })).toBeInTheDocument();
  });

  it('shows error text with retry button on network failure', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockRejectedValueOnce(new Error('Network error'));

    render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    await waitFor(() => {
      expect(screen.getByText('Không tải được ảnh trang 7')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Thử tải lại/ })).toBeInTheDocument();
  });

  it('revokes the created object URL on unmount', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockResolvedValue(
      new Response(dummyBlob, {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      })
    );

    const { unmount } = render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    await waitFor(() => {
      expect(screen.getByRole('img')).toBeInTheDocument();
    });

    expect(revokeObjectURLSpy).not.toHaveBeenCalled();

    unmount();

    expect(revokeObjectURLSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:http://localhost/mock-uuid-1');
  });

  it('revokes the previous object URL when changing pageNumber', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockResolvedValue(
      new Response(dummyBlob, {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      })
    );

    const { rerender } = render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    await waitFor(() => {
      expect(screen.getByRole('img', { name: 'Ảnh trang 7 báo cáo tài chính' })).toBeInTheDocument();
    });

    rerender(<PageImageViewer filingId="fl-123" pageNumber={8} />);

    // Page 7's object URL must be revoked
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:http://localhost/mock-uuid-1');

    await waitFor(() => {
      expect(screen.getByRole('img', { name: 'Ảnh trang 8 báo cáo tài chính' })).toBeInTheDocument();
    });
  });

  it('caches the image blob so reopening the same page is instant and does not refetch', async () => {
    const apiFetchSpy = vi.spyOn(apiClient, 'apiFetch').mockResolvedValue(
      new Response(dummyBlob, {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      })
    );

    const { unmount } = render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    await waitFor(() => {
      expect(screen.getByRole('img')).toBeInTheDocument();
    });

    expect(apiFetchSpy).toHaveBeenCalledTimes(1);
    unmount();

    // Reopen same filing and page
    render(<PageImageViewer filingId="fl-123" pageNumber={7} />);

    // Instantly available without second fetch
    await waitFor(() => {
      expect(screen.getByRole('img', { name: 'Ảnh trang 7 báo cáo tài chính' })).toBeInTheDocument();
    });
    expect(apiFetchSpy).toHaveBeenCalledTimes(1);
  });

  it('supports zoom controls and close button', async () => {
    vi.spyOn(apiClient, 'apiFetch').mockResolvedValue(
      new Response(dummyBlob, {
        status: 200,
      })
    );
    const onClose = vi.fn();

    render(<PageImageViewer filingId="fl-123" pageNumber={7} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByRole('img')).toBeInTheDocument();
    });

    expect(screen.getByText('100%')).toBeInTheDocument();

    const zoomInBtn = screen.getByRole('button', { name: 'Phóng to ảnh' });
    await userEvent.click(zoomInBtn);
    expect(screen.getByText('125%')).toBeInTheDocument();

    const zoomOutBtn = screen.getByRole('button', { name: 'Thu nhỏ ảnh' });
    await userEvent.click(zoomOutBtn);
    expect(screen.getByText('100%')).toBeInTheDocument();

    const closeBtn = screen.getByRole('button', { name: 'Đóng khung xem ảnh' });
    await userEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
