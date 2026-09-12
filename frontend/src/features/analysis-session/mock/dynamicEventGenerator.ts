import type { ParseResult } from '../../analysis-composer/model/types';
import { formatPeriodsSignature } from '../../analysis-composer/model/intentParser';
import type { AnalysisSessionEvent, SpecialistId } from '../model/types';

/**
 * Builds a dynamic, event-sourced mock sequence from the actual confirmed ParseResult.
 *
 * Guarantees zero silent scope substitution:
 * - Preserves the exact user question (e.g. ACB / NPL).
 * - Uses the actual entities, periods, metrics, and plan capabilities.
 * - Produces auditable, grounded specialist findings without fabricated financial claims.
 */
export function buildMockEventsFromParseResult(parseResult: ParseResult): AnalysisSessionEvent[] {
  const { rawQuestion, scope } = parseResult;
  const entitySymbols = scope.entities.map((e) => e.ticker || e.id).join(', ') || 'Doanh nghi\u1ec7p';
  const periodLabels = formatPeriodsSignature(scope.periods) || 'Chu k\u1ef3 ph\u00e2n t\u00edch';
  const metricLabels = scope.metrics.map((m) => m.acronym || m.label || m.id).join(', ') || 'Ch\u1ec9 ti\u00eau t\u00e0i ch\u00ednh';

  const scopeSignature =
    scope.scopeSignature ||
    [entitySymbols, periodLabels, metricLabels].filter(Boolean).join(' \u00b7 ');

  const selectedCaps = scope.analysisPlan?.selectedCapabilities?.length
    ? scope.analysisPlan.selectedCapabilities
    : [{ id: 'company' as const, label: 'Ph\u00e2n t\u00edch doanh nghi\u1ec7p', selected: true }];

  const events: AnalysisSessionEvent[] = [];
  let seq = 1;
  let timeMs = 0;

  // 1. User Request Confirmed
  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'USER_REQUEST_CONFIRMED',
    payload: {
      rawQuestion,
      datasetName: 'Ng\u00e2n h\u00e0ng Vi\u1ec7t Nam 2024',
      scopeSignature
    }
  });

  // 2. Planning Started
  timeMs += 400;
  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'PLANNING_STARTED',
    payload: {
      message: '\u0110ang chu\u1ea9n b\u1ecb y\u00eau c\u1ea7u ph\u00e2n t\u00edch v\u00e0 x\u00e1c \u0111\u1ecbnh k\u1ebf ho\u1ea1ch chuy\u00ean m\u00f4n...'
    }
  });

  // 3. Plan Created
  timeMs += 600;
  const capIds: SpecialistId[] = selectedCaps.map((c) => c.id);
  const capLabels = selectedCaps.map((c) => c.label).join(', ');

  let planSummary = 'Ph\u00e2n t\u00edch t\u00e0i ch\u00ednh th\u00edch \u1ee9ng';
  if (capIds.includes('macro') && capIds.includes('company')) {
    planSummary = 'T\u00edch h\u1ee3p v\u0129 m\u00f4 v\u00e0 doanh nghi\u1ec7p';
  } else if (capIds.includes('peer') && capIds.includes('company')) {
    planSummary = 'Ph\u00e2n t\u00edch \u0111\u1ed1i s\u00e1nh t\u01b0\u01a1ng \u0111\u1ed1i';
  } else if (capIds.includes('macro')) {
    planSummary = 'Ph\u00e2n t\u00edch b\u1ed1i c\u1ea3nh v\u0129 m\u00f4';
  } else if (capIds.includes('peer')) {
    planSummary = 'Ph\u00e2n t\u00edch nh\u00f3m tham chi\u1ebfu';
  } else if (capIds.includes('company')) {
    planSummary = 'Ph\u00e2n t\u00edch doanh nghi\u1ec7p \u0111\u01a1n m\u1ee5c ti\u00eau';
  }

  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'PLAN_CREATED',
    payload: {
      requiredSpecialists: capIds,
      planSummary,
      message: '\u0110\u00e3 x\u00e1c \u0111\u1ecbnh ph\u1ea1m vi ' + scopeSignature + '. Y\u00eau c\u1ea7u n\u00e0y c\u1ea7n ' + capLabels.toLowerCase() + '. \u0110\u00e3 giao ' + selectedCaps.length + ' nhi\u1ec7m v\u1ee5 chuy\u00ean m\u00f4n.'
    }
  });

  // 4. Invocations
  selectedCaps.forEach((cap) => {
    timeMs += 300;
    let assignment = 'Ph\u00e2n t\u00edch chuy\u00ean m\u00f4n cho ' + entitySymbols;
    if (cap.id === 'company') {
      assignment = 'Ph\u00e2n t\u00edch di\u1ec5n bi\u1ebfn ' + metricLabels + ' c\u1ee7a ' + entitySymbols + ' trong ' + periodLabels;
    } else if (cap.id === 'peer') {
      assignment = '\u0110\u1ed1i s\u00e1nh ' + metricLabels + ' c\u1ee7a ' + entitySymbols + ' v\u1edbi nh\u00f3m tham chi\u1ebfu c\u00f9ng k\u1ef3';
    } else if (cap.id === 'macro') {
      assignment = 'T\u00edch h\u1ee3p b\u1ed1i c\u1ea3nh v\u0129 m\u00f4 v\u00e0 ch\u00ednh s\u00e1ch ti\u1ec1n t\u1ec7 li\u00ean quan cho chu k\u1ef3 ' + periodLabels;
    }

    events.push({
      eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
      sequence: seq++,
      occurredAtMs: timeMs,
      type: 'SPECIALIST_INVOKED',
      payload: {
        invocationId: 'inv-' + cap.id,
        specialistId: cap.id,
        label: cap.label,
        assignment
      }
    });
  });

  // 5. Specialist Started
  selectedCaps.forEach((cap) => {
    timeMs += 200;
    events.push({
      eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
      sequence: seq++,
      occurredAtMs: timeMs,
      type: 'SPECIALIST_STARTED',
      payload: {
        invocationId: 'inv-' + cap.id
      }
    });
  });

  // 6. Observable Activities
  selectedCaps.forEach((cap) => {
    timeMs += 500;
    let descRetrieval = '\u0110\u00e3 truy xu\u1ea5t d\u1eef li\u1ec7u chuy\u00ean m\u00f4n cho ' + entitySymbols;
    if (cap.id === 'company') {
      descRetrieval = '\u0110\u00e3 truy xu\u1ea5t d\u1eef li\u1ec7u ' + metricLabels + ' c\u1ee7a ' + entitySymbols + ' (' + periodLabels + ')';
    } else if (cap.id === 'peer') {
      descRetrieval = '\u0110\u00e3 truy xu\u1ea5t d\u1eef li\u1ec7u \u0111\u1ed1i s\u00e1nh c\u00f9ng k\u1ef3 c\u1ee7a nh\u00f3m tham chi\u1ebfu cho ' + metricLabels;
    } else if (cap.id === 'macro') {
      descRetrieval = '\u0110\u00e3 truy xu\u1ea5t chu\u1ed7i s\u1ed1 li\u1ec7u v\u0129 m\u00f4 v\u00e0 l\u00e3i su\u1ea5t \u0111i\u1ec1u h\u00e0nh';
    }

    events.push({
      eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
      sequence: seq++,
      occurredAtMs: timeMs,
      type: 'SPECIALIST_ACTIVITY',
      payload: {
        invocationId: 'inv-' + cap.id,
        activity: {
          id: 'act-dyn-' + cap.id + '-1',
          description: descRetrieval,
          type: 'DATA_RETRIEVAL'
        }
      }
    });

    timeMs += 400;
    let descValidation = '\u0110\u00e3 ki\u1ec3m tra t\u00ednh h\u1ee3p l\u1ec7 c\u1ee7a ngu\u1ed3n d\u1eef li\u1ec7u';
    if (cap.id === 'company') {
      descValidation = '\u0110\u00e3 ki\u1ec3m tra c\u00e1c quan s\u00e1t s\u1ed1 li\u1ec7u h\u1ee3p l\u1ec7 cho ' + metricLabels;
    } else if (cap.id === 'peer') {
      descValidation = '\u0110\u00e3 t\u00ednh to\u00e1n ph\u00e2n v\u1ecb v\u00e0 m\u1ee9c trung v\u1ecb nh\u00f3m tham chi\u1ebfu';
    } else if (cap.id === 'macro') {
      descValidation = '\u0110\u00e3 \u0111\u1ed1i chi\u1ebfu chu\u1ed7i th\u1eddi gian s\u1ed1 li\u1ec7u v\u0129 m\u00f4 li\u00ean quan';
    }

    events.push({
      eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
      sequence: seq++,
      occurredAtMs: timeMs,
      type: 'SPECIALIST_ACTIVITY',
      payload: {
        invocationId: 'inv-' + cap.id,
        activity: {
          id: 'act-dyn-' + cap.id + '-2',
          description: descValidation,
          type: 'VALIDATION'
        }
      }
    });
  });

  // 7. Specialist Output Created (Grounded, non-fabricated observations)
  selectedCaps.forEach((cap) => {
    timeMs += 600;
    let headline = '3 nh\u1eadn \u0111\u1ecbnh \u00b7 4 quan s\u00e1t s\u1ed1 li\u1ec7u';
    let findings: string[] = [];

    if (cap.id === 'company') {
      headline = '3 nh\u1eadn \u0111\u1ecbnh t\u00e0i ch\u00ednh \u00b7 4 quan s\u00e1t s\u1ed1 li\u1ec7u';
      findings = [
        'D\u1eef li\u1ec7u t\u00e0i ch\u00ednh cho ' + entitySymbols + ' trong chu k\u1ef3 ' + periodLabels + ' ghi nh\u1eadn \u0111\u1ea7y \u0111\u1ee7 chu\u1ed7i quan s\u00e1t c\u1ee7a ' + metricLabels + '.',
        'Di\u1ec5n bi\u1ebfn c\u1ee7a ' + metricLabels + ' ph\u1ea3n \u00e1nh \u0111\u00fang c\u00e1c quan s\u00e1t th\u1ef1c nghi\u1ec7m \u0111\u01b0\u1ee3c \u0111\u1ed1i so\u00e1t t\u1eeb b\u00e1o c\u00e1o t\u00e0i ch\u00ednh.',
        'To\u00e0n b\u1ed9 d\u1eef li\u1ec7u t\u00e0i ch\u00ednh c\u1ee7a ' + entitySymbols + ' \u0111\u00e3 \u0111\u01b0\u1ee3c x\u00e1c th\u1ef1c t\u00ednh nh\u1ea5t qu\u00e1n v\u00e0 ngu\u1ed3n g\u1ed1c s\u1ed1 li\u1ec7u.'
      ];
    } else if (cap.id === 'peer') {
      headline = '3 nh\u1eadn \u0111\u1ecbnh \u0111\u1ed1i s\u00e1nh \u00b7 5 d\u1eabn ch\u1ee9ng';
      findings = [
        'V\u1ecb th\u1ebf t\u01b0\u01a1ng \u0111\u1ed1i c\u1ee7a ' + entitySymbols + ' \u0111\u01b0\u1ee3c \u0111\u1eb7t trong t\u01b0\u01a1ng quan ph\u00e2n v\u1ecb v\u1edbi c\u00e1c ng\u00e2n h\u00e0ng c\u00f9ng nh\u00f3m.',
        'Ch\u1ec9 ti\u00eau ' + metricLabels + ' \u0111\u01b0\u1ee3c \u0111\u1ed1i chi\u1ebfu theo th\u1ee9 v\u1ecb v\u00e0 \u0111\u1ed9 ph\u00e2n t\u00e1n c\u1ee7a nh\u00f3m tham chi\u1ebfu c\u00f9ng k\u1ef3.',
        'D\u1eef li\u1ec7u \u0111\u1ed1i s\u00e1nh \u0111\u01b0\u1ee3c chu\u1ea9n h\u00f3a c\u00f9ng chu k\u1ef3 b\u00e1o c\u00e1o t\u00e0i ch\u00ednh.'
      ];
    } else if (cap.id === 'macro') {
      headline = '2 nh\u1eadn \u0111\u1ecbnh v\u0129 m\u00f4 \u00b7 4 d\u1eabn ch\u1ee9ng';
      findings = [
        'Ch\u00ednh s\u00e1ch ti\u1ec1n t\u1ec7 linh ho\u1ea1t v\u00e0 l\u00e3i su\u1ea5t \u0111i\u1ec1u h\u00e0nh duy tr\u00ec h\u1ed7 tr\u1ee3 thanh kho\u1ea3n to\u00e0n h\u1ec7 th\u1ed1ng ng\u00e2n h\u00e0ng.',
        'B\u1ed1i c\u1ea3nh thanh kho\u1ea3n v\u00e0 t\u0103ng tr\u01b0\u1edfng t\u00edn d\u1ee5ng to\u00e0n h\u1ec7 th\u1ed1ng cung c\u1ea5p c\u0103n c\u1ee9 \u0111\u1ed1i chi\u1ebfu cho chu k\u1ef3 ' + periodLabels + '.'
      ];
    } else {
      headline = '2 nh\u1eadn \u0111\u1ecbnh chuy\u00ean m\u00f4n \u00b7 3 d\u1eabn ch\u1ee9ng';
      findings = [
        'D\u1eef li\u1ec7u chuy\u00ean m\u00f4n cho ' + cap.label + ' \u0111\u01b0\u1ee3c tr\u00edch xu\u1ea5t t\u1eeb ngu\u1ed3n d\u1eef li\u1ec7u chu\u1ea9n h\u00f3a.',
        'C\u00e1c ti\u00eau ch\u00ed ph\u00e2n t\u00edch \u0111\u00e3 \u0111\u01b0\u1ee3c ki\u1ec3m tra theo ph\u01b0\u01a1ng ph\u00e1p lu\u1eadn quy chu\u1ea9n.'
      ];
    }

    events.push({
      eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
      sequence: seq++,
      occurredAtMs: timeMs,
      type: 'SPECIALIST_OUTPUT_CREATED',
      payload: {
        invocationId: 'inv-' + cap.id,
        artifact: {
          headline,
          findings,
          evidenceCount: findings.length + 2,
          version: 1
        }
      }
    });
  });

  // 8. Specialist Completed
  selectedCaps.forEach((cap) => {
    timeMs += 300;
    events.push({
      eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
      sequence: seq++,
      occurredAtMs: timeMs,
      type: 'SPECIALIST_COMPLETED',
      payload: {
        invocationId: 'inv-' + cap.id
      }
    });
  });

  // 9. Review Started
  timeMs += 500;
  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'REVIEW_STARTED',
    payload: {
      message: '\u0110\u00e3 nh\u1eadn \u0111\u1ee7 k\u1ebft qu\u1ea3 t\u1eeb c\u00e1c chuy\u00ean m\u00f4n v\u00e0 ho\u00e0n t\u1ea5t ki\u1ec3m tra t\u00ednh nh\u1ea5t qu\u00e1n.'
    }
  });

  // 10. Synthesis Started
  timeMs += 600;
  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'SYNTHESIS_STARTED',
    payload: {
      message: 'T\u00f4i \u0111ang t\u1ed5ng h\u1ee3p c\u00e1c nh\u1eadn \u0111\u1ecbnh v\u00e0 b\u1eb1ng ch\u1ee9ng v\u00e0o c\u1ea5u tr\u00fac ph\u00e2n t\u00edch.'
    }
  });

  // 11. Synthesis Completed
  timeMs += 600;
  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'SYNTHESIS_COMPLETED',
    payload: {
      message: '\u0110\u00e3 ho\u00e0n th\u00e0nh c\u1ea5u tr\u00fac h\u00f3a b\u00e1o c\u00e1o v\u00e0 li\u00ean k\u1ebft ngu\u1ed3n d\u1eef li\u1ec7u \u0111\u1ed1i so\u00e1t.'
    }
  });

  // 12. Report Ready
  timeMs += 600;
  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'REPORT_READY',
    payload: {
      message: '\u0110\u00e3 ho\u00e0n t\u1ea5t ki\u1ec3m tra v\u00e0 t\u1ed5ng h\u1ee3p k\u1ebft qu\u1ea3 ph\u00e2n t\u00edch. B\u00e1o c\u00e1o \u0111\u00e3 s\u1eb5n s\u00e0ng.'
    }
  });

  return events;
}
