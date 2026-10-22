# Nguồn Markdown của khóa luận

Các tệp ở đây là nguồn của bản nộp; bản Word được dựng bằng `scripts/build_thesis_docx.py` (không lưu trong Git).

| Tệp | Nội dung |
|---|---|
| `front-matter.md`, `dau-trang.md` | Bìa phụ, lời cảm ơn, danh mục từ viết tắt |
| `tom-tat.md` | Tóm tắt (tiếng Việt) và Abstract |
| `chuong-1-2-gioi-thieu-co-so-ly-luan.md` | Chương 1, Chương 2 và danh mục tài liệu tham khảo |
| `chuong-3-phuong-phap.md` | Chương 3: phương pháp nghiên cứu |
| `chuong-4-thiet-ke-trien-khai.md`, `chuong-4b-minh-hoa-san-pham.md` | Chương 4: thiết kế, triển khai, minh họa sản phẩm |
| `chuong-5-ket-qua-thao-luan.md` | Chương 5: kết quả và thảo luận |
| `chuong-6-ket-luan.md` | Chương 6: kết luận, hạn chế, hướng phát triển |
| `phu-luc.md`, `phu-luc-b1-nguon-bao-cao.csv` | Phụ lục A đến D, danh sách 101 báo cáo nguồn |
| `figures/`, `screenshots/` | Sơ đồ Mermaid, biểu đồ và ảnh chụp màn hình dùng trong bài |
| `thuat-ngu.md` | Danh sách thuật ngữ kỹ thuật đã được thay bằng cách diễn đạt khác trong bài |

## Dựng bản Word (Windows, cần Microsoft Word)

```bash
export THESIS_DEMO_PASSWORD='<mật khẩu tài khoản dùng thử>'   # điền vào Phụ lục A, không lưu trong Git
export THESIS_PHONE='<số điện thoại>' THESIS_EMAIL='<email>'    # dòng liên hệ trên bìa
python scripts/build_thesis_docx.py --template <mẫu .docx của khoa> --out base.docx
python scripts/apply_thesis_cover.py base.docx out.docx          # ghép bìa UEH, đánh số trang
```

Mẫu `.docx` của khoa và bìa không nằm trong kho mã. Sau khi mở Word, nhấn Ctrl+A rồi F9 để cập nhật mục lục. Số liệu ở Chương 5 và Phụ lục C tính từ `experiments/`.
