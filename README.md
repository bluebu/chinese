# 我的语文小屋

小学生语文练习站。目前一个栏目：**今日练习**——把每天的生字、词语做成 A4「看拼音写汉字」打印单。

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

## 本地启动预览

```bash
make up            # 启动本地预览（默认端口 8000）
make up PORT=9000  # 指定端口
make open          # 用浏览器打开
make stop          # 停止预览
make help          # 查看全部命令
```

`make up` 会同时打印**电脑**和**手机 / iPad（同一 WiFi）**的访问地址；装了 `qrencode`
（`brew install qrencode`）还会显示手机扫码二维码。按 `Ctrl+C` 退出。

## 部署

全部相对路径，推到 GitHub 后在 **Settings → Pages** 选分支 `/ (root)` 即可；
要自定义域名就在根目录加 `CNAME`（参照 `../english`）。域名和远端目前都还没定。
