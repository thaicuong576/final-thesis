import { Link } from 'react-router-dom';
import { ArrowLeft, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';

export function ReportsPlaceholderPage() {
  return (
    <WorkspaceShell activeSection="reports">
      <div className="mx-auto w-full max-w-[1120px] px-5 py-10 sm:px-8 lg:px-12">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Thư viện kết quả</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-ink">Báo cáo</h1>
          <p className="mt-3 text-base leading-7 text-muted-foreground">Các báo cáo có bằng chứng và giới hạn rõ ràng sẽ được lưu tại đây sau khi có lần chạy đầu tiên.</p>
        </div>

        <Card className="mt-9 max-w-xl rounded-xl border-border/80 shadow-none">
          <CardHeader className="gap-2 space-y-0">
            <CardTitle className="flex items-center gap-2 text-lg text-ink"><FileText className="size-5 text-muted-foreground" aria-hidden="true" />Chưa có báo cáo</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-6 text-muted-foreground">Bắt đầu từ phạm vi dữ liệu hiện tại để tạo một báo cáo có thể kiểm tra.</p>
            <Button asChild className="mt-5 h-10 rounded-md px-4 font-semibold"><Link to="/analysis"><ArrowLeft data-icon="inline-start" aria-hidden="true" />Về Phân tích</Link></Button>
          </CardContent>
        </Card>
      </div>
    </WorkspaceShell>
  );
}
