#!/usr/bin/env python3
"""从 specs/*.txt 生成 A4 抽查单（家长照着问，孩子口头答，逐项打勾）。

用法:
  python3 generate_check.py specs/20260825.txt --pdf              # HTML + PDF
  python3 generate_check.py specs/20260825.txt                    # 只出 HTML（先在浏览器看排版）
  python3 generate_check.py --pdf                                 # 不给 spec 就用 specs/ 里最新改动的那份
  python3 generate_check.py specs/20260825.txt --answers --pdf    # 家长版（把答案印出来）

输出: sheets/<spec 同名>.html，加 --pdf 时同时导出同名 .pdf。一张单子一页。
两版分开印：题面版给孩子（答案不印，动笔题空着写），家长版给家长（答案全印，照着问、照着改）。
"""
import html
import re
import subprocess
import sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 12mm 14mm; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: "PingFang SC", "Hiragino Sans GB", "Songti SC", sans-serif;
    color: #111; font-size: 13px;
    /* 打印时保留背景/边框颜色，否则勾选框和块头底色全没了 */
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  /* 屏幕预览时模拟 A4 纸张 */
  @media screen {{
    body {{ background: #888; padding: 20px 0; }}
    .page {{
      width: 210mm; height: 297mm; margin: 0 auto 20px;
      background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.4);
      padding: 12mm 14mm;
    }}
  }}
  /* 一张单子一页：撑满 A4，总评区钉底 */
  .page {{ display: flex; flex-direction: column; }}
  @media print {{ .page {{ height: 273mm; }} }}
  .page + .page {{ page-break-before: always; }}

  .header {{
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 2px solid #111; padding-bottom: 6px; margin-bottom: 3mm;
  }}
  .header h1 {{ font-size: 16px; padding-right: 10px; }}
  .header h1 small {{ font-size: 12px; font-weight: 400; color: #666; }}
  .header .info {{ font-size: 12px; white-space: nowrap; }}
  .header .info span {{ margin-left: 10px; }}
  .header .info b {{ color: #42688F; }}
  .blank {{ display: inline-block; border-bottom: 1px solid #111; width: 42px; }}

  .hint {{
    font-size: 12px; color: #35536f; background: #E7EEF6;
    border-left: 3px solid #42688F; border-radius: 0 4px 4px 0;
    padding: 4px 9px; margin-bottom: 4mm;
  }}

  .blocks {{ flex: 0 0 auto; }}
  .block {{ margin-bottom: 4mm; break-inside: avoid; }}
  .bh {{
    display: flex; align-items: baseline; gap: 6px;
    border-bottom: 1px solid #C7D3E0; padding-bottom: 3px; margin-bottom: 2.5mm;
  }}
  .bh .no {{
    flex: 0 0 auto; width: 5.5mm; height: 5.5mm; border-radius: 50%;
    background: #42688F; color: #fff; font-size: 10px;
    display: grid; place-items: center; align-self: center;
  }}
  .bh h2 {{
    flex: 1 1 auto; font-family: "Kaiti SC", "STKaiti", "Songti SC", serif;
    font-size: 16px; font-weight: 700;
  }}
  .bh h2 small {{ font-size: 12px; font-weight: 400; color: #666; }}
  .bh .meta {{ flex: 0 0 auto; font-size: 11px; color: #666; white-space: nowrap; }}
  .bh .meta em {{ font-style: normal; color: #42688F; }}
  .bh .meta i {{
    font-style: normal; margin-left: 8px; color: #b3423f;
    background: #FAE9E7; border-radius: 3px; padding: 1px 5px;
  }}
  .note {{ font-size: 11px; color: #777; margin-bottom: 2mm; }}

  /* 勾选框：家长边问边打勾 */
  .tick {{
    flex: 0 0 auto; width: 4.6mm; height: 4.6mm;
    border: 1pt solid #42688F; border-radius: 1mm; background: #fff;
  }}

  /* 词语网格：两列，一项一格 */
  .items {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2mm 6mm; }}
  .items .it {{ display: flex; align-items: center; gap: 2.5mm; }}
  .items .q {{
    font-family: "Kaiti SC", "STKaiti", "Songti SC", serif;
    font-size: 15px; white-space: nowrap;
  }}
  .items .a {{ font-size: 11px; color: #b3423f; font-family: "Times New Roman", serif; }}
  .items .dots {{ flex: 1 1 auto; border-bottom: 1px dotted #ccc; }}

  /* 整行问答：题面长、答案长的用这个 */
  .ask {{ display: flex; align-items: flex-start; gap: 2.5mm; margin-bottom: 2mm; }}
  .ask .tick {{ margin-top: .6mm; }}
  .ask .body {{ flex: 1 1 auto; min-width: 0; }}
  .ask .q {{ font-family: "Kaiti SC", "STKaiti", "Songti SC", serif; font-size: 15px; }}
  .ask .a {{ font-size: 11px; color: #777; line-height: 1.6; }}
  .ask .a b {{ color: #b3423f; font-weight: 400; }}

  /* 默写用的空白横线 */
  .lines .ln {{ height: 9mm; border-bottom: 1px solid #999; }}
  .lines .ln:first-child {{ margin-top: 1mm; }}
  .answer {{ font-size: 11px; color: #999; margin-top: 1.5mm; }}
  .answer b {{ color: #b3423f; font-weight: 400; }}

  /* 错题格吃掉剩余高度（只印在题面版上），把空白变成能写字的地方 */
  .memo {{
    flex: 1 1 auto; min-height: 16mm; margin-top: 2mm;
    border: 1px dashed #C7D3E0; border-radius: 4px; padding: 3px 8px;
    font-size: 11px; color: #9aa8b6;
  }}

  /* 总评区钉在页底 */
  .total {{
    margin-top: auto; padding-top: 4mm; border-top: 1.5px dashed #bbb;
    display: flex; align-items: baseline; justify-content: space-between;
    font-size: 12px; color: #555;
  }}
  .total .big {{ font-size: 13px; color: #111; }}
  .total .big b {{ color: #42688F; font-size: 15px; }}
  .footer {{ margin-top: 2mm; text-align: right; color: #999; font-size: 10px; }}
</style>
</head>
<body>
{pages}
</body>
</html>
"""

PAGE_TEMPLATE = """<div class="page">
  <div class="header">
    <h1>{heading}{sub}</h1>
    <div class="info">{info}</div>
  </div>
{hint}
  <div class="blocks">
{blocks}
  </div>
{memo}
  <div class="total">
    <span class="big">过关 <span class="blank"></span> / <b>{count}</b> 项</span>
    <span>错的圈出来，明天再问一遍　　家长签字 <span class="blank"></span></span>
  </div>
  <div class="footer">{footer}</div>
</div>"""

BLOCK_TEMPLATE = """    <div class="block">
      <div class="bh">
        <span class="no">{no}</span>
        <h2>{name}{sub}</h2>
        <span class="meta">{meta}</span>
      </div>
{note}{body}
    </div>"""

DEFAULTS = {"title": "抽查单", "range": "", "hint": "", "minutes": "",
            "memo": "错在哪儿，记一笔——"}


def parse_spec(path: Path) -> tuple:
    """spec → (设置 dict, [题块 dict, ...])

    行格式：
      key: value                          设置行（只在第一个 [题块] 之前有效）
      [多音字] 只读不写 time=2 pass=错≤1   开一个题块
      note: 一句话说明                     块内说明（灰色小字）
      ask: 题面 | 参考答案                 整行问答，一行一题
      lines: 4                            留 4 条空白横线（默写用）
      answer: 参考答案                     配 lines 的答案，印在横线下面
      其余非空行                           词语网格项 `题面=答案`，用 , ， 、 分隔
    """
    conf = dict(DEFAULTS)
    blocks, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+?)\]\s*(.*)$", line)
        if m:                                # [多音字] 只读不写 time=2 pass=错≤1
            rest = m.group(2).strip()
            t = re.search(r"\btime\s*=\s*(\S+)", rest)
            time_ = ""
            if t:
                time_ = t.group(1)
                rest = (rest[:t.start()] + rest[t.end():]).strip()
            p = re.search(r"\bpass\s*=\s*(.+)$", rest)   # pass= 的值可以带空格，取到行尾
            pass_ = ""
            if p:
                pass_ = p.group(1).strip()
                rest = rest[:p.start()].strip()
            cur = {"name": m.group(1).strip(), "sub": rest, "time": time_,
                   "pass": pass_, "note": "", "answer": "",
                   "items": [], "asks": [], "lines": 0}
            blocks.append(cur)
            continue
        if cur is None:
            key, sep, val = line.partition(":")
            if sep:
                conf[key.strip()] = val.strip()
            continue
        key, sep, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if sep and key in ("note", "answer"):
            cur[key] = val
            continue
        if sep and key == "lines":
            if not val.isdigit():
                sys.exit(f"「{cur['name']}」的 lines: 要写数字，现在是 {val!r}")
            cur["lines"] = int(val)
            continue
        if sep and key == "ask":
            q, _, a = val.partition("|")
            cur["asks"].append((q.strip(), a.strip()))
            continue
        for part in re.split(r"[,，、]", line):          # 词语网格项，可跨行写
            part = part.strip()
            if not part:
                continue
            q, _, a = part.partition("=")
            cur["items"].append((q.strip(), a.strip()))
    if not blocks:
        sys.exit(f"{path} 里没有任何 [题块]")
    for b in blocks:
        if not (b["items"] or b["asks"] or b["lines"]):
            sys.exit(f"「{b['name']}」是空的：至少要有网格项、ask: 或 lines:")
    return conf, blocks


def build(spec_path: Path, pdf: bool = False, answers: bool = False) -> None:
    conf, blocks = parse_spec(spec_path)

    out_blocks, total = [], 0
    for i, b in enumerate(blocks, 1):
        body = []
        if b["items"]:
            cells = "\n".join(
                '          <div class="it"><span class="tick"></span>'
                f'<span class="q">{html.escape(q)}</span>'
                + (f'<span class="a">{html.escape(a)}</span>' if a and answers else "")
                + '<span class="dots"></span></div>'
                for q, a in b["items"])
            body.append(f'      <div class="items">\n{cells}\n      </div>')
            total += len(b["items"])
        for q, a in b["asks"]:
            body.append(
                '      <div class="ask"><span class="tick"></span><span class="body">'
                f'<span class="q">{html.escape(q)}</span>'
                + (f'<div class="a"><b>答：</b>{html.escape(a)}</div>' if a and answers else "")
                + "</span></div>")
            total += 1
        if b["lines"]:
            lns = "\n".join('        <div class="ln"></div>' for _ in range(b["lines"]))
            body.append(f'      <div class="lines">\n{lns}\n      </div>')
            total += 1
        if b["answer"] and answers:
            body.append(f'      <p class="answer"><b>答：</b>{html.escape(b["answer"])}</p>')

        meta = []
        if b["time"]:
            meta.append(f'<em>{html.escape(b["time"])} 分钟</em>')
        if b["pass"]:
            meta.append(f'<i>过关：{html.escape(b["pass"])}</i>')
        out_blocks.append(BLOCK_TEMPLATE.format(
            no=i, name=html.escape(b["name"]),
            sub=f'<small>　{html.escape(b["sub"])}</small>' if b["sub"] else "",
            meta="".join(meta),
            note=(f'      <p class="note">{html.escape(b["note"])}</p>\n'
                  if b["note"] else ""),
            body="\n".join(body)))

    info = ""
    if conf["minutes"]:
        info += f'<span>约 <b>{html.escape(conf["minutes"])}</b> 分钟</span>'
    if not answers:                       # 家长版不用填姓名日期
        info += ('<span>姓名 <span class="blank"></span></span>'
                 '<span>日期 <span class="blank"></span></span>')

    heading = conf["title"] + ("（家长版）" if answers else "")
    page = PAGE_TEMPLATE.format(
        heading=html.escape(heading),
        sub=f'<small>　{html.escape(conf["range"])}</small>' if conf["range"] else "",
        info=info,
        hint=(f'  <p class="hint">{html.escape(conf["hint"])}</p>\n'
              if conf["hint"] and answers else ""),   # 使用说明是给家长看的
        blocks="\n".join(out_blocks),
        memo=("" if answers or not conf["memo"]
              else f'  <div class="memo">{html.escape(conf["memo"])}</div>'),
        count=total,
        footer=f"共 {len(blocks)} 题块 / {total} 项")

    doc = TEMPLATE.format(title=html.escape(heading), pages=page)

    out_dir = Path("sheets")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f'{spec_path.stem}{"_answers" if answers else ""}.html'
    out.write_text(doc, encoding="utf-8")
    print(out)
    if pdf:
        pdf_path = out.with_suffix(".pdf")
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf_path}", f"file://{out.resolve()}"],
            check=True, capture_output=True)
        print(pdf_path)
    if not answers:                       # 家长版不进目录页
        write_index()


INDEX_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>抽查单 · 我的语文小屋</title>
<meta name="description" content="学完一个单元，家长照着单子问一遍，十分钟知道哪儿没记住。" />
<meta name="theme-color" content="#FBF6EB" />
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#9989;</text></svg>" />
<meta property="og:type" content="website" />
<meta property="og:title" content="抽查单 · 我的语文小屋" />
<meta property="og:description" content="学完一个单元，家长照着单子问一遍，十分钟知道哪儿没记住。" />
<style>
  :root{{
    --paper:#FBF6EB; --card:#FFFDF8; --ink:#4A3F36; --ink-soft:#9A8C7C;
    --line:rgba(120,104,84,.16); --grid:rgba(120,104,84,.05); --lan:#42688F;
    --font-display:"Kaiti SC","STKaiti","PingFang SC",serif;
    --font-cn:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
  }}
  *{{ box-sizing:border-box; }}
  html{{ -webkit-text-size-adjust:100%; }}
  body{{
    margin:0; font-family:var(--font-cn); color:var(--ink); line-height:1.7;
    min-height:100svh; background-color:var(--paper);
    background-image:
      radial-gradient(60% 50% at 88% -5%, rgba(66,104,143,.10), transparent 70%),
      linear-gradient(var(--grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--grid) 1px, transparent 1px);
    background-size:100% 100%,26px 26px,26px 26px;
    background-attachment:fixed,scroll,scroll;
  }}
  .wrap{{ width:100%; max-width:620px; margin:0 auto; padding:40px 20px 64px; }}
  .back{{ color:var(--ink-soft); text-decoration:none; font-size:.9rem; }}
  h1{{ font-family:var(--font-display); font-size:clamp(1.8rem,7vw,2.4rem);
      margin:12px 0 4px; line-height:1.25; }}
  .sub{{ color:var(--ink-soft); margin:0 0 30px; font-size:.92rem; }}
  ul{{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:12px; }}
  li{{
    display:flex; align-items:center; gap:14px; background:var(--card);
    border:2px solid var(--line); border-radius:18px; padding:16px 18px;
    box-shadow:0 3px 0 var(--line);
  }}
  li .d{{ flex:1 1 auto; min-width:0; }}
  li .d b{{ font-family:var(--font-display); font-size:1.15rem; color:var(--lan); }}
  li .d p{{ margin:0; font-size:.85rem; color:var(--ink-soft); }}
  li a{{
    flex:0 0 auto; text-decoration:none; color:var(--ink); font-size:.85rem;
    border:1.5px solid var(--line); border-radius:999px; padding:4px 12px; background:var(--paper);
  }}
  li a:active{{ transform:translateY(1px); }}
  .empty{{ color:var(--ink-soft); }}
  .foot{{ text-align:center; color:var(--ink-soft); font-size:.85rem; margin-top:36px; }}
</style>
</head>
<body>
  <main class="wrap">
    <a class="back" href="../">← 回小屋</a>
    <h1>抽查单</h1>
    <p class="sub">学完一个单元问一遍 · 点「打印单」直接开 PDF</p>
    <ul>
{rows}
    </ul>
    <p class="foot">共 {count} 份</p>
  </main>
</body>
</html>
"""

ROW_TEMPLATE = """      <li>
        <span class="d"><b>{label}</b><p>{note}</p></span>
        <a href="{pdf}">打印单</a>
      </li>"""


def write_index() -> None:
    """扫 sheets/ 生成 check/index.html（GitHub Pages 不会自动列目录）。
    按日期倒序，最新的在最上面；副标题取同名 spec 的 range: 和题块名。"""
    sheets = sorted((p for p in Path("sheets").glob("*.pdf")
                     if not p.stem.endswith("_answers")),
                    key=lambda p: p.stem, reverse=True)
    rows = []
    for p in sheets:
        m = re.match(r"^(\d{4})(\d{2})(\d{2})$", p.stem)
        label = f"{m.group(2).lstrip('0')} 月 {m.group(3).lstrip('0')} 日" if m else p.stem
        spec = Path("specs") / f"{p.stem}.txt"
        note = ""
        if spec.exists():
            text = spec.read_text(encoding="utf-8")
            rng = re.search(r"^range\s*:\s*(.+)$", text, re.MULTILINE)
            names = re.findall(r"^\[(.+?)\]", text, re.MULTILINE)
            note = " · ".join(filter(None, [rng.group(1).strip() if rng else "",
                                            " ".join(names)]))
        rows.append(ROW_TEMPLATE.format(label=html.escape(label),
                                        note=html.escape(note),
                                        pdf=f"./sheets/{p.name}"))
    if not rows:
        rows = ['      <li><span class="d empty">还没有抽查单</span></li>']
    Path("index.html").write_text(
        INDEX_TEMPLATE.format(rows="\n".join(rows), count=len(sheets)),
        encoding="utf-8")
    print("index.html")


def latest_spec() -> Path:
    specs = sorted(Path("specs").glob("*.txt"), key=lambda p: p.stat().st_mtime)
    if not specs:
        sys.exit("specs/ 下没有 spec 文件")
    return specs[-1]


if __name__ == "__main__":
    pdf = "--pdf" in sys.argv
    answers = "--answers" in sys.argv
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(Path(argv[0]) if argv else latest_spec(), pdf=pdf, answers=answers)
