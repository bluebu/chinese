---
name: practice
description: 生字词 → A4「看拼音写汉字」练习单（practice/ 目录）。把用户贴出的今日练习内容（生字、词语，按课次分组）整理成 spec，标好拼音，生成田字格练习单（HTML + PDF）+ 答案版。当用户贴出生字/词语/今日练习、要求做练习单、默写单、抄写单、A4 PDF 时使用。
argument-hint: [日期，如 0821；不给就用今天]
---

# practice：生字词 → A4 看拼音写汉字练习单

用户把今日练习的生字和词语贴过来，产出一张 A4 练习单：每项拼音标在上面，下面空田字格。
**脚本用相对路径，一律在 `practice/` 目录下运行。**

- `specs/<YYYYMMDD>.txt` — 练习内容（本 skill 负责写）
- `sheets/<YYYYMMDD>.html` / `.pdf` — 练习单；`_answers` 后缀是答案版
- `generate_practice.py` — 生成脚本；spec 完整语法见 `practice/README.md`

先读根 `CLAUDE.md`（内容准则、排版旋钮、发布约定）。

## 流程

1. **整理内容 → spec**，写到 `specs/<YYYYMMDD>.txt`。区块按用户给的分类和课次拆：
   `[生字] 16 课 copies=3`、`[词语] 15 课`。**课次分组照抄，不重排合并。**
2. **逐字标拼音**（见下），写成 `汉字=拼音`。
3. 生成：`python3 generate_practice.py specs/<YYYYMMDD>.txt --pdf`
4. **自检**：Read 生成的 PDF 看排版（别凭 HTML 源码想象）。目标是**干净地放满一页**：
   底部空掉小半页就加大 `copies` 或 `cell`，快溢出到第二页就反过来调小。
5. 要批改就再出答案版：`python3 generate_practice.py specs/<YYYYMMDD>.txt --answers --pdf`
6. `open sheets/<YYYYMMDD>.pdf` 给用户看，确认后 commit（用户要求才 push）。

## 标拼音（这一步最容易错，也最要紧）

脚本只排版、不判断读音。装了 `pypinyin` 会自动补没写拼音的项，但**只对单音字可信**。

- **多音字一律手写，按课文语境定音**：`单=dān`（不是 shàn）、`悄悄=qiāo qiāo`（不是 qiǎo）、
  `呵=hē`、`仗=zhàng`。拿不准这个字在课文里读什么，问用户是哪一册哪一课，别猜。
- **轻声、儿化、变调**照教材注音写。
- **音节数必须等于字数**：`麻雀=má què` 两个音节两格；不符时脚本会报错并提示正确写法。
- 声调用带调字母（`ǎ ǚ`），不要写数字调号（`a3`）。

## 注意

- **不增不删**：用户给的字词一个不落、也不自己加练习项（不自己补组词、造句、笔顺）。
- 只是重复昨天的内容换个日期时，`cp specs/<旧>.txt specs/<新>.txt` 再改，别从头写。
- 用户给的内容有歧义（字数与词数对不上、生字里混进了词语）先问用户。
- `practice/index.html` 由脚本自动刷新，**不要手改**。
