import type { Period } from '../../entities/capability/model/types';
import type { MetricPresentation } from '@/features/equity-report/model/types';
import { DEFAULT_METRICS } from './defaultMetrics';

export function formatPeriodLabel(period: Period) {
  return `Q${period.quarter}/${period.year}`;
}

function joinVietnamese(items: string[]) {
  if (items.length <= 1) return items[0] ?? '';
  if (items.length === 2) return items.join(' và ');
  return `${items.slice(0, -1).join(', ')} và ${items.at(-1)}`;
}

export function formatPeriodCollection(periods: Period[]) {
  const groups = new Map<number, number[]>();
  for (const period of periods) {
    const quarters = groups.get(period.year) ?? [];
    quarters.push(period.quarter);
    groups.set(period.year, quarters);
  }

  return [...groups.entries()]
    .sort(([yearA], [yearB]) => yearA - yearB)
    .map(([year, quarters]) => {
      const sortedQuarters = [...new Set(quarters)].sort((quarterA, quarterB) => quarterA - quarterB);
      if (sortedQuarters.length > 1 && sortedQuarters.every((quarter, index) => index === 0 || quarter === sortedQuarters[index - 1] + 1)) {
        return `Q${sortedQuarters[0]}–Q${sortedQuarters.at(-1)}/${year}`;
      }
      return `${joinVietnamese(sortedQuarters.map((quarter) => `Q${quarter}`))}/${year}`;
    })
    .join(' · ');
}

export function formatCapabilityTimestamp(timestamp?: string | null) {
  if (!timestamp) return 'Chưa công bố';
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Ho_Chi_Minh'
  }).format(new Date(timestamp));
}

export function formatGoldVersion(version?: string | null) {
  return version ? `Gold v${version}` : 'Chưa công bố';
}

/**
 * Gracefully formats financial metrics with fallback to 'N/A' when values are null, undefined, or invalid.
 */
export function formatMetric(
  value: number | string | null | undefined,
  digits = 1,
  suffix = '%'
): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return 'N/A';
  }
  return `${Number(value).toFixed(digits)}${suffix}`;
}

export function fmtPct(value: number | string | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return '—';
  }
  const formatted = new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(Number(value));
  return `${formatted}%`;
}

export function fmtPp(value: number | string | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return '—';
  }
  const formatted = new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(Number(value));
  return `${formatted} điểm %`;
}

export function fmtTimes(value: number | string | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return '—';
  }
  const formatted = new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(Number(value));
  return `${formatted} lần`;
}

export function fmtRank(
  rank: number | null | undefined,
  denominator: number | null | undefined
): string {
  if (rank === null || rank === undefined) {
    return '—';
  }
  if (denominator === null || denominator === undefined) {
    return `#${rank}`;
  }
  return `${rank}/${denominator}`;
}

export function fmtPeriod(period: string | null | undefined): string {
  if (!period) return '';
  const p = String(period).trim();
  const m1 = /^(\d{4})_Q([1-4])$/i.exec(p);
  if (m1) return `Quý ${m1[2]}/${m1[1]}`;
  const m2 = /^Q([1-4])_(\d{4})$/i.exec(p);
  if (m2) return `Quý ${m2[1]}/${m2[2]}`;
  const m3 = /^(\d{4})Q([1-4])$/i.exec(p);
  if (m3) return `Quý ${m3[2]}/${m3[1]}`;
  return p;
}

export function formatPeriodCode(period: string | null | undefined): string {
  if (!period) return '';
  const p = String(period).trim();
  const m = /^(\d{4})_Q([1-4])$/i.exec(p);
  if (m) return `Q${m[2]}/${m[1]}`;
  const m2 = /^Q([1-4])_(\d{4})$/i.exec(p);
  if (m2) return `Q${m2[1]}/${m2[2]}`;
  const m3 = /^(\d{4})Q([1-4])$/i.exec(p);
  if (m3) return `Q${m3[2]}/${m3[1]}`;
  return p;
}

