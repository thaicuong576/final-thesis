import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { HeroComposer } from '../src/features/analysis-composer/components/HeroComposer';

describe('HeroComposer scope cues', () => {
  it('adds only the chosen bank and leaves period and metric for the analyst to state', async () => {
    const user = userEvent.setup();
    render(
      <HeroComposer
        availableEntities={[{ id: 'tcb', ticker: 'TCB', name: 'Ngân hàng Kỹ thương Việt Nam' }]}
        availablePeriods={[1, 2, 3, 4].map((quarter) => ({ id: `2024-q${quarter}`, year: 2024, quarter }))}
        availableMetrics={[{ id: 'roe', acronym: 'ROE', label: 'Tỷ suất sinh lời trên vốn chủ sở hữu', topicId: 'profitability' }]}
        onSubmit={vi.fn()}
      />
    );

    await user.click(screen.getByRole('button', { name: '+ TCB' }));

    const question = screen.getByRole('textbox', { name: 'Câu hỏi phân tích' }) as HTMLTextAreaElement;
    expect(question).toHaveValue('Phân tích TCB');
    expect(question.value).not.toMatch(/ROE|2024|Q[1-4]/);
    expect(question.placeholder).toContain('một chỉ tiêu và kỳ dữ liệu');
  });
});
