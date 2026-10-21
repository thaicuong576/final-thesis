"""Add the UEH cover template and lay out the thesis sections with Word (COM).

Usage: python scripts/apply_thesis_cover.py <built.docx> [out.docx]
Needs Windows + Word (COM). Edit INFO below for names/dates/contact.

Sections after this script (UII guide, part 5-6):
  1 cover (A4, no page number)  2 secondary cover (no number)
  3 thanks .. list of figures (page numbers i, ii, ...)  4 abstract .. appendices (1, 2, 3, ...)
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
 contact="Email: cuongphungthai1@gmail.com",  # the guide also asks for a phone number on the cover: add "Điện thoại: ..." here
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
def pf_rec(par):
    f=par.Range.ParagraphFormat; fn=par.Range.Font
    return (f.Alignment,f.LineSpacingRule,f.LineSpacing,f.SpaceBefore,f.SpaceAfter,f.LeftIndent,f.FirstLineIndent,f.RightIndent,fn.Name,fn.Size)
def pf_apply(par,rec):
    f=par.Range.ParagraphFormat
    f.Alignment=rec[0]; f.LineSpacingRule=rec[1]
    if rec[1] in (3,4,5): f.LineSpacing=rec[2]
    f.SpaceBefore=rec[3]; f.SpaceAfter=rec[4]; f.LeftIndent=rec[5]; f.FirstLineIndent=rec[6]; f.RightIndent=rec[7]
    if rec[9] and rec[9]<1000:
        par.Range.Font.Size=rec[9]
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
            rec["pfs"]=[pf_rec(p) for p in tr.Paragraphs]
    except Exception: pass
    tmpl.setdefault(key(s),[]).append(rec)
# 1. insert the cover in front of the secondary cover (first paragraph of the built file)
BIA_PHU="TRƯỜNG ĐẠI HỌC KINH TẾ TP. HỒ CHÍ MINH"
def para_start(text, nth=0):
    k=0
    for p in d.Paragraphs:
        if p.Range.Text.strip()==text:
            if k==nth: return p.Range.Start
            k+=1
    raise SystemExit("paragraph not found: "+text)
r=d.Range(0,0)
r.InsertFile(cov)
def section_break_before(text):
    pos=para_start(text); d.Range(pos,pos).InsertBreak(2)  # wdSectionBreakNextPage
# the document's Normal style (justified, 1.5 lines, 6 pt) leaks into the cover text boxes: restore the template's own
seen0={}
for s_ in walk(d.Shapes):
    k=key(s_); i=seen0.get(k,0); seen0[k]=i+1
    L=tmpl.get(k)
    try:
        if L and s_.TextFrame.HasText:
            rec=L[min(i,len(L)-1)].get("pfs")
            ps_=s_.TextFrame.TextRange.Paragraphs
            if rec and ps_.Count==len(rec):
                for pr,rc in zip(ps_,rec): pf_apply(pr,rc)
    except Exception as e: print("pf restore err",k,e)
section_break_before(BIA_PHU)
section_break_before("LỜI CẢM ƠN")
section_break_before("TÓM TẮT (ABSTRACT)")
print("sections",d.Sections.Count)
assert d.Sections.Count==4
# 2. page setup and page numbers
CM=28.3465
for i in range(1,5):
    ps=d.Sections(i).PageSetup; ps.PageWidth=595.3; ps.PageHeight=841.9
    if i==1:  # the cover keeps the margins it was designed with
        ps.TopMargin=ps.BottomMargin=ps.LeftMargin=ps.RightMargin=72; ps.HeaderDistance=0; ps.FooterDistance=36
    else:
        ps.TopMargin=1.5*CM; ps.BottomMargin=2.0*CM; ps.LeftMargin=2.5*CM; ps.RightMargin=2.0*CM
        ps.HeaderDistance=1.0*CM; ps.FooterDistance=1.0*CM
for i in range(1,5):
    sec=d.Sections(i)
    if i>1: sec.Footers(1).LinkToPrevious=False; sec.Headers(1).LinkToPrevious=False
    sec.Footers(1).Range.Text=""; sec.Headers(1).Range.Text=""
for i,style in ((3,2),(4,0)):  # 2 = lower-case roman, 0 = arabic
    f=d.Sections(i).Footers(1)
    r=f.Range; r.Fields.Add(r,33)  # wdFieldPage
    f.Range.ParagraphFormat.Alignment=2  # right
    f.Range.Font.Name="Times New Roman"; f.Range.Font.Size=12
    f.PageNumbers.NumberStyle=style
    f.PageNumbers.RestartNumberingAtSection=True; f.PageNumbers.StartingNumber=1
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
        setp(ps_(4),INFO["student"]+(chr(11)+INFO["contact"] if INFO.get("contact") else "")); ps_(4).Range.ParagraphFormat.LeftIndent=0
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
for f in d.TablesOfContents: f.Update()
d.Fields.Update()
d.Save(); 
print("pages",d.ComputeStatistics(2))
d.Close(False); a.Quit()