export function fmtPeriodRange(periods: string[] | string | null | undefined): string {
  if (!periods) return '';
  if (typeof periods === 'string') {
    const rangeMatch = /^(\d{4})_Q([1-4])_to_(\d{4})_Q([1-4])$/i.exec(periods);
    if (rangeMatch && rangeMatch[1] === rangeMatch[3]) {
      return `Q${rangeMatch[2]}–Q${rangeMatch[4]}/${rangeMatch[1]}`;
    }
    return fmtPeriod(periods);
  }
  if (!Array.isArray(periods) || periods.length === 0) return '';
  if (periods.length === 1) return fmtPeriod(periods[0]);

  const parsed = periods
    .map((p) => {
      const m = /^(\d{4})_Q([1-4])$/i.exec(p);
      return m ? { year: Number(m[1]), quarter: Number(m[2]) } : null;
    })
    .filter((x): x is { year: number; quarter: number } => x !== null);

  if (parsed.length === periods.length) {
    const years = [...new Set(parsed.map((p) => p.year))];
    if (years.length === 1) {
      const quarters = parsed.map((p) => p.quarter).sort((a, b) => a - b);
      return `Q${quarters[0]}–Q${quarters[quarters.length - 1]}/${years[0]}`;
    }
  }

  return periods.map(fmtPeriod).join(' · ');
}

export function niceTicks(min: number, max: number, count = 3): number[] {
  if (min >= max) return [min];
  const range = max - min;
  const rawStep = range / Math.max(1, count - 1);
  let step: number;
  if (Number.isInteger(rawStep) && rawStep > 0 && (rawStep <= 5 || rawStep % 10 === 0)) {
    step = rawStep;
  } else {
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const norm = rawStep / magnitude;
    if (norm <= 1.5) step = 1 * magnitude;
    else if (norm <= 3) step = 2 * magnitude;
    else if (norm <= 7) step = 5 * magnitude;
    else step = 10 * magnitude;
  }

  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const totalTicks = Math.round((end - start) / step);
  const ticks: number[] = [];
  for (let i = 0; i <= totalTicks; i++) {
    const v = start + i * step;
    ticks.push(Number(v.toFixed(6)));
  }
  return ticks;
}

/**
 * Formats a number with Vietnamese locale (comma decimal separator, dot thousands separator).
 */
export function formatDecimalVi(
  val: number | string | null | undefined,
  decimals?: number
): string {
  if (val === null || val === undefined || val === '' || isNaN(Number(val))) {
    return '—';
  }
  const num = Number(val);
  const options: Intl.NumberFormatOptions = {
    useGrouping: true
  };
  if (decimals !== undefined) {
    options.minimumFractionDigits = decimals;
    options.maximumFractionDigits = decimals;
  }
  return new Intl.NumberFormat('vi-VN', options).format(num);
}

/**
 * Sanitizes and formats text displayed to users:
 * - Translates periods from machine format ("2024_Q4") to human format ("Q4/2024")
 * - Translates period ranges ("2024_Q1_to_2024_Q4") to human format ("Q1–Q4/2024")
 * - Maps metric identifiers from metricRegistry / capabilities (e.g. bank.llr_coverage, LLR_COVERAGE)
 * - Translates technical missing reason codes (DATA_UNAVAILABLE -> Chưa có số liệu đã kiểm định)
 * Unmapped tokens are preserved as-is.
 */
