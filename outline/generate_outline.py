#!/usr/bin/env python3
"""从 specs/*.txt 生成「课文要求总表」：A4 打印单 + 网页速查页。

用法:
  python3 generate_outline.py specs/g4a.txt --pdf   # 打印单 HTML + PDF，同时刷新网页速查页
  python3 generate_outline.py specs/g4a.txt         # 只出 HTML（先在浏览器看排版）
  python3 generate_outline.py --pdf                 # 不给 spec 就用 specs/ 里最新改动的那份

输出:
  sheets/<spec 同名>.html|.pdf   A4 打印单，一页装完，夹在语文书里
  index.html                     网页速查页（手机上翻），内容和打印单一样，别手改

一册一份，所以 spec 按册命名（g4a = 四年级上册），不按日期。
"""
import html
import re
import subprocess
import sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 属性值可以带空格（recite=第 3~4 自然段），所以按下一个 key= 的位置切
ATTR_RE = re.compile(r"\b(read|recite|copy|write)\s*=\s*")
DEFAULTS = {"title": "课文要求总表", "range": "", "note": ""}

# ---------------------------------------------------------------- A4 打印单

CSS_SHEET = """
  @page { size: A4; margin: 12mm 14mm; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Songti SC", sans-serif;
    color: #111; font-size: 11px;
    /* 打印时保留背景色，否则"要背/要默写"那两列的底色全没了，表就白扫一遍 */
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  /* 屏幕预览时模拟 A4 纸张 */
  @media screen {
    body { background: #888; padding: 20px 0; }
    .page {
      width: 210mm; height: 297mm; margin: 0 auto 20px;
      background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.4);
      padding: 12mm 14mm;
    }
  }
  /* 一页装完：小结钉在页底 */
  .page { display: flex; flex-direction: column; }
  @media print { .page { height: 273mm; } }

  .header {
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 2px solid #111; padding-bottom: 5px; margin-bottom: 3mm;
  }
  .header h1 { font-size: 17px; padding-right: 10px; }
  .header h1 small { font-size: 11px; font-weight: 400; color: #666; }
  .header .info { font-size: 10px; color: #666; white-space: nowrap; }
  .header .info b { color: #b3423f; }

  .sum {
    border: 1.2px solid #42688F; border-radius: 5px; background: #F2F6FA;
    padding: 4px 9px; margin-bottom: 2mm;
  }
  .sum ul { list-style: none; }
  .sum li { display: flex; gap: 7px; font-size: 10.5px; line-height: 1.62; }
  .sum li b { flex: 0 0 auto; color: #42688F; white-space: nowrap; }
  .sum li span { color: #444; }
  .note { font-size: 9.5px; color: #999; margin-bottom: 2mm; }

  table { width: 100%; border-collapse: collapse; }
  th, td { border: .6pt solid #C7D3E0; padding: 2px 4px; vertical-align: middle; }
  thead th { background: #E7EEF6; color: #2F4D6B; font-size: 10px; white-space: nowrap; }
  td.no {
    width: 10mm; text-align: center; color: #42688F; font-weight: 700;
    font-size: 9.5px; font-family: "Times New Roman", serif;
  }
  td.name {
    width: 25mm; font-family: "Kaiti SC", "STKaiti", "Songti SC", serif; font-size: 12.5px;
  }
  td.read { width: 22mm; }
  td.recite { width: 25mm; }
  td.copy { width: 20mm; font-size: 10px; }
  td.other { font-size: 9.5px; color: #444; line-height: 1.45; }
  td.write { width: 12mm; text-align: center; font-size: 9.5px; color: #666; }
  /* 要背 / 要默写：底色 + 圆点，一眼扫得出哪几行有 */
  .on { background: #FAE9E7; color: #b3423f; font-weight: 700; }
  .on i { font-style: normal; margin-right: 2px; }
  .off { color: #C4C4C4; }
  .todo { color: #999; }
  tr.yuan td.no, tr.yuan td.name { color: #4E8E7C; }
  tr.yuan { background: #FBFCFB; }

  .tail { margin-top: auto; padding-top: 3mm; border-top: 1.5px dashed #bbb; }
  .tail ul { list-style: none; }
  .tail li { font-size: 9.5px; color: #555; line-height: 1.7; }
  .tail li::before { content: "· "; color: #42688F; font-weight: 700; }
  .footer { margin-top: 2mm; text-align: right; color: #999; font-size: 9px; }
"""

