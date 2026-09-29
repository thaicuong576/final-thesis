import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { TraceActor, TraceKind, TraceStep } from '../model/types';

export interface ProcessTraceProps {
  steps: TraceStep[];
  live?: boolean;
  className?: string;
}

const ACTOR_META: Record<TraceActor, { label: string; color: string }> = {
  orchestrator: { label: 'Điều phối', color: 'var(--text-secondary, #62625d)' },
  company: { label: 'Company', color: 'var(--c-company, #1d8a7a)' },
  sector: { label: 'Sector', color: 'var(--c-sector, #6a5fc8)' },
  macro: { label: 'Macro', color: 'var(--text-muted, #85857e)' },
  critic: { label: 'Phản biện', color: 'var(--c-critic, #c85a2a)' },
  verifier: { label: 'Kiểm tra số liệu', color: 'var(--c-verifier, #2d7fbf)' },
  system: { label: 'Hệ thống', color: 'var(--text-muted, #85857e)' }
};

const QUESTION_TYPE_LABELS: Record<string, string> = {
  lookup: 'Tra cứu nhanh',
  company_profile: 'Hồ sơ doanh nghiệp',
  ranking: 'Xếp hạng',
  trend: 'Diễn biến chuỗi thời gian',
  head_to_head: 'Đối đầu',
  sector_theme: 'Chủ đề ngành',
  relationship: 'Mối quan hệ chỉ tiêu'
};

function formatDuration(ms: number): string {
  const sec = Math.max(1, Math.round(ms / 1000));
  return `${sec} giây`;
}