export function formatDisplayText(
  text: string | null | undefined,
  metrics?: MetricPresentation[]
): string {
  if (!text) return '';
  let s = String(text);

  // 1. Format range periods: 2024_Q1_to_2024_Q4 -> Q1–Q4/2024
  s = s.replace(/(\d{4})_Q([1-4])_to_(\d{4})_Q([1-4])/gi, (_, y1, q1, y2, q2) => {
    if (y1 === y2) return `Q${q1}–Q${q2}/${y1}`;
    return `Q${q1}/${y1}–Q${q2}/${y2}`;
  });

  // 2. Format quarter periods: 2024_Q4 -> Q4/2024, Q4_2024 -> Q4/2024, 2024_Q -> Q/2024
  s = s.replace(/(\d{4})_Q([0-9]+)/gi, 'Q$2/$1');
  s = s.replace(/Q([0-9]+)_(\d{4})/gi, 'Q$1/$2');
  s = s.replace(/(\d{4})_Q/gi, 'Q/$1');

  // 3. Map metric identifiers from metricRegistry / capabilities
  const metricList = metrics && metrics.length > 0 ? metrics : Object.values(DEFAULT_METRICS);
  for (const m of metricList) {
    if (!m) continue;
    const replacement = m.shortLabel || m.label || m.acronym;
    if (!replacement) continue;

    // Replace m.id (e.g. 'bank.npl_g35', 'bank.llr_coverage')
    if (m.id) {
      const escapedId = m.id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      s = s.replace(new RegExp(`\\b${escapedId}\\b`, 'gi'), replacement);
    }

    // Replace technical acronym (e.g. 'LLR_COVERAGE', 'NPL_G35') if different from replacement
    if (m.acronym && m.acronym.toLowerCase() !== replacement.toLowerCase()) {
      const escapedAcronym = m.acronym.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      s = s.replace(new RegExp(`\\b${escapedAcronym}\\b`, 'gi'), replacement);
    }
  }

  // 4. Missing reason code & technical reason codes
  s = s.replace(/\bDATA_UNAVAILABLE\b/g, 'Chưa có số liệu đã kiểm định');

  return s;
}

/**
 * Humanizes structured machine locator strings into clean, user-friendly labels.
 * E.g. 'pdf_pages:6,8;equity_scope:total_equity_minus_nci;formula:...' -> 'tr. 6, 8'
 */
export function humanizeLocator(raw?: string | null): string {
  if (!raw) return '';
  const text = String(raw).trim();
  if (!text) return '';

  const parts = text.split(';').map((p) => p.trim()).filter(Boolean);
  const kv: Record<string, string> = {};
  for (const part of parts) {
    const idx = part.indexOf(':');
    const eqIdx = part.indexOf('=');
    const splitIdx = idx !== -1 ? idx : eqIdx;
    if (splitIdx !== -1) {
      const k = part.slice(0, splitIdx).trim();
      const v = part.slice(splitIdx + 1).trim();
      kv[k] = v;
    }
  }

  const formatPages = (val: string) =>
    val
      .replace(/_and_/g, ', ')
      .replace(/\|/g, ', ')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .join(', ');

  const tokens: string[] = [];

  // 1. Page
  if (kv.printed_page) {
    tokens.push(`tr. ${formatPages(kv.printed_page)}`);
  } else if (kv.printed_pages) {
    tokens.push(`tr. ${formatPages(kv.printed_pages)}`);
  } else if (kv.page) {
    tokens.push(`tr. ${formatPages(kv.page)}`);
  } else if (kv.pages) {
    tokens.push(`tr. ${formatPages(kv.pages)}`);
  } else if (kv.pdf_page) {
    tokens.push(`tr. ${formatPages(kv.pdf_page)}`);
  } else if (kv.pdf_pages) {
    tokens.push(`tr. ${formatPages(kv.pdf_pages)}`);
  }

  // 2. Section / Statement / Table / Note
  const sec = kv.section || kv.sections;
  if (sec) {
    tokens.push(sec.replace(/_/g, ' ').split('|').map((s) => s.trim()).join(' · '));
  } else if (kv.statement || kv.statements) {
    const stmt = kv.statement || kv.statements || '';
    tokens.push(stmt.replace(/_/g, ' ').split('|').map((s) => s.trim()).join(' · '));
  } else if (kv.table || kv.tables) {
    const tbl = kv.table || kv.tables || '';
    tokens.push(tbl.replace(/_/g, ' ').split('|').map((s) => s.trim()).join(' · '));
  } else if (kv.note || kv.notes) {
    const note = kv.note || kv.notes || '';
    tokens.push(note.replace(/_/g, ' ').split('|').map((s) => s.trim()).join(' · '));
  }

  if (tokens.length > 0) return tokens.join(' · ');
  if (Object.keys(kv).length > 0) return '';
  return text;
}

