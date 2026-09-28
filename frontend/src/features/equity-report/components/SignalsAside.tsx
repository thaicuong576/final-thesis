import React from 'react';
import type { Signal, SignalVerdict } from '../model/types';
import { useEquityReport } from './useEquityReport';

interface VerdictConfig {
  label: string;
  icon: string;
  colorClass: string;
}

const VERDICT_CONFIGS: Record<SignalVerdict, VerdictConfig> = {
  above_peers: {
    label: 'Trên nhóm',
    icon: '↗',
    colorClass: 'text-emerald-700 font-medium'
  },
  in_line: {
    label: 'Ngang nhóm',
    icon: '—',
    colorClass: 'text-text-secondary'
  },
  below_peers: {
    label: 'Dưới nhóm',
    icon: '↘',
    colorClass: 'text-amber-700 font-medium'
  },
  mixed: {
    label: 'Trái chiều',
    icon: '↔',
    colorClass: 'text-amber-700 font-medium'
  },
  insufficient_data: {
    label: 'Chưa đủ dữ liệu',
    icon: '?',
    colorClass: 'text-text-muted'
  }
};

export const SignalsAside: React.FC<{ signals: Signal[] }> = ({ signals }) => {
  const { report, datasets } = useEquityReport();
  const audit = report.narrative_audit;

  // Determine peer group count
  const allEntities = new Set<string>();
  for (const ds of datasets) {
    for (const r of ds.rows || []) {
      if (r.entity_id) allEntities.add(r.entity_id);
    }
  }
  const peerCount = allEntities.size || 5;

  const matched = audit?.numbers_matched ?? 0;
  const checked = audit?.numbers_checked ?? matched;

  return (
    <aside className="bg-surface-secondary rounded p-3.5 text-xs font-sans h-fit border border-line">
      <div className="font-semibold text-text-primary mb-2 text-xs">
        Tín hiệu so với nhóm
      </div>
      <div className="divide-y divide-line">
        {signals.map((sig, idx) => {
          const config = VERDICT_CONFIGS[sig.verdict] || VERDICT_CONFIGS.insufficient_data;
          return (
            <div key={idx} className="flex justify-between items-center py-1.5">
              <span className="text-text-secondary">{sig.label}</span>
              <span className={`inline-flex items-center gap-1 ${config.colorClass}`}>
                <span className="text-xs" aria-hidden="true">{config.icon}</span>
                <span>{config.label}</span>
              </span>
            </div>
          );
        })}
      </div>

      <div className="font-semibold text-text-primary mt-3 mb-2 text-xs">
        Phạm vi
      </div>
      <div className="divide-y divide-line">
        <div className="flex justify-between items-center py-1.5 text-text-secondary">
          <span>Nhóm so sánh</span>
          <span className="text-text-primary font-medium">{peerCount} ngân hàng</span>
        </div>
        <div className="flex justify-between items-center py-1.5 text-text-secondary">
          <span>Số liệu có nguồn</span>
          <span className="text-text-primary font-medium font-mono">{matched}/{checked}</span>
        </div>
        <div className="flex justify-between items-center py-1.5 text-text-secondary">
          <span>Agent tham gia</span>
          <span className="text-text-primary font-medium">Company, Sector, Phản biện</span>
        </div>
      </div>
    </aside>
  );
};
