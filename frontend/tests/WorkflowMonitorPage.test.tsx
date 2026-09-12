import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { WorkflowMonitorPage } from '../src/pages/workflow/WorkflowMonitorPage';

function renderWorkflowPage(initialUrl = '/analysis/test-run?scenario=COMPANY_ONLY') {
  return render(
    <MemoryRouter initialEntries={[initialUrl]}>
      <Routes>
        <Route path="/analysis/:runId" element={<WorkflowMonitorPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('WorkflowMonitorPage (Clean-Room Screen 2 - Live Multi-Agent Workflow)', () => {
  it('Scenario A: Company-only run renders Orchestrator + 1 specialist, omitting inactive specialists', async () => {
    renderWorkflowPage('/analysis/test-run?scenario=COMPANY_ONLY');

    // 1. Top bar question & scope
    expect(screen.getByText(/ROE của TCB thay đổi thế nào trong năm 2024/)).toBeInTheDocument();
    expect(screen.getByText('TCB · Q1–Q4/2024 · ROE')).toBeInTheDocument();
    expect(screen.getByText('Ngân hàng Việt Nam 2024')).toBeInTheDocument();

    // 2. Orchestrator Card
    expect(screen.getByRole('heading', { name: 'Tác tử Điều phối' })).toBeInTheDocument();
    expect(
      screen.getByText(/Yêu cầu phân tích đơn mục tiêu tập trung vào một doanh nghiệp/)
    ).toBeInTheDocument();

    // 3. Active specialist: Company ONLY
    expect(screen.getByRole('heading', { name: 'Phân tích Doanh nghiệp' })).toBeInTheDocument();
    expect(screen.getByText('TCB')).toBeInTheDocument();
    expect(screen.getByText(/Đang đọc dữ liệu ROE của TCB cho Q1–Q4\/2024/)).toBeInTheDocument();

    // 4. Inactive specialists (Peer & Macro) must NOT have any DOM presence
    expect(screen.queryByRole('heading', { name: 'Nhóm tham chiếu' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Bối cảnh vĩ mô' })).not.toBeInTheDocument();
  });

  it('Scenario B: Company + Peer run renders both active specialists and omits Macro', async () => {
    renderWorkflowPage('/analysis/test-run?scenario=COMPANY_PEER');

    // 1. Question & scope signature
    expect(screen.getByText(/TCB sinh lời tốt hơn hay kém nhóm so sánh/)).toBeInTheDocument();
    expect(screen.getByText('TCB · Q1–Q4/2024 · ROA · ROE')).toBeInTheDocument();

    // 2. Orchestrator active badges
    expect(screen.getByRole('heading', { name: 'Tác tử Điều phối' })).toBeInTheDocument();
    expect(
      screen.getByText(/Yêu cầu so sánh tương đối giữa doanh nghiệp mục tiêu và nhóm ngang hàng/)
    ).toBeInTheDocument();

    // 3. Both Company and Peer specialists must be rendered
    expect(screen.getByRole('heading', { name: 'Phân tích Doanh nghiệp' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Nhóm tham chiếu' })).toBeInTheDocument();
    expect(screen.getByText('Đối sánh dữ liệu ngang hàng với Nhóm 5 ngân hàng')).toBeInTheDocument();

    // 4. Macro is inactive and must NOT be rendered
    expect(screen.queryByRole('heading', { name: 'Bối cảnh vĩ mô' })).not.toBeInTheDocument();
  });

  it('Scenario C: Targeted Revision renders Peer in revision while Company remains unaffected', async () => {
    renderWorkflowPage('/analysis/test-run?scenario=TARGETED_REVISION');

    // 1. Overall Orchestrator status indicates revision
    expect(
      screen.getByText(/So sánh chất lượng tài sản và tỷ lệ bao phủ nợ xấu của TCB/)
    ).toBeInTheDocument();
    expect(screen.getByText('Đang hiệu chỉnh · Vòng 1/2')).toBeInTheDocument();
    expect(
      screen.getByText(/sai lệch kỳ đối sánh ở Chuyên gia Nhóm tham chiếu/)
    ).toBeInTheDocument();

    // 2. Company specialist remains COMPLETED (unaffected by Peer revision)
    expect(screen.getByRole('heading', { name: 'Phân tích Doanh nghiệp' })).toBeInTheDocument();
    expect(screen.getByText('Đã hoàn tất')).toBeInTheDocument();

    // 3. Peer specialist displays revision status and orchestrator feedback
    expect(screen.getByRole('heading', { name: 'Nhóm tham chiếu' })).toBeInTheDocument();
    expect(
      screen.getByText(/Yêu cầu hiệu chỉnh \(Vòng 1\/2\)/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Chỉ tiêu bao phủ nợ xấu \(Coverage\) của nhóm tham chiếu chưa đồng nhất kỳ đối sánh với TCB/)
    ).toBeInTheDocument();
  });

  it('allows clicking an active specialist to open the detailed activity sheet', async () => {
    const user = userEvent.setup();
    renderWorkflowPage('/analysis/test-run?scenario=COMPANY_ONLY');

    // Find and click "Chi tiết hoạt động" on Company specialist card
    const detailBtn = screen.getByRole('button', { name: /Chi tiết hoạt động/i });
    await user.click(detailBtn);

    // Dialog/Sheet should be opened
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText('Nhiệm vụ được giao')).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Tính toán ROE từng quý và lũy kế năm 2024 của Ngân hàng Kỹ thương/i)
    ).toBeInTheDocument();

    // Observable activity trace
    expect(within(dialog).getByText(/Nhật ký hoạt động quan sát được/)).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Báo cáo tài chính hợp nhất kiểm toán 2024 \(TCB\)/)
    ).toBeInTheDocument();

    // Preliminary findings
    expect(within(dialog).getByText(/Kết quả phân tích có dẫn chứng/)).toBeInTheDocument();
    expect(within(dialog).getByText('16.8%')).toBeInTheDocument();
  });

  it('allows switching between scenarios using the top bar switcher', async () => {
    const user = userEvent.setup();
    renderWorkflowPage('/analysis/test-run?scenario=COMPANY_ONLY');

    // Initially Scenario A
    expect(screen.getByText(/ROE của TCB thay đổi thế nào trong năm 2024/)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Nhóm tham chiếu' })).not.toBeInTheDocument();

    // Switch to Scenario B
    const scenarioBBtn = screen.getByRole('button', { name: /B\. Doanh nghiệp \+ Đối sánh/i });
    await user.click(scenarioBBtn);

    // Now Scenario B is active
    expect(await screen.findByText(/TCB sinh lời tốt hơn hay kém nhóm so sánh/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Nhóm tham chiếu' })).toBeInTheDocument();

    // Switch to Scenario C
    const scenarioCBtn = screen.getByRole('button', { name: /C\. Hiệu chỉnh tập trung/i });
    await user.click(scenarioCBtn);

    // Now Scenario C is active
    expect(
      await screen.findByText(/So sánh chất lượng tài sản và tỷ lệ bao phủ nợ xấu của TCB/)
    ).toBeInTheDocument();
    expect(screen.getByText('Đang hiệu chỉnh · Vòng 1/2')).toBeInTheDocument();
  });
});