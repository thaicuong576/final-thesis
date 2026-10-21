"""Replace the generated title page of the thesis .docx with the UEH cover template.

Usage: python scripts/apply_thesis_cover.py <built.docx> [out.docx]
Needs Windows + Word (COM). Edit INFO below for names/dates.
"""
import win32com.client as w, os, sys, shutil
sys.stdout.reconfigure(encoding="utf-8")
B=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","docs","thesis-v2","build"))
src=os.path.abspath(sys.argv[1]); cov=os.path.join(B,"Bìa templatedocx.docx")
out=os.path.abspath(sys.argv[2] if len(sys.argv)>2 else sys.argv[1])
INFO=dict(
 title="THIẾT KẾ VÀ ĐÁNH GIÁ HỆ THỐNG ĐA TÁC TỬ HỖ TRỢ TỔNG HỢP THÔNG TIN VÀ PHÂN TÍCH CƠ BẢN CÁC NGÂN HÀNG NIÊM YẾT TẠI VIỆT NAM",
 kind="KHÓA LUẬN TỐT NGHIỆP",
 advisor="Giảng viên hướng dẫn: Lê Văn",
 student="Phùng Thái Cường - 31231024489 - Lớp FEP001",
 date="Hồ Chí Minh, ngày 21 tháng 10 năm 2026")
if src!=out: shutil.copy(src,out)
a=w.Dispatch("Word.Application"); a.Visible=False; a.DisplayAlerts=0
d=a.Documents.Open(out)
T=a.Documents.Open(cov,ReadOnly=True)
def walk(shapes):
    for s in shapes:
        if s.Type==6: yield from walk(s.GroupItems)
        else: yield s
def key(s): return (s.Name, round(s.Width), round(s.Height))
tmpl={}
for s in walk(T.Shapes):
    rec={}
    try:
        rec["fill"]=(s.Fill.Visible, s.Fill.ForeColor.RGB)
        rec["line"]=(s.Line.Visible, s.Line.ForeColor.RGB)
    except Exception: pass
    try:
        if s.TextFrame.HasText:
            tr=s.TextFrame.TextRange
            rec["chars"]=[c.Font.Color for c in tr.Characters]
    except Exception: pass
    tmpl.setdefault(key(s),[]).append(rec)
# 1. remove old front-matter paragraphs (everything before "MỤC LỤC")
n=0
for i,p in enumerate(d.Paragraphs):
    if p.Range.Text.strip()=="MỤC LỤC": n=i+1; break
start=d.Paragraphs(1).Range.Start; end=d.Paragraphs(n).Range.Start
d.Range(start,end).Delete()
# 2. insert cover + next-page section break
r=d.Range(0,0)
r.InsertFile(cov)
r=d.Range(0,0)
# the cover file ends with its own last paragraph; add section break after cover content
cov_end=None
for i,p in enumerate(d.Paragraphs):
    if p.Range.Text.strip()=="MỤC LỤC": cov_end=p.Range.Start; break
d.Range(cov_end,cov_end).InsertBreak(2)  # wdSectionBreakNextPage
print("sections",d.Sections.Count)
# 3. section 2 keeps footer, section 1 cover has none; A4 cover
s1,s2=d.Sections(1),d.Sections(2)
s2.Footers(1).LinkToPrevious=False
s1.Footers(1).Range.Text=""
s1.Headers(1).Range.Text=""
ps=s1.PageSetup; ps.PageWidth=595.45; ps.PageHeight=841.7
# page numbering of section 2 restarts at 1? keep continuous but start at 1
s2.Footers(1).PageNumbers.RestartNumberingAtSection=True
s2.Footers(1).PageNumbers.StartingNumber=1
# 4. replace text in shapes
def setp(par,text,fix=True):
    r=par.Range; r.MoveEnd(1,-1); r.Text=text
    if fix:
        pf=par.Range.ParagraphFormat
        pf.FirstLineIndent=0; pf.Alignment=0
        try: par.Range.ListFormat.RemoveNumbers()
        except Exception: pass
