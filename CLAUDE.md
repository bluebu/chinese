# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 我的语文小屋 — 项目准则

面向小学生的语文练习站。姊妹项目 `../english`（英语小屋）——**结构、工程约定、发布流程一律照它来**，
遇到本文件没写到的问题，先看 `../english/CLAUDE.md` 怎么定的。

纯静态 HTML + Python 生成脚本，无构建步骤、无依赖安装（`pypinyin` 是可选增强，缺了也能跑）。

## 栏目隔离
- **每个栏目整体隔离在自己的目录**（今日练习 `practice/`）；根目录只放站点级文件
  （栏目导航页 `index.html`、`Makefile`、`.nojekyll`），栏目之间不互相引用。
- 栏目内部全部相对路径，无论部署在根域名还是 `/仓库名/` 子路径下都能打开。
- 新栏目另建独立目录，并在根 `index.html` 加一张卡片（未上线的标 `soon`）。

## practice/ — 今日练习单
「看拼音写汉字」A4 打印单：拼音在上，田字格在下。`specs/<YYYYMMDD>.txt` → `sheets/<YYYYMMDD>.html|.pdf`。
spec 完整语法见 `practice/README.md`；日常工作流见 `/practice` skill。

- **标拼音是这个栏目的核心职责，也是唯一容易出错的地方**。脚本只排版，不判断读音：
  多音字必须在 spec 里手写，按**课文语境**定音——`单=dān`（不是 shàn）、`悄悄=qiāo qiāo`（不是 qiǎo）。
  装了 `pypinyin` 的自动补全只对单音字可信，多音字一律手写覆盖。
- **音节数必须等于字数**（`麻雀=má què` → 2 格），不符时脚本报错并提示写法。
- 生字比词语更需要练手，惯例 `[生字] copies=3`、`[词语] copies=2`；
  `copies` / `cell` 是**排满一页 A4** 的两个旋钮，别让它溢出到第二页、也别空掉小半页。
- 答案版（`--answers`）格子里印楷体汉字，给家长批改用，**不进目录页**。
- 田字格用 CSS 画（实线外框 + 十字虚线），所以 `print-color-adjust: exact` 必须留着，
  否则打印时红线全没了；相邻格子靠负边距共享边线，别改成各画一圈边框（会叠成粗线）。

## 内容准则
- **不增不删**：用户给的字词一个不落、也不自己加练习项。字词的**课次分组照抄**，不重排合并。
- 每天的练习单是独立一份 spec；只是换个日期时 `cp specs/<旧>.txt specs/<新>.txt` 再改，别从头写。
- 用户给的内容有歧义（字词数量对不上、看不出是哪一课）先问，别猜。
- 排版细节：中文与数字/英文之间留空格（`16 课`）。

## 工程与发布
- 生成脚本**用相对路径，一律在自己的栏目目录下运行**（`cd practice && python3 generate_practice.py …`）。
- PDF 由无头 Chrome 导出。**改完排版一定 Read 生成的 PDF 自检**，别凭 HTML 源码想象效果。
- 本地预览 `make up`（会打印手机/iPad 同 WiFi 地址 + 二维码）；`make practice` 生成最新一份练习单。
- `practice/index.html` 由脚本自动生成（GitHub Pages 不列目录），**不要手改**——改模板改脚本里的 `INDEX_TEMPLATE`。
- 重大改动 / 体系取舍先和用户讨论；确认后 commit（用户要求才 push）。
- **域名和 GitHub 远端尚未确定**：还没有 `CNAME`，也没有 remote。定下来之前只在本地预览。
