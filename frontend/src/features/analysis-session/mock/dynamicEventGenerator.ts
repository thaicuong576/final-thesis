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

  const selectedCaps = scope.analysisPlan?.selectedCapabilities || [];

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

  let planSummary = 'Kh\u00f4ng y\u00eau c\u1ea7u chuy\u00ean m\u00f4n';
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

  const planMessage =
    selectedCaps.length > 0
      ? '\u0110\u00e3 x\u00e1c \u0111\u1ecbnh ph\u1ea1m vi ' + scopeSignature + '. Y\u00eau c\u1ea7u n\u00e0y c\u1ea7n ' + capLabels.toLowerCase() + '. \u0110\u00e3 giao ' + selectedCaps.length + ' nhi\u1ec7m v\u1ee5 chuy\u00ean m\u00f4n.'
      : '\u0110\u00e3 x\u00e1c \u0111\u1ecbnh ph\u1ea1m vi ' + scopeSignature + '. Y\u00eau c\u1ea7u kh\u00f4ng c\u1ea7n kh\u1edfi t\u1ea1o nhi\u1ec7m v\u1ee5 chuy\u00ean m\u00f4n.';

  events.push({
    eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
    sequence: seq++,
    occurredAtMs: timeMs,
    type: 'PLAN_CREATED',
    payload: {
      requiredSpecialists: capIds,
      planSummary,
      message: planMessage
    }
  });

  // Terminal Edge Case: Empty Analysis Plan must emit RUN_BLOCKED and stop without report synthesis
  if (selectedCaps.length === 0) {
    timeMs += 400;
    events.push({
      eventId: 'evt-dyn-' + String(seq).padStart(2, '0'),
      sequence: seq++,
      occurredAtMs: timeMs,
      type: 'RUN_BLOCKED',
      payload: {
        reason:
          'Không có chuyên môn phân tích phù hợp với yêu cầu trong phạm vi dữ liệu hiện tại.'
      }
    });
    return events;
  }

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
    let descValidation = 'Đã kiểm tra tính hợp lệ của nguồn dữ liệu';
    if (cap.id === 'company') {
      descValidation = 'Đã kiểm tra các quan sát số liệu hợp lệ cho ' + metricLabels;
    } else if (cap.id === 'peer') {
      descValidation = 'Đã chuẩn hóa định dạng và đối soát số liệu nhóm tham chiếu';
    } else if (cap.id === 'macro') {
      descValidation = 'Đã đối chiếu chuỗi thời gian số liệu vĩ mô liên quan';
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

  // 7. Specialist Output Created (Grounded, structural observations)
  selectedCaps.forEach((cap) => {
    timeMs += 600;
    let headline = '3 nhận định cấu trúc · 4 quan sát số liệu';
    let findings: string[] = [];

    if (cap.id === 'company') {
      headline = '3 nhận định cấu trúc · ' + (entitySymbols ? 'Dữ liệu ' + entitySymbols : 'Báo cáo tài chính');
      findings = [
        'Đã tạo 3 nhận định cấu trúc từ chuỗi số liệu ' + metricLabels + ' của ' + entitySymbols + ' (' + periodLabels + ').',
        'Toàn bộ các quan sát số liệu đã được đối soát nguồn gốc từ báo cáo tài chính kiểm toán.',
        'Đã xác thực tính nhất quán và hoàn thiện liên kết dẫn chứng số liệu.'
      ];
    } else if (cap.id === 'peer') {
      headline = '3 nhận định đối sánh · 6 dẫn chứng';
      findings = [
        'Đã hoàn tất đối sánh cùng kỳ chỉ số ' + metricLabels + ' với nhóm tham chiếu cho chu kỳ ' + periodLabels + '.',
        'Các điểm dữ liệu nhóm tham chiếu đã được đồng bộ cùng kỳ báo cáo tài chính.',
        '6 dẫn chứng đối sánh đã được trích xuất và liên kết với chuỗi quan sát chuẩn hóa.'
      ];
    } else if (cap.id === 'macro') {
      headline = '2 nhận định bối cảnh · 4 dẫn chứng';
      findings = [
        'Đã trích xuất chuỗi thời gian lãi suất điều hành và bối cảnh vĩ mô khả dụng cho chu kỳ ' + periodLabels + '.',
        '4 dẫn chứng bối cảnh vĩ mô toàn ngành đã được đối chiếu đồng bộ theo quý.'
      ];
    } else {
      headline = '2 nhận định chuyên môn · 3 dẫn chứng';
      findings = [
        'Dữ liệu chuyên môn cho ' + cap.label + ' đã được trích xuất từ nguồn dữ liệu chuẩn hóa.',
        'Các tiêu chí phân tích đã được kiểm tra theo phương pháp luận quy chuẩn.'
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
      message:
        selectedCaps.length > 0
          ? 'Đã nhận đủ kết quả từ các chuyên môn và hoàn tất kiểm tra tính nhất quán.'
          : 'Đã hoàn tất kiểm tra yêu cầu và tính hợp lệ của phạm vi phân tích.'
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
