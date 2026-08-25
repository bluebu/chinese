#!/usr/bin/env python3
"""从 specs/*.txt 生成 A4 朗读打卡单（课文大字排版 + 底部打卡圈）。

用法:
  python3 generate_recite.py specs/20260825.txt --pdf   # HTML + PDF
  python3 generate_recite.py specs/20260825.txt         # 只出 HTML（先在浏览器看排版）
  python3 generate_recite.py --pdf                      # 不给 spec 就用 specs/ 里最新改动的那份

输出: sheets/<spec 同名>.html，加 --pdf 时同时导出同名 .pdf。一篇课文一页。
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
    /* 打印时保留背景/边框颜色，否则打卡圈和译文底色全没了 */
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
  /* 一篇课文一页：撑满 A4，正文居中，打卡区钉底 */
  .page {{ display: flex; flex-direction: column; }}
  @media print {{ .page {{ height: 273mm; }} }}
  /* 正文块吃掉剩余高度，把空白都留到打卡区上方 */
  .main {{ flex: 1 1 auto; }}
  .page + .page {{ page-break-before: always; }}

  .header {{
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 2px solid #111; padding-bottom: 6px; margin-bottom: 6mm;
  }}
  .header h1 {{ font-size: 15px; padding-right: 10px; }}
  .header .info {{ font-size: 12px; white-space: nowrap; }}
  .header .info span {{ margin-left: 10px; }}
  .blank {{ display: inline-block; border-bottom: 1px solid #111; width: 44px; }}

  .lesson {{ text-align: center; margin-bottom: 5mm; }}
  .lesson h2 {{
    font-family: "Kaiti SC", "STKaiti", "Songti SC", serif;
    font-size: 26px; font-weight: 700; line-height: 1.3;
  }}
  .lesson h2 small {{ font-size: 15px; font-weight: 400; color: #555; }}
  .lesson .author {{ font-size: 12px; color: #777; margin-top: 2px; }}

  .task {{
    font-size: 12px; color: #b3423f; background: #FAE9E7;
    border-left: 3px solid #d94f4f; border-radius: 0 4px 4px 0;
    padding: 4px 9px; margin-bottom: 5mm;
  }}

  /* 正文：大字宽行距，给朗读用 */
  .text p {{
    font-family: "Kaiti SC", "STKaiti", "Songti SC", serif;
    font-size: var(--size, {size}px); line-height: 2.1; text-indent: 2em;
    text-align: justify; margin-bottom: 3mm;
  }}
  ruby rt {{
    font-family: "Times New Roman", "PingFang SC", serif;
    font-size: .5em; color: #b3423f; line-height: 1;
  }}

  .note {{
    font-size: 12px; line-height: 1.8; color: #444; background: #F5F2EA;
    border: 1px dashed #C9BCA6; border-radius: 5px; padding: 6px 10px; margin-top: 3mm;
  }}
  .note b {{ color: #7a6a52; font-weight: 700; }}

  /* 打卡区钉在页面底部，正文长短不一时位置也一致 */
  .check {{ margin-top: auto; padding-top: 5mm; border-top: 1.5px dashed #bbb; }}
  .check .cap {{ font-size: 12px; color: #666; margin-bottom: 3mm; }}
  .check .cap b {{ color: #d94f4f; font-size: 13px; }}
  .ticks {{ display: flex; flex-wrap: wrap; gap: 4mm; }}
  .tick {{
    width: 13mm; height: 13mm; border: 1pt solid #d94f4f; border-radius: 50%;
    display: grid; place-items: center; font-size: 11px; color: #e79a9a;
    font-style: normal; font-family: "Times New Roman", serif;
  }}

  .footer {{ margin-top: 3mm; text-align: right; color: #999; font-size: 10px; }}
</style>
</head>
<body>
{pages}
</body>
</html>
"""

