import type { MetricPresentation } from '@/features/equity-report/model/types';

export const DEFAULT_METRICS: Record<string, MetricPresentation> = {
  'bank.roe': {
    id: 'bank.roe',
    acronym: 'ROE',
    label: 'Tỷ suất sinh lời trên vốn chủ sở hữu',
    shortLabel: 'ROE',
    unit: '%',
    direction: 'higher_is_better',
    decimals: 1,
    group: 'profitability',
    groupLabel: 'Sinh lời'
  },
  'bank.roa': {
    id: 'bank.roa',
    acronym: 'ROA',
    label: 'Tỷ suất sinh lời trên tổng tài sản',
    shortLabel: 'ROA',
    unit: '%',
    direction: 'higher_is_better',
    decimals: 2,
    group: 'profitability',
    groupLabel: 'Sinh lời'
  },
  'bank.npl_g35': {
    id: 'bank.npl_g35',
    acronym: 'NPL_G35',
    label: 'Tỷ lệ nợ xấu',
    shortLabel: 'Nợ xấu',
    unit: '%',
    direction: 'lower_is_better',
    decimals: 2,
    group: 'asset_quality',
    groupLabel: 'Chất lượng nợ'
  },
  'bank.llr_coverage': {
    id: 'bank.llr_coverage',
    acronym: 'LLR_COVERAGE',
    label: 'Bao phủ nợ xấu',
    shortLabel: 'Bao phủ',
    unit: '%',
    direction: 'higher_is_better',
    decimals: 1,
    group: 'provisioning',
    groupLabel: 'Đệm dự phòng'
  },
  'bank.cir': {
    id: 'bank.cir',
    acronym: 'CIR',
    label: 'Tỷ lệ chi phí trên thu nhập',
    shortLabel: 'CIR',
    unit: '%',
    direction: 'lower_is_better',
    decimals: 1,
    group: 'efficiency',
    groupLabel: 'Hiệu quả hoạt động'
  },
  'bank.nim': {
    id: 'bank.nim',
    acronym: 'NIM',
    label: 'Biên lãi thuần',
    shortLabel: 'NIM',
    unit: '%',
    direction: 'higher_is_better',
    decimals: 2,
    group: 'profitability',
    groupLabel: 'Sinh lời'
  },
  'bank.casa': {
    id: 'bank.casa',
    acronym: 'CASA',
    label: 'Tỷ lệ tiền gửi không kỳ hạn',
    shortLabel: 'CASA',
    unit: '%',
    direction: 'higher_is_better',
    decimals: 1,
    group: 'funding',
    groupLabel: 'Cơ cấu huy động'
  },
  'bank.car': {
    id: 'bank.car',
    acronym: 'CAR',
    label: 'Tỷ lệ an toàn vốn',
    shortLabel: 'CAR',
    unit: '%',
    direction: 'higher_is_better',
    decimals: 1,
    group: 'capital',
    groupLabel: 'An toàn vốn'
  },
  'bank.ldr': {
    id: 'bank.ldr',
    acronym: 'LDR',
    label: 'Tỷ lệ dư nợ trên vốn huy động',
    shortLabel: 'LDR',
    unit: '%',
    direction: 'neutral',
    decimals: 1,
    group: 'liquidity',
    groupLabel: 'Thanh khoản'
  },
  'derived.roe_over_roa': {
    id: 'derived.roe_over_roa',
    acronym: 'ROE/ROA',
    label: 'Hệ số đòn bẩy vốn (ROE/ROA)',
    shortLabel: 'ROE/ROA',
    unit: 'lần',
    direction: 'neutral',
    decimals: 1,
    group: 'profitability',
    groupLabel: 'Đòn bẩy sinh lời'
  },
  'comparison.overall': {
    id: 'comparison.overall',
    acronym: 'SO_SANH',
    label: 'So sánh tổng thể',
    shortLabel: 'So sánh',
    unit: '',
    direction: 'neutral',
    decimals: 0,
    group: 'comparison',
    groupLabel: 'So sánh'
  }
};
