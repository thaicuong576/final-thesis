import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Database, Check, Plus } from 'lucide-react';

interface DatasetSelectorSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectDataset?: (datasetId: string) => void;
}

export function DatasetSelectorSheet({
  open,
  onOpenChange,
  onSelectDataset
}: DatasetSelectorSheetProps) {
  function handleSelect(datasetId: string) {
    onSelectDataset?.(datasetId);
    onOpenChange(false);
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md bg-white p-6 flex flex-col justify-between overflow-y-auto"
      >
        <div className="space-y-6">
          <SheetHeader className="text-left space-y-1 pb-2 border-b border-line">
            <SheetTitle className="text-base font-semibold text-ink flex items-center gap-2">
              <Database className="w-4 h-4 text-[#1c5d9c]" />
              <span>Nguồn dữ liệu phân tích</span>
            </SheetTitle>
            <SheetDescription className="text-xs text-muted">
              Chọn tập dữ liệu đã được xác thực cho động cơ phân tích đa tác tử.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-4">
            {/* Active Verified Dataset */}
            <div className="border-2 border-[#1c5d9c] bg-[#f5f8fb] rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-ink">
                  Ngân hàng Việt Nam 2024
                </span>
                <Badge
                  variant="outline"
                  className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] text-[10px] gap-1 font-semibold"
                >
                  <Check className="w-3 h-3 text-[#2f6f5e]" />
                  Đang kích hoạt
                </Badge>
              </div>

              <div className="text-[11px] text-muted space-y-1.5 leading-relaxed">
                <div>
                  <strong className="text-ink font-medium">Doanh nghiệp:</strong>{' '}
                  ACB · TCB · VPB · MBB · VCB
                </div>
                <div>
                  <strong className="text-ink font-medium">Thời gian:</strong> Q1–Q4/2024 (4 kỳ)
                </div>
                <div>
                  <strong className="text-ink font-medium">Chỉ tiêu:</strong> NPL · Coverage · ROA · ROE
                </div>
                <div>
                  <strong className="text-ink font-medium">Vĩ mô:</strong> Hạn chế (Tăng trưởng tín dụng, lãi suất điều hành)
                </div>
              </div>

              <Button
                disabled
                size="sm"
                className="w-full bg-[#1c5d9c] text-white opacity-85 text-xs font-semibold cursor-default h-8"
              >
                Đang sử dụng nguồn này
              </Button>
            </div>

            {/* Inactive Dataset 1 */}
            <div className="border border-line bg-white rounded-lg p-4 space-y-3 hover:border-slate-400 transition">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-ink">
                  Ngân hàng Việt Nam 2020–2023
                </span>
                <Badge variant="outline" className="text-[10px] text-muted font-normal">
                  Chưa kết nối
                </Badge>
              </div>

              <div className="text-[11px] text-muted space-y-1.5 leading-relaxed">
                <div>
                  <strong className="text-ink font-medium">Doanh nghiệp:</strong> 10 ngân hàng niêm yết
                </div>
                <div>
                  <strong className="text-ink font-medium">Thời gian:</strong> 2020–2023 (16 quý)
                </div>
                <div>
                  <strong className="text-ink font-medium">Chỉ tiêu:</strong> Bộ chỉ số CAMEL mở rộng
                </div>
                <div>
                  <strong className="text-ink font-medium">Vĩ mô:</strong> Đầy đủ chu kỳ
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSelect('vn-banks-2020-2023')}
                className="w-full border-line hover:bg-canvas text-xs font-semibold text-ink h-8"
              >
                Chọn nguồn này
              </Button>
            </div>

            {/* Inactive Dataset 2 */}
            <div className="border border-line bg-white rounded-lg p-4 space-y-2 opacity-80">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-ink">
                  Chứng khoán Việt Nam 2024
                </span>
                <Badge variant="outline" className="text-[10px] text-muted font-normal">
                  Đang chuẩn bị
                </Badge>
              </div>

              <div className="text-[11px] text-muted space-y-1">
                <div>Top 5 công ty chứng khoán niêm yết (SSI, VND, VCI, HCM, TCBS)</div>
              </div>
            </div>

            {/* Lightweight Connection Flow (Section 16) */}
            <div className="p-4 bg-canvas border border-dashed border-line rounded-lg text-center space-y-2">
              <div className="text-xs font-semibold text-ink">
                Thêm / kết nối nguồn dữ liệu
              </div>
              <p className="text-[11px] text-muted leading-relaxed">
                Nguồn → Nhận diện → Kiểm tra → Sẵn sàng phân tích. Hỗ trợ CSV/Excel, Cơ sở dữ liệu và BCTC.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => alert('Quy trình kết nối dữ liệu: Nguồn → Nhận diện → Kiểm tra → Sẵn sàng.')}
                className="border-[#c4daf0] text-[#1c5d9c] hover:bg-[#f0f5fa] text-xs font-semibold h-8 gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Kết nối nguồn mới</span>
              </Button>
            </div>
          </div>
        </div>

        <SheetFooter className="pt-4 border-t border-line mt-6 sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="w-full sm:w-auto border-line text-xs font-semibold"
          >
            Đóng
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