PAGE_TEMPLATE = """<div class="page">
  <div class="header">
    <h1>{heading}</h1>
    <div class="info">{info}</div>
  </div>
  <div class="lesson">
    <h2>{name}{sub}</h2>
{author}
  </div>
{task}
  <div class="main"{style}>
    <div class="text">
{paras}
    </div>
{note}
  </div>
  <div class="check">
    <p class="cap">读一遍，涂一个圈 —— 一共读 <b>{times}</b> 遍</p>
    <div class="ticks">
{ticks}
    </div>
  </div>
  <div class="footer">{footer}</div>
</div>"""

INFO_HTML = ('姓名 <span class="blank"></span> 日期 <span class="blank"></span> '
             '家长签字 <span class="blank"></span>')

DEFAULTS = {"date": "", "title": "朗读打卡",
            "hint": "大声读一遍，涂一个圈。", "times": "10", "size": "17"}


def parse_spec(path: Path) -> tuple:
    """spec → (设置 dict, [篇目 dict, ...])

    行格式：
      key: value                              设置行（只在第一个 [篇目] 之前有效）
      [观潮] 第 3-4 自然段 author=… times=10   开一篇课文
      task: 今天读 10 遍                       本篇的任务小条
      note: 炎帝的小女儿……                     本篇的译文/注释框
      其余非空行                               正文，空行分段
    """
    conf = dict(DEFAULTS)
    lessons, cur = [], None
    blank = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            continue
        if not line:
            blank = True                         # 空行 = 正文分段
            continue
        m = re.match(r"^\[(.+?)\]\s*(.*)$", line)
        if m:                                    # [观潮] 第 3-4 自然段 author=… times=…
            rest = m.group(2).strip()
            attrs = {}
            for key in ("author", "times", "size"):
                a = re.search(rf"\b{key}\s*=\s*(\S+)", rest)
                if a:
                    attrs[key] = a.group(1)
                    rest = (rest[:a.start()] + rest[a.end():]).strip()
            cur = {"name": m.group(1).strip(), "sub": rest,
                   "author": attrs.get("author", ""),
                   "times": int(attrs.get("times", conf["times"])),
                   "size": attrs.get("size", conf["size"]),
                   "task": "", "note": "", "paras": []}
            lessons.append(cur)
            blank = False
            continue
        if cur is None:
            key, sep, val = line.partition(":")
            if sep:
                conf[key.strip()] = val.strip()
            continue
        key, sep, val = line.partition(":")
        if sep and key.strip() in ("task", "note"):
            cur[key.strip()] = val.strip()
            continue
        if blank or not cur["paras"]:            # 空行后另起一段
            cur["paras"].append(line)
        else:
            cur["paras"][-1] += line             # spec 里断行的同一段接回去
        blank = False
    if not lessons:
        sys.exit(f"{path} 里没有任何 [篇目]")
    for les in lessons:
        if not les["paras"]:
            sys.exit(f"「{les['name']}」没有正文")
    return conf, lessons


