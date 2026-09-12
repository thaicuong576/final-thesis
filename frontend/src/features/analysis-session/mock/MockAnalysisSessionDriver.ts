import { useEffect, useMemo, useState } from 'react';
import type { AnalysisSessionEvent, AnalysisSessionViewModel } from '../model/types';
import { projectAnalysisSession } from '../model/projector';

export type DriverMode = 'AUTOPLAY' | 'FROZEN';

export interface DriverConfig {
  events: AnalysisSessionEvent[];
  mode?: DriverMode;
  step?: number; // If provided, limits playback to prefix of `step` events
  autoPlaySpeed?: number; // Speed scale, default 1.0
}

export interface UseAnalysisSessionDriverReturn {
  viewModel: AnalysisSessionViewModel;
  emittedEvents: AnalysisSessionEvent[];
  isComplete: boolean;
  currentStep: number;
  totalSteps: number;
  setStep: (step: number) => void;
}

/**
 * React hook that connects to the MockAnalysisSessionDriver.
 * Preserves the core principle:
 * MOCK EVENT SOURCE -> AnalysisSessionEvent[] -> PURE PROJECTOR -> AnalysisSessionViewModel -> UI
 */
export function useAnalysisSessionDriver({
  events,
  mode = 'FROZEN',
  step,
  autoPlaySpeed = 1.0
}: DriverConfig): UseAnalysisSessionDriverReturn {
  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => a.sequence - b.sequence),
    [events]
  );
  const totalSteps = sortedEvents.length;

  const initialStep = step !== undefined ? Math.min(Math.max(1, step), totalSteps) : totalSteps;

  const [currentStep, setCurrentStep] = useState<number>(
    mode === 'FROZEN' ? initialStep : 1
  );

  useEffect(() => {
    if (mode === 'FROZEN') {
      setCurrentStep(initialStep);
      return;
    }

    // AUTOPLAY MODE
    setCurrentStep(1);
    if (totalSteps <= 1) return;

    let timerId: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function scheduleNext(nextIndex: number) {
      if (cancelled || nextIndex > totalSteps) return;

      const prevEvent = sortedEvents[nextIndex - 2];
      const nextEvent = sortedEvents[nextIndex - 1];

      // Calculate relative delta in ms, scaled for comfortable review (~6-8s max)
      const rawDelta = nextEvent.occurredAtMs - (prevEvent ? prevEvent.occurredAtMs : 0);
      const scaledDelta = Math.max(300, Math.min(rawDelta / autoPlaySpeed, 1200));

      timerId = setTimeout(() => {
        if (!cancelled) {
          setCurrentStep(nextIndex);
          if (nextIndex < totalSteps) {
            scheduleNext(nextIndex + 1);
          }
        }
      }, scaledDelta);
    }

    scheduleNext(2);

    return () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
    };
  }, [sortedEvents, mode, initialStep, autoPlaySpeed, totalSteps]);

  const emittedEvents = useMemo(
    () => sortedEvents.slice(0, currentStep),
    [sortedEvents, currentStep]
  );

  const viewModel = useMemo(
    () => projectAnalysisSession(emittedEvents),
    [emittedEvents]
  );

  return {
    viewModel,
    emittedEvents,
    isComplete: currentStep >= totalSteps,
    currentStep,
    totalSteps,
    setStep: setCurrentStep
  };
}
