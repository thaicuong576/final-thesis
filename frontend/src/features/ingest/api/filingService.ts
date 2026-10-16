/**
 * API service for the PDF filing ingestion wizard (INGEST-3).
 * Calls endpoints defined in CONTRACT.md 2026-10-16.
 * All calls go through apiFetch which handles Bearer auth and 401 handling.
 */

import { apiFetch } from '@/shared/api/apiClient';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';
import type {
  ConfirmResult,
  Filing,
  FilingSample,
  FilingSummary,
  PutRowBody,
} from '../model/types';

function apiUrl(path: string): string {
  const base = getApiBaseUrl();
  return `${base}${path}`;
}

/** POST /api/onboarding/filings — upload a PDF and start processing. */
export async function createFiling(
  file: File,
  params: {
    entity_id: string;
    fiscal_year: number;
    reporting_scope: 'consolidated' | 'separate';
    display_name?: string;
  }
): Promise<{ filing_id: string; status: 'processing' }> {
  const form = new FormData();
  form.append('file', file);
  form.append('entity_id', params.entity_id);
  form.append('fiscal_year', String(params.fiscal_year));
  form.append('reporting_scope', params.reporting_scope);
  if (params.display_name) form.append('display_name', params.display_name);

  const res = await apiFetch(apiUrl('/api/onboarding/filings'), {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Lỗi ${res.status}` }));
    const detail = err?.detail;
    const msg =
      res.status === 413
        ? 'Tệp quá lớn (tối đa 40 MB).'
        : res.status === 400
        ? (typeof detail === 'string' ? detail : 'Đầu vào không hợp lệ.')
        : typeof detail === 'string'
        ? detail
        : `Lỗi ${res.status}`;
    throw new Error(msg);
  }

  return res.json();
}

/** GET /api/onboarding/filings/{filing_id} — poll status. */
export async function getFiling(filingId: string): Promise<Filing> {
  const res = await apiFetch(apiUrl(`/api/onboarding/filings/${filingId}`));
  if (!res.ok) throw new Error(`Không tải được filing ${filingId} (HTTP ${res.status})`);
  return res.json();
}

/** GET /api/onboarding/filings — recent list. */
export async function listFilings(): Promise<FilingSummary[]> {
  const res = await apiFetch(apiUrl('/api/onboarding/filings'));
  if (!res.ok) throw new Error(`Lỗi tải danh sách (HTTP ${res.status})`);
  return res.json();
}

/** PUT /api/onboarding/filings/{filing_id}/rows/{row_id} — edit a row. */
export async function updateRow(
  filingId: string,
  rowId: string,
  body: PutRowBody
): Promise<{ row: Filing['rows'][0]; validation: Filing['validation'] }> {
  const res = await apiFetch(apiUrl(`/api/onboarding/filings/${filingId}/rows/${rowId}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Lỗi cập nhật dòng (HTTP ${res.status})`);
  return res.json();
}

/** POST /api/onboarding/filings/{filing_id}/confirm — finalize. */
export async function confirmFiling(filingId: string): Promise<ConfirmResult> {
  const res = await apiFetch(apiUrl(`/api/onboarding/filings/${filingId}/confirm`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (res.status === 409) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail || 'Chưa thể xác nhận: còn lỗi hoặc dòng chưa được duyệt.');
  }
  if (!res.ok) throw new Error(`Lỗi xác nhận filing (HTTP ${res.status})`);
  return res.json();
}

/** GET /api/onboarding/filing-samples */
export async function listFilingSamples(): Promise<FilingSample[]> {
  const res = await apiFetch(apiUrl('/api/onboarding/filing-samples'));
  if (!res.ok) throw new Error(`Lỗi tải mẫu (HTTP ${res.status})`);
  return res.json();
}

/** POST /api/onboarding/filing-samples/{sample_id}/open */
export async function openFilingSample(sampleId: string): Promise<Filing> {
  const res = await apiFetch(apiUrl(`/api/onboarding/filing-samples/${sampleId}/open`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Lỗi mở mẫu (HTTP ${res.status})`);
  return res.json();
}

/** Build the page image URL (no auth needed, direct img src). */
export function filingPageImageUrl(filingId: string, pageNumber: number): string {
  return apiUrl(`/api/onboarding/filings/${filingId}/pages/${pageNumber}.png`);
}