def ruby(text: str) -> str:
    """正文里的 字(拼音) → <ruby>字<rt>拼音</rt></ruby>；其余字符转义。

    拼音只跟在它前面那一个汉字上，所以「鼎(dǐng)沸(fèi)」要一个字一个字标。
    """
    out, pos = [], 0
    for m in re.finditer(r"([一-鿿])\(([^()]+)\)", text):
        out.append(html.escape(text[pos:m.start()]))
        out.append(f"<ruby>{html.escape(m.group(1))}"
                   f"<rt>{html.escape(m.group(2))}</rt></ruby>")
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def build(spec_path: Path, pdf: bool = False) -> None:
    conf, lessons = parse_spec(spec_path)

    heading = conf["title"] + (f'　{conf["date"]}' if conf["date"] else "")
    pages = []
    for i, les in enumerate(lessons, 1):
        paras = "\n".join(f"      <p>{ruby(p)}</p>" for p in les["paras"])
        ticks = "\n".join(f'      <i class="tick">{i}</i>'
                          for i in range(1, les["times"] + 1))
        pages.append(PAGE_TEMPLATE.format(
            heading=html.escape(heading), info=INFO_HTML,
            name=html.escape(les["name"]),
            sub=f'<small>（{html.escape(les["sub"])}）</small>' if les["sub"] else "",
            author=(f'    <p class="author">{html.escape(les["author"])}</p>'
                    if les["author"] else ""),
            task=(f'  <p class="task">{html.escape(les["task"])}</p>'
                  if les["task"] else ""),
            style=f' style="--size:{les["size"]}px"',
            paras=paras,
            note=(f'    <p class="note"><b>意思：</b>{html.escape(les["note"])}</p>'
                  if les["note"] else ""),
            ticks=ticks, times=les["times"],
            footer=f"第 {i} 篇 / 共 {len(lessons)} 篇"))

    doc = TEMPLATE.format(title=html.escape(heading), size=conf["size"],
                          pages="\n".join(pages))

    out_dir = Path("sheets")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{spec_path.stem}.html"
    out.write_text(doc, encoding="utf-8")
    print(out)
    if pdf:
        pdf_path = out.with_suffix(".pdf")
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf_path}", f"file://{out.resolve()}"],
            check=True, capture_output=True)
        print(pdf_path)
    write_index()


INDEX_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>朗读打卡 · 我的语文小屋</title>
<meta name="description" content="要背的课文，大字排版打印出来，读一遍涂一个圈。" />
<meta name="theme-color" content="#FBF6EB" />
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#128220;</text></svg>" />
<meta property="og:type" content="website" />
<meta property="og:title" content="朗读打卡 · 我的语文小屋" />
<meta property="og:description" content="要背的课文，大字排版打印出来，读一遍涂一个圈。" />
<style>
  :root{{
    --paper:#FBF6EB; --card:#FFFDF8; --ink:#4A3F36; --ink-soft:#9A8C7C;
    --line:rgba(120,104,84,.16); --grid:rgba(120,104,84,.05); --qing:#4E8E7C;
    --font-display:"Kaiti SC","STKaiti","PingFang SC",serif;
    --font-cn:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
  }}
  *{{ box-sizing:border-box; }}
  html{{ -webkit-text-size-adjust:100%; }}
  body{{
    margin:0; font-family:var(--font-cn); color:var(--ink); line-height:1.7;
    min-height:100svh; background-color:var(--paper);
    background-image:
      radial-gradient(60% 50% at 88% -5%, rgba(78,142,124,.10), transparent 70%),
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
  li .d b{{ font-family:var(--font-display); font-size:1.15rem; color:var(--qing); }}
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
    <h1>朗读打卡</h1>
    <p class="sub">要背的课文 · 点「打印单」直接开 PDF</p>
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
    """扫 sheets/ 生成 recite/index.html（GitHub Pages 不会自动列目录）。
    按日期倒序，最新的在最上面；副标题列出这份打卡单里的篇目（从同名 spec 读）。"""
    sheets = sorted(Path("sheets").glob("*.pdf"), key=lambda p: p.stem, reverse=True)
    rows = []
    for p in sheets:
        m = re.match(r"^(\d{4})(\d{2})(\d{2})$", p.stem)
        label = f"{m.group(2).lstrip('0')} 月 {m.group(3).lstrip('0')} 日" if m else p.stem
        spec = Path("specs") / f"{p.stem}.txt"
        names = re.findall(r"^\[(.+?)\]", spec.read_text(encoding="utf-8"),
                           re.MULTILINE) if spec.exists() else []
        note = " · ".join(names) if names else (f"{m.group(1)} 年" if m else "")
        rows.append(ROW_TEMPLATE.format(label=html.escape(label),
                                        note=html.escape(note),
                                        pdf=f"./sheets/{p.name}"))
    if not rows:
        rows = ['      <li><span class="d empty">还没有打卡单</span></li>']
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
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(Path(argv[0]) if argv else latest_spec(), pdf=pdf)
