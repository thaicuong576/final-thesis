import { useCallback, useMemo, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { AnalysisRequest } from '../../entities/analysis/model/types';
import type { AnalysisCapabilities } from '../../entities/capability/model/types';
import { analysisService } from '../../entities/analysis/api/analysisService';
import { AnalysisIntentSection } from '../../features/create-analysis/components/AnalysisIntentSection';
import { CapabilityDetailsDrawer } from '../../features/create-analysis/components/CapabilityDetailsDrawer';
import { CapabilitySummaryBar } from '../../features/create-analysis/components/CapabilitySummaryBar';
import { RequestSummary } from '../../features/create-analysis/components/RequestSummary';
import { ScopeSelectors } from '../../features/create-analysis/components/ScopeSelectors';
import { SystemContextSection } from '../../features/create-analysis/components/SystemContextSection';
import { TopicMetricSelector } from '../../features/create-analysis/components/TopicMetricSelector';
import { useAnalysisCapabilities } from '../../features/create-analysis/hooks/useAnalysisCapabilities';
import { generateSuggestedObjective, getScopeSignature, hasPossibleObjectiveMismatch } from '../../features/create-analysis/model/objective';
import { analysisRequestSchema, type AnalysisFormValues } from '../../features/create-analysis/schema';
import { WorkspaceShell } from '../../components/layout/WorkspaceShell';

const defaultValues: AnalysisFormValues = {
  objective: '',
  analysisTargetIds: [],
  periodIds: [],
  metricIds: []
};

export function CreateAnalysisPage() {
  const capabilitiesQuery = useAnalysisCapabilities();
  const capabilitiesData = capabilitiesQuery.data;
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedTopicIds, setSelectedTopicIds] = useState<string[]>([]);
  const [manualMetricOverrides, setManualMetricOverrides] = useState<Record<string, boolean>>({});
  const [objectiveState, setObjectiveState] = useState<{ text: string; signature: string } | null>(null);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const form = useForm<AnalysisFormValues>({
    resolver: zodResolver(analysisRequestSchema),
    mode: 'onChange',
    defaultValues
  });
  const values = useWatch({ control: form.control });
  const objective = values.objective ?? '';

  const scopeSignature = useMemo(() => getScopeSignature({
    analysisTargetIds: values.analysisTargetIds ?? [],
    periodIds: values.periodIds ?? [],
    metricIds: values.metricIds ?? []
  }), [values.analysisTargetIds, values.periodIds, values.metricIds]);

  const scopeChangedNotice = Boolean(objectiveState && objectiveState.signature !== scopeSignature);
  const canSuggest = Boolean((values.analysisTargetIds?.length ?? 0) > 0 && (values.periodIds?.length ?? 0) > 0 && (values.metricIds?.length ?? 0) > 0 && capabilitiesData);
  const closeDetails = useCallback(() => setDetailsOpen(false), []);

  if (capabilitiesQuery.isPending) return <WorkspaceShell activeSection="analysis"><LoadingState /></WorkspaceShell>;
  if (capabilitiesQuery.isError || !capabilitiesData) return <WorkspaceShell activeSection="analysis"><ErrorState /></WorkspaceShell>;
  const capabilities = capabilitiesData;

  function applySuggestedObjective() {
    const nextValues = form.getValues();
    const text = generateSuggestedObjective(nextValues, capabilities);
    form.setValue('objective', text, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setObjectiveState({ text, signature: getScopeSignature(nextValues) });
    setSubmissionMessage(null);
  }

  function handleTopicToggle(topicId: string) {
    const topic = capabilities.topics.find((item) => item.id === topicId);
    if (!topic) return;
    const isSelected = selectedTopicIds.includes(topicId);
    const currentMetrics = form.getValues('metricIds');
    const nextMetrics = isSelected
      ? currentMetrics.filter((metricId) => !topic.metricIds.includes(metricId) || manualMetricOverrides[metricId] !== undefined)
      : [...new Set([...currentMetrics, ...topic.metricIds.filter((metricId) => manualMetricOverrides[metricId] !== false)])];
    setSelectedTopicIds(isSelected ? selectedTopicIds.filter((id) => id !== topicId) : [...selectedTopicIds, topicId]);
    form.setValue('metricIds', nextMetrics, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setSubmissionMessage(null);
  }

  function handleManualMetricToggle(metricId: string) {
    const isSelected = form.getValues('metricIds').includes(metricId);
    const nextMetrics = isSelected
      ? form.getValues('metricIds').filter((id) => id !== metricId)
      : [...form.getValues('metricIds'), metricId];
    setManualMetricOverrides((current) => ({ ...current, [metricId]: !isSelected }));
    form.setValue('metricIds', nextMetrics, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setSubmissionMessage(null);
  }

  function restoreDefaultMetrics() {
    const nextMetrics = capabilities.topics.filter((topic) => selectedTopicIds.includes(topic.id)).flatMap((topic) => topic.metricIds);
    setManualMetricOverrides({});
    form.setValue('metricIds', [...new Set(nextMetrics)], { shouldDirty: true, shouldTouch: true, shouldValidate: true });
  }

  function keepCurrentObjective() {
    setObjectiveState(null);
  }

  async function submitAnalysis() {
    const isValid = await form.trigger();
    if (!isValid || capabilities.macro.status === 'UNAVAILABLE') return;
    setIsSubmitting(true);
    setSubmissionMessage(null);
    const formValues = form.getValues();
    const request: AnalysisRequest = {
      ...formValues,
      capabilitySnapshotId: capabilities.snapshotId,
      peerUniverseId: capabilities.peerUniverse.id
    };
    const receipt = await analysisService.submit(request);
    setSubmissionMessage(receipt.message);
    setIsSubmitting(false);
  }

  return (
    <WorkspaceShell
      activeSection="analysis"
      context={<AnalysisContextBar capabilities={capabilities} onOpenDetails={() => setDetailsOpen(true)} />}
    >
      <div className="min-h-screen bg-canvas text-ink">
        <div className="mx-auto max-w-[1440px] px-5 pb-12 pt-4 lg:px-9 lg:pt-5">
          <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
            <form className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); void submitAnalysis(); }} noValidate>
              <AnalysisIntentSection
                control={form.control}
                errors={form.formState.errors}
                register={form.register}
                canSuggest={canSuggest}
                objectiveWasEdited={Boolean(objectiveState && objective !== objectiveState.text)}
                scopeChangedNotice={scopeChangedNotice}
                possibleMismatch={hasPossibleObjectiveMismatch(objective, capabilities, { analysisTargetIds: values.analysisTargetIds ?? [], periodIds: values.periodIds ?? [], metricIds: values.metricIds ?? [] })}
                onSuggest={applySuggestedObjective}
                onUpdateSuggestion={applySuggestedObjective}
                onKeepObjective={keepCurrentObjective}
              />
              <ScopeSelectors capabilities={capabilities} errors={form.formState.errors} setValue={form.setValue} watch={form.watch} />
              <TopicMetricSelector capabilities={capabilities} errors={form.formState.errors} watch={form.watch} selectedTopicIds={selectedTopicIds} onTopicToggle={handleTopicToggle} onManualMetricToggle={handleManualMetricToggle} onRestoreDefaults={restoreDefaultMetrics} />
              <SystemContextSection capabilities={capabilities} />
            </form>

            <RequestSummary capabilities={capabilities} values={{ objective, analysisTargetIds: values.analysisTargetIds ?? [], periodIds: values.periodIds ?? [], metricIds: values.metricIds ?? [] }} isValid={form.formState.isValid} isSubmitting={isSubmitting} submissionMessage={submissionMessage} onSubmit={() => void submitAnalysis()} />
          </div>
        </div>

        <CapabilityDetailsDrawer capabilities={capabilities} open={detailsOpen} onClose={closeDetails} />
      </div>
    </WorkspaceShell>
  );
}