TEMPLATE_SHEET = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>{title}{range}</h1>
    <div class="info">{stat}</div>
  </div>
  <div class="sum">
    <ul>
{summaries}
    </ul>
  </div>
{note}  <table>
    <thead>
      <tr>
        <th>课</th><th>课文</th><th>背诵</th><th>默写</th><th>朗读</th>
        <th>其他要求（书上原话）</th><th>写字</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
  <div class="tail">
    <ul>
{tails}
    </ul>
  </div>
  <div class="footer">{footer}</div>
</div>
</body>
</html>
"""

ROW_SHEET = """      <tr{cls}>
        <td class="no">{no}</td>
        <td class="name">{name}</td>
        <td class="recite">{recite}</td>
        <td class="copy">{copy}</td>
        <td class="read">{read}</td>
        <td class="other">{other}</td>
        <td class="write">{write}</td>
      </tr>"""

# ---------------------------------------------------------------- 网页速查页

CSS_WEB = """
  :root{
    --paper:#FBF6EB; --card:#FFFDF8; --ink:#4A3F36; --ink-soft:#9A8C7C;
    --line:rgba(120,104,84,.16); --grid:rgba(120,104,84,.05);
    --lan:#42688F; --lan-bg:#E7EEF6; --zhu:#b3423f; --zhu-bg:#FAE9E7; --qing:#4E8E7C;
    --font-display:"Kaiti SC","STKaiti","PingFang SC",serif;
    --font-cn:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
  }
  *{ box-sizing:border-box; }
  html{ -webkit-text-size-adjust:100%; }
  body{
    margin:0; font-family:var(--font-cn); color:var(--ink); line-height:1.7;
    min-height:100svh; background-color:var(--paper);
    background-image:
      radial-gradient(60% 50% at 88% -5%, rgba(66,104,143,.10), transparent 70%),
      linear-gradient(var(--grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--grid) 1px, transparent 1px);
    background-size:100% 100%,26px 26px,26px 26px;
    background-attachment:fixed,scroll,scroll;
  }
  .wrap{ width:100%; max-width:900px; margin:0 auto; padding:40px 20px 64px; }
  .back{ color:var(--ink-soft); text-decoration:none; font-size:.9rem; }
  h1{ font-family:var(--font-display); font-size:clamp(1.8rem,7vw,2.4rem);
      margin:12px 0 4px; line-height:1.25; }
  .sub{ color:var(--ink-soft); margin:0 0 24px; font-size:.92rem; }

  /* 摘要卡片：手机上第一屏就看到"要背的只有 3 处" */
  .sum{ display:flex; flex-direction:column; gap:10px; margin-bottom:20px; }
  .sum .c{
    background:var(--card); border:2px solid var(--line); border-radius:16px;
    padding:12px 16px; box-shadow:0 3px 0 var(--line);
  }
  .sum .c b{ display:block; font-family:var(--font-display); font-size:1.1rem; color:var(--lan); }
  .sum .c span{ font-size:.88rem; color:var(--ink-soft); }
  .note{
    font-size:.82rem; color:var(--ink-soft); background:var(--card);
    border:1px dashed var(--line); border-radius:10px; padding:8px 12px; margin-bottom:22px;
  }

  /* 宽表格自己横向滚动，别让整页横滚 */
  .scroll{ overflow-x:auto; -webkit-overflow-scrolling:touch;
           border:2px solid var(--line); border-radius:16px; background:var(--card); }
  table{ border-collapse:collapse; min-width:820px; width:100%; font-size:.84rem; }
  th,td{ border-bottom:1px solid var(--line); padding:9px 11px; text-align:left;
         vertical-align:middle; }
  thead th{ background:var(--lan-bg); color:#2F4D6B; font-weight:700; white-space:nowrap;
            position:sticky; top:0; }
  tbody tr:last-child td{ border-bottom:none; }
  td.no{ color:var(--lan); font-weight:800; text-align:center; white-space:nowrap; }
  td.name{ font-family:var(--font-display); font-size:1rem; white-space:nowrap; }
  td.other{ font-size:.8rem; color:var(--ink-soft); line-height:1.6; min-width:230px; }
  td.write{ text-align:center; font-size:.78rem; color:var(--ink-soft); white-space:nowrap; }
  td.read,td.recite,td.copy{ white-space:nowrap; }
  .on{ background:var(--zhu-bg); color:var(--zhu); font-weight:700; }
  .on i{ font-style:normal; margin-right:3px; }
  .off{ color:#CFC7BC; }
  .todo{ color:var(--ink-soft); }
  tr.yuan td.no, tr.yuan td.name{ color:var(--qing); }

  .tail{ margin:22px 0 0; padding:0; list-style:none; }
  .tail li{ font-size:.86rem; color:var(--ink-soft); line-height:1.9; }
  .tail li::before{ content:"· "; color:var(--lan); font-weight:800; }
  .dl{ margin-top:26px; text-align:center; }
  .dl a{
    display:inline-block; text-decoration:none; color:var(--ink); font-size:.9rem;
    border:2px solid var(--line); border-radius:999px; padding:8px 20px;
    background:var(--card); box-shadow:0 3px 0 var(--line);
  }
  .dl a:active{ transform:translateY(1px); box-shadow:0 1px 0 var(--line); }
  .foot{ text-align:center; color:var(--ink-soft); font-size:.85rem; margin-top:30px; }
"""

TEMPLATE_WEB = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>{title} · 我的语文小屋</title>
<meta name="description" content="{desc}" />
<meta name="theme-color" content="#FBF6EB" />
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#128451;</text></svg>" />
<meta property="og:type" content="website" />
<meta property="og:title" content="{title} · 我的语文小屋" />
<meta property="og:description" content="{desc}" />
<style>{css}</style>
</head>
<body>
  <main class="wrap">
    <a class="back" href="../">← 回小屋</a>
    <h1>{title}</h1>
    <p class="sub">{range}</p>

    <div class="sum">
{summaries}
    </div>
{note}
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th>课</th><th>课文</th><th>背诵</th><th>默写</th><th>朗读</th>
            <th>其他要求（书上原话）</th><th>写字</th>
          </tr>
        </thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </div>

    <ul class="tail">
{tails}
    </ul>

    <p class="dl"><a href="{pdf}">下载 A4 打印单（PDF）</a></p>
    <p class="foot">{footer}</p>
  </main>
</body>
</html>
"""


def parse_spec(path: Path) -> tuple:
    """spec → (设置 dict, [摘要 (标题, 详情)], [行 dict], [小结句])

    行格式：
      key: value                       设置行：title / range / note
      summary: 标题 | 详情              顶部摘要，可重复
      tail: 一句话                      底部小结，可重复
      [1] 观潮 read=… recite=… write=…  开一行（课号带 * 是略读课文）
      other: 其他要求                    上一行的"其他要求"列
    """
    conf = dict(DEFAULTS)
    summaries, rows, tails = [], [], []
    cur = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+?)\]\s*(.*)$", line)
        if m:
            no, rest = m.group(1).strip(), m.group(2).strip()
            marks = list(ATTR_RE.finditer(rest))
            name = (rest[:marks[0].start()] if marks else rest).strip()
            attrs = {}
            for i, mk in enumerate(marks):
                end = marks[i + 1].start() if i + 1 < len(marks) else len(rest)
                attrs[mk.group(1)] = rest[mk.end():end].strip()
            cur = {"no": no, "name": name, "other": "",
                   "read": attrs.get("read", ""), "recite": attrs.get("recite", ""),
                   "copy": attrs.get("copy", ""), "write": attrs.get("write", ""),
                   "lue": no.endswith("*"),          # 略读课文
                   "yuan": no.startswith("园地")}
            rows.append(cur)
            continue
        key, sep, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if not sep:
            continue
        if key == "summary":
            head, _, detail = val.partition("|")
            summaries.append((head.strip(), detail.strip()))
            continue
        if key == "tail":
            tails.append(val)
            continue
        if cur is not None and key == "other":
            cur["other"] = val
            continue
        if cur is None:
            conf[key] = val
    if not rows:
        sys.exit(f"{path} 里没有任何 [课] 行")
    return conf, summaries, rows, tails


