"""E6: ask a general LLM (no tools, no data, no verifier) the ten analytic questions of Table 3.4.
One call per question, no web search (plain chat completion without tools). Output: answers.jsonl."""
import json, os, sys, time, datetime, pathlib
from openai import OpenAI
root = pathlib.Path(__file__).resolve().parents[2]
for line in (root / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"'))
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.6-luna"
Q = {
"T01":"Sức khỏe tài chính của BID trong quý 2/2026 so với các ngân hàng cùng nhóm.",
"T02":"Đánh giá chất lượng tài sản và khả năng sinh lời của STB trong quý 4/2025.",
"T03":"Tỷ lệ bao phủ nợ xấu của HDB trong quý 1/2026 là bao nhiêu?",
"T04":"Xu hướng nợ xấu và tỷ lệ bao phủ nợ xấu của CTG diễn biến thế nào trong năm 2025?",
"T05":"ROA và ROE của SHB thay đổi thế nào qua các quý năm 2025?",
"T06":"Ngân hàng nào có tỷ lệ nợ xấu thấp nhất trong quý 2/2026?",
"T07":"Xếp hạng ROE các ngân hàng trong quý 4/2025.",
"T08":"VPB đánh đổi chất lượng tài sản và khả năng sinh lời thế nào trong năm 2025 so với các ngân hàng cùng nhóm?",
"T09":"So sánh MBB và TCB trong quý 2/2026.",
"T10":"VCB hay CTG tốt hơn về chất lượng tài sản trong quý 4/2025?"}
c = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None, api_key=os.environ["OPENAI_API_KEY"])
out = root / "experiments/e6-pure-llm/answers.jsonl"
with out.open("w", encoding="utf-8") as f:
    for qid, q in Q.items():
        t = time.time()
        r = c.chat.completions.create(model=MODEL, messages=[{"role":"user","content":q}])
        f.write(json.dumps({"id":qid,"question":q,"model":MODEL,"asked_at":datetime.datetime.now().isoformat(timespec="seconds"),
            "web_search":False,"answer":r.choices[0].message.content,"tokens":r.usage.total_tokens,"seconds":round(time.time()-t,1)}, ensure_ascii=False)+"\n")
        print(qid, r.usage.total_tokens, round(time.time()-t,1), flush=True)