/**
 * Defensive sanitizer for limitations to ensure reader-facing Vietnamese text without internal technical IDs.
 */
export function cleanReaderLimitations(limitations: string[]): string[] {
  const results: string[] = [];
  let unhandledCount = 0;
  const seen = new Set<string>();

  for (const lim of limitations) {
    if (!lim || !lim.trim()) continue;
    const raw = lim.trim();

    const hasInternalId = /\b(?:sent-[a-zA-Z0-9_-]+|block[ _-]?\d+)\b/i.test(raw);
    const hasWriterCommand = /\b(?:cần bổ sung|cần điều chỉnh|cần diễn đạt|cần kiểm tra|cần lưu ý|đề nghị|khuyến nghị)\b/i.test(raw);
    const isCriticPrefix = /^góp ý phản biện/i.test(raw);

    if (hasInternalId || hasWriterCommand || isCriticPrefix) {
      const isPeerMedian = /(?:trung vị|peer median|peer_median)/i.test(raw);
      const isSingleObs = /(?:1 quan sát|một quan sát|chỉ có 1|chỉ có một|mẫu chỉ có 1|mẫu chỉ có một|đúng giá trị của|duy nhất)/i.test(raw);

      if (isPeerMedian && isSingleObs) {
        let metric = '';
        if (/\broe\b/i.test(raw)) metric = 'ROE';
        else if (/\broa\b/i.test(raw)) metric = 'ROA';
        else if (/\b(?:tỷ lệ nợ xấu|nợ xấu|npl)\b/i.test(raw)) metric = 'tỷ lệ nợ xấu';
        else if (/\b(?:bao phủ|llr)\b/i.test(raw)) metric = 'tỷ lệ bao phủ nợ xấu';
        else if (/\bcasa\b/i.test(raw)) metric = 'tỷ lệ CASA';
        else if (/\bnim\b/i.test(raw)) metric = 'NIM';
        else if (/\bcir\b/i.test(raw)) metric = 'tỷ lệ CIR';
        else if (/\bldr\b/i.test(raw)) metric = 'tỷ lệ LDR';

        let period = '';
        const pMatch = raw.match(/\b(?:quý\s*([1-4])[/_](\d{4})|Q([1-4])[/_](\d{4})|(\d{4})[/_]Q([1-4]))\b/i);
        if (pMatch) {
          const q = pMatch[1] || pMatch[3] || pMatch[6];
          const y = pMatch[2] || pMatch[4] || pMatch[5];
          period = `quý ${q}/${y}`;
        }

        const formatted = metric && period
          ? `Trung vị ngành cho ${metric} ${period} chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo.`
          : metric
          ? `Trung vị ngành cho ${metric} chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo.`
          : period
          ? `Trung vị ngành ${period} chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo.`
          : 'Trung vị ngành chỉ dựa trên 1 quan sát, nên so sánh với trung vị mang tính tham khảo.';

        if (!seen.has(formatted)) {
          seen.add(formatted);
          results.push(formatted);
        }
      } else {
        unhandledCount++;
      }
      continue;
    }

    let cleaned = raw;
    if (cleaned.includes('fact:')) {
      cleaned = cleaned.replace(/fact:[a-zA-Z0-9_.:-]+/g, 'chỉ tiêu');
    }

    if (!seen.has(cleaned)) {
      seen.add(cleaned);
      results.push(cleaned);
    }
  }

  if (unhandledCount > 0) {
    const msg = unhandledCount === 1
      ? 'Bộ phản biện còn 1 lưu ý chưa xử lý; xem quá trình phân tích.'
      : `Bộ phản biện còn ${unhandledCount} lưu ý chưa xử lý; xem quá trình phân tích.`;
    if (!seen.has(msg)) {
      results.push(msg);
    }
  }

  return results;
}



