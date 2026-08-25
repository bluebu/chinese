# 我的语文小屋

小学生语文练习站。两个栏目：

- **今日练习**——把每天的生字、词语做成 A4「看拼音写汉字」打印单。
- **朗读打卡**——把要背的课文做成 A4 大字打印单，读一遍涂一个圈。

姊妹项目：[english](../english)（英语小屋），结构和工程约定一致。

## 文件结构

```
index.html              站点入口：栏目导航
practice/               栏目一：今日练习（自包含，和其他栏目隔离）
  generate_practice.py  spec → A4 练习单（HTML + PDF）
  specs/<日期>.txt      练习内容，一天一份
  sheets/<日期>.html    生成的练习单（.pdf 同名；_answers 后缀是答案版）
  index.html            练习单目录页（脚本自动生成，别手改）
  README.md             spec 完整语法
recite/                 栏目二：朗读打卡（自包含，和其他栏目隔离）
  generate_recite.py    spec → A4 朗读打卡单（HTML + PDF），一篇课文一页
  specs/<日期>.txt      当天要读的篇目，一天一份
  sheets/<日期>.html    生成的打卡单（.pdf 同名）
  index.html            打卡单目录页（脚本自动生成，别手改）
  README.md             spec 完整语法
Makefile                本地预览 + 生成快捷命令
.nojekyll               让 GitHub Pages 原样服务静态文件
```

## 出一张练习单

```bash
cd practice
python3 generate_practice.py specs/20260821.txt --pdf            # HTML + PDF
python3 generate_practice.py specs/20260821.txt --answers --pdf  # 答案版（批改用）
```

或在根目录 `make practice`，用 `specs/` 里最新改动的那份 spec 生成。

spec 长这样（`汉字=拼音`，田字格数 = 字数，`copies` 是抄写遍数）：

```
date: 8月21日
copies: 2
cell: 15

[生字] 16 课 copies=3
陡=dǒu, 级=jí, 链=liàn, 攀=pān, 猴=hóu, 呵=hē

[词语] 15 课
麻雀=má què, 打猎=dǎ liè, 悄悄=qiāo qiāo
```

> **多音字必须手写拼音**，按课文语境定音（`单=dān` 不是 shàn，`悄悄=qiāo qiāo` 不是 qiǎo）。
> 装了 `pypinyin`（`pip3 install pypinyin`）可以省掉单音字的拼音，不装也能用。

PDF 由无头 Chrome 导出，A4 竖版，直接打印。

## 出一张朗读打卡单

```bash
cd recite
python3 generate_recite.py specs/20260825.txt --pdf
```

或在根目录 `make recite`。spec 长这样（一篇课文一页，`times` 是读几遍、`size` 是正文字号）：

```
date: 8月25日
times: 10

[观潮] 第 3-4 自然段 author=赵宗成、朱明元 size=17
task: 今天读 10 遍，以后要背诵。
午后一点左右，从远处传来隆隆的响声，好像闷雷滚动。顿时人声鼎(dǐng)沸(fèi)……
```

> 正文里 `字(拼音)` 排成小字注音，只标难字。正文短就把 `size` 调大，别让一页看着空。
> 完整语法见 [recite/README.md](recite/README.md)。

## 本地启动预览

```bash
make up            # 启动本地预览（默认端口 8001）
make up PORT=9000  # 指定端口
make open          # 用浏览器打开
make stop          # 停止预览
make help          # 查看全部命令
```

`make up` 会同时打印**电脑**和**手机 / iPad（同一 WiFi）**的访问地址；装了 `qrencode`
（`brew install qrencode`）还会显示手机扫码二维码。按 `Ctrl+C` 退出。

## 部署

远端 `git@github.com:bluebu/chinese.git`，分支 `master`。

全部相对路径，所以部署在根域名或 `/仓库名/` 子路径下都能打开。在 GitHub 仓库
**Settings → Pages → Build and deployment** 里 Source 选 `Deploy from a branch`、
Branch 选 `master` / `/ (root)`，保存后等一两分钟即可访问：

```
https://bluebu.github.io/chinese/
```

要自定义域名就在根目录加 `CNAME`（参照 `../english` 的 `english.hi-ruby.com`）。域名目前还没定。
