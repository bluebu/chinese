#!/usr/bin/env python3
"""从 specs/*.txt 生成 A4「看拼音写汉字」练习单（拼音在上，田字格在下）。

用法:
  python3 generate_practice.py specs/20260821.txt --pdf   # HTML + PDF
  python3 generate_practice.py specs/20260821.txt         # 只出 HTML（先在浏览器看排版）
  python3 generate_practice.py --pdf                      # 不给 spec 就用 specs/ 里最新改动的那份
  python3 generate_practice.py specs/20260821.txt --answers --pdf   # 答案版（格子里印汉字）

输出: sheets/<spec 同名>.html，加 --pdf 时同时导出同名 .pdf
"""
import html
import re
import subprocess
import sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 可选依赖：装了就能自动补 spec 里没手写拼音的字（多音字仍应在 spec 里手写覆盖）
try:
    from pypinyin import pinyin, Style
except ImportError:
    pinyin = None

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 11mm 12mm; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: "PingFang SC", "Hiragino Sans GB", "Songti SC", sans-serif;
    color: #111; font-size: 13px;
    /* 打印时保留背景/边框颜色，否则田字格的红线打不出来 */
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  /* 屏幕预览时模拟 A4 纸张 */
  @media screen {{
    body {{ background: #888; padding: 20px 0; }}
    .page {{
      width: 210mm; min-height: 297mm; margin: 0 auto 20px;
      background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.4);
      padding: 11mm 12mm;
    }}
  }}
  .header {{
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 2px solid #111; padding-bottom: 6px; margin-bottom: 5mm;
  }}
  .header h1 {{ font-size: 15px; padding-right: 10px; }}
  .header .info {{ font-size: 12px; white-space: nowrap; }}
  .header .info span {{ margin-left: 10px; }}
  .blank {{ display: inline-block; border-bottom: 1px solid #111; width: 44px; }}
  .hint {{ font-size: 11px; color: #777; margin-bottom: 4mm; }}

  .block {{ margin-bottom: 4mm; }}
  .block h2 {{
    font-size: 13px; font-weight: 700; margin-bottom: 2.5mm;
    border-left: 3px solid #d94f4f; padding-left: 5px; line-height: 1.2;
  }}
  .items {{ display: flex; flex-wrap: wrap; gap: 4mm {gap}mm; }}

  /* 一个字/词 = 拼音行 + 田字格行，两行按格宽对齐成同样的列 */
  .item {{ display: inline-grid; grid-template-rows: auto auto; break-inside: avoid; }}
  .py {{ display: grid; grid-auto-flow: column; grid-auto-columns: {cell}mm; }}
  .py span {{
    text-align: center; font-size: {py}px; line-height: 1.5; color: #333;
    font-family: "Times New Roman", "PingFang SC", serif;
    letter-spacing: -.2px;
  }}
  .cells {{ display: grid; grid-auto-flow: column; grid-auto-columns: {cell}mm; }}

  /* 田字格：实线外框 + 十字虚线；相邻格子负边距共享竖边 */
  .tian {{
    width: {cell}mm; height: {cell}mm; position: relative;
    border: .75pt solid #d94f4f;
  }}
  .tian + .tian {{ margin-left: -.75pt; }}
  .cells + .cells {{ margin-top: -.75pt; }}
  .tian::before, .tian::after {{ content: ""; position: absolute; }}
  .tian::before {{ left: 0; right: 0; top: 50%; border-top: .5pt dashed #e79a9a; }}
  .tian::after {{ top: 0; bottom: 0; left: 50%; border-left: .5pt dashed #e79a9a; }}
  /* 答案版：格子里印出汉字 */
  .tian b {{
    position: absolute; inset: 0; display: grid; place-items: center;
    font-size: {ans}mm; font-weight: 400; color: #444;
    font-family: "Kaiti SC", "STKaiti", "Songti SC", serif;
  }}

  .footer {{ margin-top: 4mm; text-align: right; color: #999; font-size: 10px; }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>{heading}</h1>
    <div class="info">{info}</div>
  </div>
{hint}
{blocks}
  <div class="footer">{footer}</div>
</div>
</body>
</html>
"""

INFO_HTML = ('姓名 <span class="blank"></span> 日期 <span class="blank"></span> '
             '得分 <span class="blank"></span>')

DEFAULTS = {
    "date": "", "title": "今日练习", "hint": "看拼音，在田字格里写汉字。",
    "copies": "1", "cell": "13", "gap": "5", "py": "11",
}


def parse_spec(path: Path) -> tuple:
    """spec → (设置 dict, [(区块标题, [(汉字, [拼音音节]), ...]), ...])

    行格式：
      key: value            设置行（只在第一个 [区块] 之前有效）
      [区块标题]            开一个新区块
      陡=dǒu, 级=jí         区块内的项，逗号/顿号分隔；= 后是拼音，音节用空格分开
    """
    conf = dict(DEFAULTS)
    blocks, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+?)\]\s*(.*)$", line)
        if m:                                    # [生字] 16课 copies=3
            rest = m.group(2).strip()
            n = re.search(r"\bcopies\s*=\s*(\d+)", rest)
            if n:
                rest = (rest[:n.start()] + rest[n.end():]).strip()
            title = " ".join(p for p in (m.group(1).strip(), rest) if p)
            cur = (title, [], int(n.group(1)) if n else None)
            blocks.append(cur)
            continue
        if cur is None:
            key, sep, val = line.partition(":")
            if sep:
                conf[key.strip()] = val.strip()
            continue
        for part in re.split(r"[,，、]", line):
            part = part.strip()
            if not part:
                continue
            word, _, py = part.partition("=")
            word = word.strip()
            syllables = py.split()
            if not syllables:
                syllables = auto_pinyin(word)
            if len(syllables) != len(word):
                sys.exit(f"「{part}」拼音音节数({len(syllables)})与字数({len(word)})不符，"
                         f"请在 spec 里写成 {word}=" + " ".join(["?"] * len(word)))
            cur[1].append((word, syllables))
    if not blocks:
        sys.exit(f"{path} 里没有任何 [区块]")
    return conf, blocks


def auto_pinyin(word: str) -> list:
    if pinyin is None:
        sys.exit(f"「{word}」没写拼音，且没装 pypinyin。"
                 f"请在 spec 里写 {word}=… ，或 pip3 install pypinyin")
    return [s[0] for s in pinyin(word, style=Style.TONE)]


def item_html(word: str, syllables: list, copies: int, answers: bool) -> str:
    py = "".join(f"<span>{html.escape(s)}</span>" for s in syllables)
    cell = lambda ch: f'<i class="tian">{f"<b>{html.escape(ch)}</b>" if answers else ""}</i>'
    groups = []
    for _ in range(copies):
        groups.append('<div class="cells">' + "".join(cell(c) for c in word) + "</div>")
    # 抄写多遍时，拼音只标在第一组上面
    return ('<div class="item">'
            f'<div class="py">{py}</div>' + groups[0] +
            "".join(groups[1:]) + "</div>")


def build(spec_path: Path, pdf: bool = False, answers: bool = False) -> None:
    conf, blocks = parse_spec(spec_path)
    copies = int(conf["copies"])

    parts = []
    for title, items, block_copies in blocks:
        n = block_copies or copies
        rows = "\n".join("      " + item_html(w, s, n, answers) for w, s in items)
        parts.append(f'  <div class="block">\n    <h2>{html.escape(title)}</h2>\n'
                     f'    <div class="items">\n{rows}\n    </div>\n  </div>')

    total = sum(len(items) for _, items, _ in blocks)
    heading = conf["title"] + ("（答案）" if answers else "")
    if conf["date"]:
        heading += f'　{conf["date"]}'
    hint = f'  <p class="hint">{html.escape(conf["hint"])}</p>' if conf["hint"] and not answers else ""

    doc = TEMPLATE.format(
        title=html.escape(heading), heading=html.escape(heading),
        info="" if answers else INFO_HTML, hint=hint, blocks="\n".join(parts),
        footer=f"共 {total} 项", cell=conf["cell"], gap=conf["gap"],
        py=conf["py"], ans=str(round(float(conf["cell"]) * 0.62, 1)))

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
    if not answers:
        write_index()


INDEX_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>今日练习 · 我的语文小屋</title>
<meta name="description" content="每天的生字词练习单，看拼音写汉字，点开就能打印。" />
<meta name="theme-color" content="#FBF6EB" />
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#9999;&#65039;</text></svg>" />
<meta property="og:type" content="website" />
<meta property="og:title" content="今日练习 · 我的语文小屋" />
<meta property="og:description" content="每天的生字词练习单，看拼音写汉字，点开就能打印。" />
<style>
  :root{{
    --paper:#FBF6EB; --card:#FFFDF8; --ink:#4A3F36; --ink-soft:#9A8C7C;
    --line:rgba(120,104,84,.16); --grid:rgba(120,104,84,.05); --zhu:#D94F4F;
    --font-display:"Kaiti SC","STKaiti","PingFang SC",serif;
    --font-cn:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
  }}
  *{{ box-sizing:border-box; }}
  html{{ -webkit-text-size-adjust:100%; }}
  body{{
    margin:0; font-family:var(--font-cn); color:var(--ink); line-height:1.7;
    min-height:100svh; background-color:var(--paper);
    background-image:
      radial-gradient(60% 50% at 88% -5%, rgba(217,79,79,.10), transparent 70%),
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
  li .d b{{ font-family:var(--font-display); font-size:1.15rem; color:var(--zhu); }}
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
    <h1>今日练习</h1>
    <p class="sub">看拼音写汉字 · 点「打印单」直接开 PDF</p>
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
    """扫 sheets/ 生成 practice/index.html（GitHub Pages 不会自动列目录）。
    按日期倒序，最新的在最上面；答案版不列（那是给家长批改用的）。"""
    sheets = sorted((p for p in Path("sheets").glob("*.pdf")
                     if not p.stem.endswith("_answers")),
                    key=lambda p: p.stem, reverse=True)
    rows = []
    for p in sheets:
        m = re.match(r"^(\d{4})(\d{2})(\d{2})$", p.stem)
        label = f"{m.group(2).lstrip('0')} 月 {m.group(3).lstrip('0')} 日" if m else p.stem
        note = f"{m.group(1)} 年" if m else ""
        rows.append(ROW_TEMPLATE.format(label=html.escape(label),
                                        note=html.escape(note),
                                        pdf=f"./sheets/{p.name}"))
    if not rows:
        rows = ['      <li><span class="d empty">还没有练习单</span></li>']
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
