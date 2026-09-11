import { z } from 'zod';

export const analysisRequestSchema = z.object({
  objective: z.string().trim().min(1, 'Mục tiêu phân tích là bắt buộc.').max(500, 'Mục tiêu phân tích tối đa 500 ký tự.'),
  analysisTargetIds: z.array(z.string()).min(1, 'Chọn ít nhất một đối tượng phân tích.'),
  periodIds: z.array(z.string()).min(1, 'Chọn ít nhất một kỳ tài chính.'),
  metricIds: z.array(z.string()).min(1, 'Chọn ít nhất một chủ đề hoặc chỉ tiêu.')
});

export type AnalysisFormValues = z.infer<typeof analysisRequestSchema>;
