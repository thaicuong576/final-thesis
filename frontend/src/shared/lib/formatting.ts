import type { Period } from '../../entities/capability/model/types';

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
 * - Replaces raw metric identifiers (LLR_COVERAGE, NPL_G35, bank.*) with Vietnamese labels
 * - Cleans up internal technical reason codes (DATA_UNAVAILABLE -> Chưa có số liệu)
 */
export function formatDisplayText(text: string | null | undefined): string {
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

  // 3. Format specific known metric acronyms & keys
  s = s.replace(/bank\.llr_coverage/gi, 'Bao phủ nợ xấu');
  s = s.replace(/LLR_COVERAGE/gi, 'Bao phủ nợ xấu');
  s = s.replace(/llr_coverage/gi, 'Bao phủ nợ xấu');

  s = s.replace(/bank\.npl_g35/gi, 'Tỷ lệ nợ xấu');
  s = s.replace(/NPL_G35/gi, 'Tỷ lệ nợ xấu');
  s = s.replace(/npl_g35/gi, 'Tỷ lệ nợ xấu');

  s = s.replace(/bank\.roe/gi, 'ROE');
  s = s.replace(/bank\.roa/gi, 'ROA');
  s = s.replace(/bank\.nim/gi, 'NIM');
  s = s.replace(/bank\.casa/gi, 'CASA');
  s = s.replace(/bank\.cir/gi, 'CIR');
  s = s.replace(/bank\.car/gi, 'CAR');
  s = s.replace(/bank\.ldr/gi, 'LDR');
  s = s.replace(/derived\.roe_over_roa/gi, 'ROE/ROA');

  // 4. Any remaining bank.* patterns
  s = s.replace(/bank\.([a-z0-9_]+)/gi, (_, key: string) => key.toUpperCase());
  s = s.replace(/bank\./gi, '');

  // 5. Missing reason code & technical reason codes
  s = s.replace(/\bDATA_UNAVAILABLE\b/g, 'Chưa có số liệu đã kiểm định');

  return s;
}

