import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import type { ParsedScope } from '@/features/analysis-composer/model/types';
import { parseAnalysisQuestion } from '@/features/analysis-composer/model/intentParser';
import type { AnalysisStreamRequest } from '@/features/analysis-session/useAnalysisSessionStream';

export type SupportedStreamRequest =
  | { request: AnalysisStreamRequest; reason: null }
  | { request: null; reason: string };

/** The current SSE API accepts one target, optional peers, and one year or quarter. */
export function buildSupportedStreamRequest(
  question: string,
  scope: ParsedScope,
  capabilities: AnalysisCapabilities
): SupportedStreamRequest {
  if (capabilities.analysis_available !== true) {
    const status = capabilities.database_status;
    const detail = status ? ` Trạng thái kho dữ liệu: ${status}.` : '';
    return {
      request: null,
      reason: `API chưa xác nhận có snapshot dữ liệu đã kiểm định để chạy phân tích.${detail}`
    };
  }

  if (!capabilities.dataset_snapshot_id?.trim()) {
    return {
      request: null,
      reason: 'API chưa công bố mã snapshot dữ liệu đã kiểm định cho phiên này.'
    };
  }

  if (scope.entities.length === 0) {
    return { request: null, reason: 'API hiện cần một ngân hàng mục tiêu. Hãy nêu mã ngân hàng trong câu hỏi.' };
  }

  const normalizedQuestion = question.toLowerCase();
  const unnamedEntities = scope.entities.filter((entity) =>
    !normalizedQuestion.includes(entity.ticker.toLowerCase()) &&
    !normalizedQuestion.includes(entity.name.toLowerCase())
  );
  if (unnamedEntities.length > 0) {
    return {
      request: null,
      reason: `Câu hỏi chưa nêu rõ ${unnamedEntities.map((entity) => entity.ticker).join(', ')}. Hãy chỉnh câu hỏi để phạm vi xác nhận khớp với yêu cầu gửi đi.`
    };
  }

  const mentionedEntities = capabilities.entities.filter((entity) =>
    normalizedQuestion.includes(entity.ticker.toLowerCase()) ||
    normalizedQuestion.includes(entity.name.toLowerCase())
  );
  if (
    mentionedEntities.length > 0 &&
    mentionedEntities.map((entity) => entity.id).sort().join(',') !==
      scope.entities.map((entity) => entity.id).sort().join(',')
  ) {
    return {
      request: null,
      reason: 'Danh sách ngân hàng trong câu hỏi chưa khớp với phạm vi đang xác nhận. Hãy sửa câu hỏi hoặc chọn lại toàn bộ ngân hàng được nêu.'
    };
  }

  const implementedCapabilities = new Set(
    (capabilities.implemented_capabilities ?? []).map((capability) => capability.toLowerCase())
  );
  const capabilityNames: Record<string, string> = {
    company: 'company',
    peer: 'sector',
    macro: 'macro'
  };
  const unsupportedCapabilities = scope.analysisPlan.selectedCapabilities
    .map((capability) => capabilityNames[capability.id] ?? capability.id)
    .filter((capability) => !implementedCapabilities.has(capability));
  if (unsupportedCapabilities.length > 0) {
    return {
      request: null,
      reason: `API hiện chưa triển khai năng lực ${unsupportedCapabilities.join(', ')} cho snapshot này.`
    };
  }

  const periods = scope.periods;
  if (periods.length === 0) {
    return { request: null, reason: 'Chưa chọn kỳ dữ liệu để phân tích.' };
  }

  const explicitPeriodInQuestion = /\b(?:19|20)\d{2}\b|\bq[1-4]\b|quý\s*[1-4]/i.test(question);
  if (!explicitPeriodInQuestion) {
    return {
      request: null,
      reason: 'Câu hỏi cần nêu rõ năm hoặc quý. API không thể nhận kỳ mặc định từ phạm vi xem trước.'
    };
  }

  const hasExplicitMetric = capabilities.metrics.some((metric) =>
    normalizedQuestion.includes(metric.acronym.toLowerCase()) ||
    normalizedQuestion.includes(metric.label.toLowerCase())
  );
  if (!hasExplicitMetric) {
    return {
      request: null,
      reason: 'Câu hỏi cần nêu rõ chỉ tiêu được hỗ trợ. API không thể nhận chỉ tiêu mặc định từ phạm vi xem trước.'
    };
  }

  let period: string;
  if (periods.length === 1) {
    period = `${periods[0].year}_Q${periods[0].quarter}`;
  } else {
    const year = periods[0].year;
    const quarters = [...new Set(periods.filter((item) => item.year === year).map((item) => item.quarter))].sort();
    if (periods.length !== 4 || quarters.join(',') !== '1,2,3,4') {
      return {
        request: null,
        reason: 'API hiện chỉ xử lý một quý hoặc một năm đầy đủ. Hãy chọn đúng một quý hoặc Q1–Q4 của cùng một năm.'
      };
    }
    period = String(year);
  }

  const detectedMetricIds = parseAnalysisQuestion(question, capabilities).scope.metrics.map((metric) => metric.id).sort();
  const selectedMetricIds = scope.metrics.map((metric) => metric.id).sort();
  if (detectedMetricIds.join(',') !== selectedMetricIds.join(',')) {
    return {
      request: null,
      reason: 'API hiện suy ra chỉ tiêu từ câu hỏi và chưa nhận danh sách chỉ tiêu chỉnh tay. Hãy sửa câu hỏi để nêu đúng các chỉ tiêu đã chọn.'
    };
  }

  const questionPeriods = parseAnalysisQuestion(question, capabilities).scope.periods
    .map((item) => item.id)
    .sort();
  const selectedPeriods = scope.periods.map((item) => item.id).sort();
  if (questionPeriods.join(',') !== selectedPeriods.join(',')) {
    return {
      request: null,
      reason: 'Kỳ dữ liệu đã chọn khác kỳ được nêu trong câu hỏi. Hãy sửa câu hỏi để phạm vi hiển thị khớp với yêu cầu gửi đi.'
    };
  }

  return {
    request: {
      query: question,
      target_ticker: scope.entities[0].ticker,
      peer_tickers: scope.entities.slice(1).map((entity) => entity.ticker),
      period
    },
    reason: null
  };
}
