import React from 'react';
import type { Signal, SignalVerdict } from '../model/types';
import { useEquityReport } from './useEquityReport';
import { formatDisplayText } from '@/shared/lib/formatting';
import type { LucideIcon } from 'lucide-react';
import { ArrowDownRight, ArrowLeftRight, ArrowUpRight, CircleHelp, Minus } from 'lucide-react';

interface VerdictConfig {
  label: string;
  icon: LucideIcon;
  colorClass: string;
}

const VERDICT_CONFIGS: Record<SignalVerdict, VerdictConfig> = {
  above_peers: {
    label: 'Trên nhóm',
    icon: ArrowUpRight,
    colorClass: 'text-emerald-700 font-medium'
  },
  in_line: {
    label: 'Ngang nhóm',
    icon: Minus,
    colorClass: 'text-text-secondary'
  },
  below_peers: {
    label: 'Dưới nhóm',
    icon: ArrowDownRight,
    colorClass: 'text-amber-700 font-medium'
  },
  mixed: {
    label: 'Trái chiều',
    icon: ArrowLeftRight,
    colorClass: 'text-amber-700 font-medium'
  },
  insufficient_data: {
    label: 'Chưa đủ dữ liệu',
    icon: CircleHelp,
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
    <aside className="bg-surface-secondary rounded-lg p-4 text-[13px] font-sans h-fit border border-border-subtle">
      <div className="font-semibold text-text-primary mb-1.5 text-[13px]">
        Tín hiệu so với nhóm
      </div>
      <div className="divide-y divide-line">
        {signals.map((sig, idx) => {
          const config = VERDICT_CONFIGS[sig.verdict] || VERDICT_CONFIGS.insufficient_data;
          return (
            <div key={idx} className="flex justify-between items-center py-2">
              <span className="text-text-secondary">{formatDisplayText(sig.label)}</span>
              <span className={`inline-flex items-center gap-1 ${config.colorClass}`}>
                <config.icon className="size-3.5 stroke-[2.2]" aria-hidden="true" />
                <span>{config.label}</span>
              </span>
            </div>
          );
        })}
      </div>

      <div className="font-semibold text-text-primary mt-4 mb-1.5 text-[13px]">
        Phạm vi
      </div>
      <div className="divide-y divide-line">
        <div className="flex justify-between items-center py-2 text-text-secondary">
          <span>Nhóm so sánh</span>
          <span className="text-text-primary font-medium">{peerCount} ngân hàng</span>
        </div>
        <div className="flex justify-between items-center py-2 text-text-secondary">
          <span>Số liệu có nguồn</span>
          <span className="text-text-primary font-medium tabular-nums">{matched}/{checked}</span>
        </div>
        <div className="flex justify-between items-center py-2 text-text-secondary">
          <span>Agent tham gia</span>
          <span className="text-text-primary font-medium">Company, Sector, Phản biện</span>
        </div>
      </div>
    </aside>
  );
};