for s in walk(d.Shapes):
    try:
        if not s.TextFrame.HasText: continue
    except Exception: continue
    tr=s.TextFrame.TextRange; t=tr.Text
    if "TÁC ĐỘNG" in t: setp(tr.Paragraphs(1),INFO["title"]); tr.Paragraphs(1).Range.ParagraphFormat.LeftIndent=35
    elif t.strip()=="TIỂU LUẬN":
        setp(tr.Paragraphs(1),INFO["kind"]); tr.Font.Size=30; s.Left=s.Left-34
    elif "Hồ Chí Minh, ngày" in t: setp(tr.Paragraphs(1),INFO["date"],False)
    elif "Môn học" in t:
        ps_=tr.Paragraphs
        setp(ps_(2),INFO["advisor"])
        setp(ps_(4),INFO["student"]); ps_(4).Range.ParagraphFormat.LeftIndent=0
        # delete paragraphs 5,6,7 then 1
        for k in (7,6,5,1): ps_(k).Range.Delete()
seen={}
for s_ in walk(d.Shapes):
    k=key(s_); i=seen.get(k,0); seen[k]=i+1
    L=tmpl.get(k)
    if not L: 
        # edited boxes change size? match by name only on fallback
        continue
    rec=L[min(i,len(L)-1)]
    try:
        if "fill" in rec:
            s_.Fill.Visible=rec["fill"][0]
            if rec["fill"][0]: s_.Fill.ForeColor.RGB=rec["fill"][1]
        if "line" in rec:
            s_.Line.Visible=rec["line"][0]
            if rec["line"][0]: s_.Line.ForeColor.RGB=rec["line"][1]
    except Exception as e: print("fill err",k,e)
    try:
        if s_.TextFrame.HasText and "chars" in rec:
            tr=s_.TextFrame.TextRange; cols=rec["chars"]
            if tr.Characters.Count==len(cols):
                for ch,col in zip(tr.Characters,cols):
                    if col!=9999999: ch.Font.Color=col
            else:
                c0=cols[0]
                if c0!=9999999: tr.Font.Color=c0
    except Exception as e: print("txt err",k,e)
T.Close(False)
for s_ in walk(d.Shapes):
    try:
        if s_.TextFrame.HasText and "VIỆN ĐỔI MỚI" in s_.TextFrame.TextRange.Text:
            f=s_.TextFrame.TextRange.Find
            r=s_.TextFrame.TextRange; 
            rr=r.Duplicate; rr.Find.Execute("VIỆN ĐỔI MỚI SÁNG TẠO"); rr.Font.Color=0xA6A6A6
    except Exception as e: print("gray err",e)
for s_ in walk(d.Shapes):
    try:
        if s_.TextFrame.HasText:
            tt=s_.TextFrame.TextRange.Text
            if "ĐẠI HỌC KINH TẾ" in tt:
                pf=s_.TextFrame.TextRange.ParagraphFormat
                print("hdr spacing",pf.LineSpacingRule,pf.LineSpacing,pf.SpaceBefore,pf.SpaceAfter)
                pf.LineSpacingRule=0; pf.SpaceBefore=0
            if "VIỆN ĐỔI MỚI" in tt:
                f=s_.TextFrame.TextRange.Duplicate
                if f.Find.Execute("KẾ     VIỆN"): f.Text="KẾ"+" "*8+"   VIỆN"
                g=s_.TextFrame.TextRange.Duplicate
                if g.Find.Execute("VIỆN ĐỔI MỚI SÁNG TẠO"): g.Font.Color=0xA6A6A6
    except Exception as e: print("hdr err",e)
for f in d.TablesOfContents: f.Update()
d.Fields.Update()
d.Save(); 
print("pages",d.ComputeStatistics(2))
d.Close(False); a.Quit()