def cells(r: dict) -> dict:
    """一行的五个"要求"格子：有要求就上底色加圆点，没要求就淡灰一杠。"""
    def mark(val: str) -> str:
        if not val:
            return '<span class="off">—</span>'
        if val == "待补":
            return '<span class="todo">待补</span>'
        return f'<i>●</i>{html.escape(val)}'

    if r["write"] in ("-", "—"):
        write = '<span class="off">—</span>'
    elif r["lue"] or r["write"] == "0":
        write = '<span class="todo">只认字</span>'
    elif r["write"]:
        write = f'{html.escape(r["write"])} 字'
    else:
        write = '<span class="off">—</span>'

    on = ' class="{} on"'
    off = ' class="{}"'
    return {
        "read": (html.escape(r["read"]) if r["read"] else '<span class="off">—</span>'),
        "recite": mark(r["recite"]),
        "copy": mark(r["copy"]),
        "write": write,
        "recite_cls": (on if r["recite"] and r["recite"] != "待补" else off).format("recite"),
        "copy_cls": (on if r["copy"] else off).format("copy"),
    }


def build(spec_path: Path, pdf: bool = False) -> None:
    conf, summaries, rows, tails = parse_spec(spec_path)

    def n(pred) -> int:
        return sum(1 for r in rows if pred(r))

    backed = lambda r: bool(r["recite"]) and r["recite"] != "待补"
    stat = (f'共 {n(lambda r: not r["yuan"])} 课　'
            f'课文要背 <b>{n(lambda r: backed(r) and not r["yuan"])}</b> 处　'
            f'日积月累 <b>{n(lambda r: backed(r) and r["yuan"])}</b> 处　'
            f'默写 <b>{n(lambda r: bool(r["copy"]))}</b> 首')

    sheet_rows, web_rows = [], []
    for r in rows:
        c = cells(r)
        cls = ' class="yuan"' if r["yuan"] else ""
        row = ROW_SHEET.format(
            cls=cls, no=html.escape(r["no"]), name=html.escape(r["name"]),
            read=c["read"], recite=c["recite"], copy=c["copy"],
            other=html.escape(r["other"]), write=c["write"])
        # 两版共用一份行 HTML，只是把 class="recite"/"copy" 换成带底色的那份
        row = (row.replace('<td class="recite">', f'<td{c["recite_cls"]}>')
                  .replace('<td class="copy">', f'<td{c["copy_cls"]}>'))
        sheet_rows.append(row)
        web_rows.append("    " + row.replace("\n      ", "\n          "))

    sheet_sum = "\n".join(
        f'      <li><b>{html.escape(h)}</b><span>{html.escape(d)}</span></li>'
        for h, d in summaries)
    web_sum = "\n".join(
        f'      <div class="c"><b>{html.escape(h)}</b><span>{html.escape(d)}</span></div>'
        for h, d in summaries)
    sheet_tail = "\n".join(f'      <li>{html.escape(t)}</li>' for t in tails)
    web_tail = "\n".join(f'      <li>{html.escape(t)}</li>' for t in tails)

    footer = f"{conf['range']}　共 {len(rows)} 行"

    out_dir = Path("sheets")
    out_dir.mkdir(exist_ok=True)
    sheet = out_dir / f"{spec_path.stem}.html"
    sheet.write_text(TEMPLATE_SHEET.format(
        css=CSS_SHEET, title=html.escape(conf["title"]),
        range=(f'<small>　{html.escape(conf["range"])}</small>' if conf["range"] else ""),
        stat=stat, summaries=sheet_sum,
        note=(f'  <p class="note">{html.escape(conf["note"])}</p>\n'
              if conf["note"] else ""),
        rows="\n".join(sheet_rows), tails=sheet_tail,
        footer=html.escape(footer)), encoding="utf-8")
    print(sheet)

    pdf_path = sheet.with_suffix(".pdf")
    if pdf:
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf_path}", f"file://{sheet.resolve()}"],
            check=True, capture_output=True)
        print(pdf_path)

    desc = "；".join(f"{h}：{d}" for h, d in summaries[:2]) or conf["title"]
    Path("index.html").write_text(TEMPLATE_WEB.format(
        css=CSS_WEB, title=html.escape(conf["title"]),
        desc=html.escape(desc), range=html.escape(conf["range"]),
        summaries=web_sum,
        note=(f'    <p class="note">{html.escape(conf["note"])}</p>\n'
              if conf["note"] else ""),
        rows="\n".join(web_rows), tails=web_tail,
        pdf=f"./sheets/{pdf_path.name}", footer=html.escape(footer)),
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