function AnalysisContextBar({ capabilities, onOpenDetails }: { capabilities: AnalysisCapabilities; onOpenDetails: () => void }) {
  return (
    <div className="mx-auto w-full max-w-[1440px] px-5 py-2.5 lg:px-9">
      <div className="flex min-h-7 items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-[-0.025em] text-ink">Tạo phân tích</h1>
          <p className="hidden text-xs text-muted sm:block">Xây dựng yêu cầu trong phạm vi dữ liệu đã được xác thực.</p>
        </div>
        <span className="hidden shrink-0 text-[11px] font-medium text-muted md:block">Phân tích tài chính</span>
      </div>
      <CapabilitySummaryBar capabilities={capabilities} onOpenDetails={onOpenDetails} />
    </div>
  );
}

function LoadingState() {
  return <div className="grid min-h-screen place-items-center bg-canvas p-6"><p className="text-sm text-muted" role="status">Đang tải phạm vi dữ liệu…</p></div>;
}

function ErrorState() {
  return <div className="grid min-h-screen place-items-center bg-canvas p-6"><div className="border border-[#e4c0bb] bg-white p-6 text-center"><p className="font-semibold text-blocked">Không thể tải phạm vi dữ liệu.</p><p className="mt-2 text-sm text-muted">Vui lòng thử lại khi dịch vụ phạm vi dữ liệu sẵn sàng.</p></div></div>;
}