function formatTime(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export const ProcessTrace: React.FC<ProcessTraceProps> = ({ steps, live = false, className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedActor, setSelectedActor] = useState<string | null>(null);

  // User toggled steps: overrides default behavior (critique_issue and revision expanded by default)
  const [explicitlyToggled, setExplicitlyToggled] = useState<Record<string, boolean>>({});

  const isStepExpanded = useCallback(
    (step: TraceStep) => {
      const explicit = explicitlyToggled[step.step_id];
      if (explicit !== undefined) return explicit;
      return step.kind === 'critique_issue' || step.kind === 'revision';
    },
    [explicitlyToggled]
  );

  const toggleStep = useCallback((stepId: string, currentExpanded: boolean) => {
    setExplicitlyToggled((prev) => ({
      ...prev,
      [stepId]: !currentExpanded
    }));
  }, []);

  // Auto-scroll when live, ONLY if user is already at the bottom
  useEffect(() => {
    if (!live || !containerRef.current) return;
    const el = containerRef.current;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= 40;
    if (isAtBottom) {
      el.scrollTop = el.scrollHeight;
    }
  }, [steps, live]);

  // Metrics
  const lastStep = steps[steps.length - 1];
  const durationText = lastStep ? formatDuration(lastStep.t_ms) : '0 giây';

  // Count sub-agents: company, sector, macro, critic
  const involvedAgents = useMemo(() => {
    const plan = steps.find((s) => s.kind === 'plan');
    const planned = (plan?.detail?.agents as Array<{ agent: string; decision: string }>) || [];
    const activePlanned = planned.filter((a) => a.decision === 'run').map((a) => a.agent.toLowerCase());
    const set = new Set(activePlanned);
    steps.forEach((s) => {
      if (['company', 'sector', 'macro', 'critic'].includes(s.actor.toLowerCase())) {
        set.add(s.actor.toLowerCase());
      }
    });
    return Math.max(set.size, 1);
  }, [steps]);

  // Count critique rounds
  const critiqueRounds = useMemo(() => {
    let maxR = 0;
    steps.forEach((s) => {
      const r = Number(s.detail?.round);
      if (!isNaN(r) && r > maxR) maxR = r;
    });
    return maxR;
  }, [steps]);

  // Unique actors present in steps for filter chips
  const presentActors = useMemo(() => {
    const set = new Set<TraceActor>();
    steps.forEach((s) => {
      if (s.actor) set.add(s.actor);
    });
    return Array.from(set);
  }, [steps]);

  // Filtered steps
  const filteredSteps = useMemo(() => {
    if (!selectedActor) return steps;
    return steps.filter((s) => s.actor === selectedActor || s.recipient === selectedActor);
  }, [steps, selectedActor]);

  const allExpanded = filteredSteps.length > 0 && filteredSteps.every((s) => isStepExpanded(s));

  const toggleAll = (e: React.MouseEvent) => {
    e.preventDefault();
    const next: Record<string, boolean> = {};
    const targetState = !allExpanded;
    filteredSteps.forEach((s) => {
      next[s.step_id] = targetState;
    });
    setExplicitlyToggled(next);
  };

  return (
    <div className={`bg-surface-secondary border border-line rounded-lg p-5 ${className}`}>
      {/* Header */}
      <div className="flex flex-wrap justify-between items-baseline gap-2 mb-3">
        <h3 className="text-[15px] font-semibold text-text-primary">Quá trình phân tích</h3>
        <span className="text-xs text-text-muted">
          {involvedAgents} agent · {critiqueRounds} vòng phản biện · {durationText} ·{' '}
          <button
            type="button"
            onClick={toggleAll}
            className="text-text-accent hover:underline font-medium"
          >
            {allExpanded ? 'Thu gọn' : 'Mở tất cả'}
          </button>
        </span>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-1.5 mb-3" role="group" aria-label="Lọc theo agent">
        <button
          type="button"
          onClick={() => setSelectedActor(null)}
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border transition-colors ${
            selectedActor === null
              ? 'bg-surface-tertiary border-border-stronger text-text-primary'
              : 'bg-transparent border-line text-text-secondary hover:bg-surface-tertiary'
          }`}
        >
          Tất cả
        </button>
        {presentActors.map((actor) => {
          const meta = ACTOR_META[actor] || { label: actor, color: 'var(--text-muted)' };
          const isSelected = selectedActor === actor;
          return (
            <button
              key={actor}
              type="button"
              onClick={() => setSelectedActor(isSelected ? null : actor)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border transition-colors ${
                isSelected
                  ? 'bg-surface-tertiary border-border-stronger text-text-primary'
                  : 'bg-transparent border-line text-text-secondary hover:bg-surface-tertiary'
              }`}
            >
              <span
                className="w-2 h-2 rounded-full flex-none"
                style={{ backgroundColor: meta.color }}
                aria-hidden="true"
              />
              <span>{meta.label}</span>
            </button>
          );
        })}
      </div>

      {/* Steps List */}
      <div
        ref={containerRef}
        className="border-t border-line divide-y divide-border-subtle max-h-[600px] overflow-y-auto"
        tabIndex={0}
        aria-label="Danh sách các bước phân tích"
      >
        {filteredSteps.map((step) => {
          const isExpanded = isStepExpanded(step);
          const actorMeta = ACTOR_META[step.actor] || { label: step.actor, color: 'var(--text-muted)' };
          const recipientMeta = step.recipient ? ACTOR_META[step.recipient] || { label: step.recipient } : null;

          const actorSenderLabel = actorMeta.label;
          const recipientLabel = recipientMeta ? recipientMeta.label : null;

          return (
            <div key={step.step_id} className="text-xs">
              {/* Row Header */}
              <div
                role="button"
                tabIndex={0}
                aria-expanded={isExpanded}
                onClick={() => toggleStep(step.step_id, isExpanded)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleStep(step.step_id, isExpanded);
                  }
                }}
                className="grid grid-cols-[40px_12px_1fr_18px] gap-2 items-center py-2 px-1 cursor-pointer hover:bg-surface-tertiary transition-colors select-none"
              >
                <span className="font-mono text-text-muted text-[11px]">{formatTime(step.t_ms)}</span>
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: actorMeta.color }}
                  aria-hidden="true"
                />
                <span className="truncate pr-2">
                  <span className="font-semibold text-text-primary">
                    {actorSenderLabel}
                    {recipientLabel && recipientLabel !== 'Hệ thống' && ` → ${recipientLabel}`}
                  </span>
                  <span className="text-text-secondary ml-1">· {step.summary}</span>
                </span>
                <span className="text-text-muted">
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </span>
              </div>

              {/* Row Expanded Content */}
              {isExpanded && (
                <div className="pl-14 pr-2 pb-3 pt-1 text-text-secondary leading-relaxed border-b border-border-subtle bg-surface-primary/40">
                  <StepDetailRenderer kind={step.kind} detail={step.detail} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const ISSUE_TYPE_LABELS: Record<string, string> = {
  unsupported_claim: 'Nhận định thiếu căn cứ',
  missing_data: 'Thiếu dữ liệu',
  missing_evidence: 'Thiếu bằng chứng',
  numeric_inconsistency: 'Số liệu không khớp',
  scope_violation: 'Vi phạm phạm vi',
  cross_level_contradiction: 'Mâu thuẫn đa cấp',
  meaningful_divergence: 'Sai lệch ý nghĩa',
  incomplete_synthesis: 'Tổng hợp chưa đủ',
  malformed_output: 'Lỗi định dạng',
};

const SEVERITY_LABELS: Record<string, string> = {
  blocker: 'Chặn',
  major: 'Lớn',
  minor: 'Nhỏ',
  warning: 'Cảnh báo',
  notice: 'Lưu ý',
};

const REQUIRED_ACTION_LABELS: Record<string, string> = {
  requery_data: 'Truy vấn lại dữ liệu',
  retrieve_evidence: 'Thu thập thêm chứng cứ',
  revise_claim: 'Sửa nhận định',
  remove_claim: 'Loại bỏ nhận định',
  add_limitation: 'Bổ sung giới hạn',
  reconcile_cross_level: 'Đối chiếu chéo',
};

function formatIssueType(raw?: string): string {
  if (!raw) return '—';
  return ISSUE_TYPE_LABELS[raw.toLowerCase()] || raw;
}

function formatSeverity(raw?: string): string {
  if (!raw) return '—';
  return SEVERITY_LABELS[raw.toLowerCase()] || raw;
}

function formatRequiredAction(raw?: string): string {
  if (!raw) return '—';
  return REQUIRED_ACTION_LABELS[raw.toLowerCase()] || raw;
}

function StepDetailRenderer({ kind, detail }: { kind: TraceKind; detail: Record<string, unknown> }) {
  if (!detail || Object.keys(detail).length === 0) return null;

  switch (kind) {
    case 'plan': {
      const qType = (detail.question_type as string) || '';
      const qLabel = QUESTION_TYPE_LABELS[qType] || qType;
      const rationale = detail.rationale as string | undefined;
      const tools = (detail.tools as Array<{ tool: string; agent: string; label: string }>) || [];
      const agents = (detail.agents as Array<{ agent: string; decision: string; reason: string }>) || [];
      const isRules = detail.planner_source === 'rules';

      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-text-primary">Dạng câu hỏi:</span>
            <span>{qLabel}</span>
            {isRules && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-tertiary text-text-muted border border-line">
                Kế hoạch theo luật
              </span>
            )}
          </div>
          {rationale && <p className="italic text-text-secondary">{rationale}</p>}

          {tools.length > 0 && (
            <div className="mt-2">
              <div className="text-[11px] font-semibold text-text-muted mb-1">Phép phân tích</div>
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-line text-text-muted text-[11px]">
                    <th className="py-1">Phép phân tích</th>
                    <th className="py-1">Agent</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {tools.map((t, idx) => (
                    <tr key={idx}>
                      <td className="py-1 text-text-primary">{t.label || t.tool}</td>
                      <td className="py-1">{t.agent}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {agents.length > 0 && (
            <div className="mt-2">
              <div className="text-[11px] font-semibold text-text-muted mb-1">Phân công agent</div>
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-line text-text-muted text-[11px]">
                    <th className="py-1">Agent</th>
                    <th className="py-1">Quyết định</th>
                    <th className="py-1">Lý do</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {agents.map((a, idx) => (
                    <tr key={idx}>
                      <td className="py-1 font-medium text-text-primary">{a.agent}</td>
                      <td className="py-1">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            a.decision === 'run'
                              ? 'bg-success-soft text-text-success'
                              : 'bg-surface-tertiary text-text-muted'
                          }`}
                        >
                          {a.decision === 'run' ? 'Gọi' : 'Bỏ qua'}
                        </span>
                      </td>
                      <td className="py-1 text-text-secondary">{a.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      );
    }

    case 'assign': {
      const task = detail.task as string | undefined;
      const tools = (detail.tools as string[]) || [];
      return (
        <div className="space-y-1">
          {task && (
            <blockquote className="border-l-2 border-border-strong pl-2 text-text-primary italic">
              {task}
            </blockquote>
          )}
          {tools.length > 0 && (
            <div className="text-[11px] text-text-muted">
              Công cụ: {tools.join(', ')}
            </div>
          )}
        </div>
      );
    }

    case 'tool_result': {
      const label = (detail.label || detail.tool) as string | undefined;
      const facts = (detail.facts as Array<{ label: string; display_value: string; source_note_no?: number }>) || [];
      const datasets = (detail.datasets as Array<{ title: string }>) || [];
      const missing = (detail.missing as Array<{ reason: string }>) || [];

      return (
        <div className="space-y-2">
          {label && <div className="font-semibold text-text-primary">{label}</div>}

          {facts.length > 0 && (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-line text-text-muted text-[11px]">
                  <th className="py-1">Nội dung</th>
                  <th className="py-1">Giá trị</th>
                  <th className="py-1">Nguồn</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {facts.map((f, idx) => (
                  <tr key={idx}>
                    <td className="py-1 text-text-primary">{f.label}</td>
                    <td className="py-1 font-semibold">{f.display_value}</td>
                    <td className="py-1 text-text-muted">Nguồn {f.source_note_no || 1}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {datasets.length > 0 && (
            <div className="text-[11px] text-text-secondary">
              <span className="font-semibold text-text-muted">Tập dữ liệu: </span>
              {datasets.map((d) => d.title).join('; ')}
            </div>
          )}

          {missing.length > 0 && (
            <div className="text-[11px] text-text-muted italic">
              {missing.map((m) => m.reason).join('; ')}
            </div>
          )}
        </div>
      );
    }

    case 'draft': {
      const sentences = (detail.sentences as Array<{ text: string }>) || [];
      return (
        <div className="space-y-1">
          <div className="text-[11px] font-semibold text-text-muted">Nhận định nháp:</div>
          <div className="space-y-1">
            {sentences.map((s, idx) => (
              <blockquote key={idx} className="border-l-2 border-border-strong pl-2 text-text-primary">
                {s.text}
              </blockquote>
            ))}
          </div>
        </div>
      );
    }

    case 'compose': {
      const blocks = (detail.blocks as Array<{ type: string; title: string }>) || [];
      const isFallback = detail.composition_source === 'deterministic_fallback';
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-text-muted">Các khối báo cáo:</span>
            {isFallback && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-tertiary text-text-muted border border-line">
                Bố cục mặc định
              </span>
            )}
          </div>
          <ol className="list-decimal list-inside space-y-0.5 text-xs text-text-primary">
            {blocks.map((b, idx) => (
              <li key={idx}>
                <span className="font-medium">{b.title || b.type}</span>
                <span className="text-text-muted text-[11px] ml-1">({b.type})</span>
              </li>
            ))}
          </ol>
        </div>
      );
    }

    case 'verify': {
      const matched = String(detail.numbers_matched ?? detail.sentences_checked ?? 0);
      const checked = String(detail.numbers_checked ?? detail.sentences_checked ?? 0);
      const dropped = (detail.dropped as Array<{ text: string; reason: string }>) || [];

      return (
        <div className="space-y-1.5">
          <div className="font-medium text-text-primary">
            {matched}/{checked} số khớp dữ liệu gốc
          </div>
          {dropped.length > 0 ? (
            <div className="space-y-1 mt-1">
              <div className="text-[11px] font-semibold text-text-danger">Câu bị loại:</div>
              {dropped.map((d, idx) => (
                <div key={idx} className="p-2 bg-surface-tertiary rounded border border-line text-xs">
                  <div className="line-through text-text-danger mb-0.5">{d.text}</div>
                  <div className="text-text-muted text-[11px]">Lý do: {d.reason}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[11px] text-text-muted">Không có câu nào bị loại.</div>
          )}
        </div>
      );
    }
    case 'critique_issue': {
      const issueType = formatIssueType((detail.issue_type as string) || (detail.type as string));
      const severity = formatSeverity(detail.severity as string);
      const action = formatRequiredAction((detail.required_action as string) || (detail.action as string));
      const targetText = detail.target_text as string | undefined;
      const evidence = detail.evidence as string | undefined;

      return (
        <div className="space-y-2">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line text-text-muted text-[11px]">
                <th className="py-1">Loại</th>
                <th className="py-1">Mức độ</th>
                <th className="py-1">Yêu cầu</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="py-1 text-text-primary font-medium">{issueType}</td>
                <td className="py-1">{severity}</td>
                <td className="py-1">{action}</td>
              </tr>
            </tbody>
          </table>

          {targetText && (
            <div>
              <div className="text-[11px] font-semibold text-text-muted mb-0.5">Câu bị bắt:</div>
              <blockquote className="border-l-2 border-border-warning pl-2 text-text-primary italic">
                {targetText}
              </blockquote>
            </div>
          )}

          {evidence && (
            <div className="text-xs">
              <span className="font-semibold text-text-muted">Căn cứ: </span>
              <span>{evidence}</span>
            </div>
          )}
        </div>
      );
    }

    case 'revision': {
      const before = detail.before as string | undefined;
      const after = detail.after as string | undefined;

      return (
        <div className="space-y-1.5">
          {before && (
            <div className="border-l-2 border-border-strong pl-2">
              <span className="text-[11px] font-semibold text-text-muted">Trước · </span>
              <span className="line-through text-text-danger">{before}</span>
            </div>
          )}
          {after && (
            <div className="border-l-2 border-border-success pl-2">
              <span className="text-[11px] font-semibold text-text-success">Sau · </span>
              <span className="text-text-success font-medium">{after}</span>
            </div>
          )}
        </div>
      );
    }

    case 'cross_level_finding': {
      const text = detail.text as string | undefined;
      const kindStr = detail.kind as string | undefined;
      return (
        <div className="space-y-1">
          {kindStr && <div className="text-[11px] font-semibold text-text-muted">{kindStr}</div>}
          {text && <div className="text-text-primary">{text}</div>}
        </div>
      );
    }

    case 'blocked': {
      const msg = (detail.message as string) || 'Yêu cầu bị chặn.';
      return <div className="text-text-danger font-medium">{msg}</div>;
    }

    case 'accept': {
      const round = detail.round ?? 1;
      return (
        <div className="text-text-success font-medium">
          Phê duyệt sau vòng {String(round)}, không còn vấn đề mở.
        </div>
      );
    }

    case 'report_ready': {
      const repId = detail.report_id as string | undefined;
      return (
        <div className="text-text-success font-medium">
          Báo cáo sẵn sàng {repId ? `(${repId})` : ''}
        </div>
      );
    }

    default:
      return (
        <pre className="text-[11px] overflow-x-auto text-text-muted">
          {JSON.stringify(detail, null, 2)}
        </pre>
      );
  }
}
