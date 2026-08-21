# 今日练习（A4 打印）

「看拼音写汉字」练习单：拼音标在上面，下面田字格空着让孩子写。

```
practice/
  generate_practice.py      生成脚本
  specs/<日期>.txt          练习内容（手写，一天一份）
  sheets/<日期>.html|.pdf   生成的练习单（_answers 后缀是答案版）
```

## 生成

**脚本用相对路径，一律在 `practice/` 目录下运行。**

```bash
python3 generate_practice.py specs/20260821.txt --pdf              # HTML + PDF
python3 generate_practice.py specs/20260821.txt                    # 只出 HTML（先在浏览器看排版）
python3 generate_practice.py --pdf                                 # 不给 spec 就用 specs/ 里最新改动的那份
python3 generate_practice.py specs/20260821.txt --answers --pdf    # 答案版（格子里印楷体汉字，用来批改）
```

PDF 由无头 Chrome 导出，A4 竖版，直接打印。

## spec 写法

```
# 井号开头是注释
date: 8月21日                      # 页头日期，不写就不显示
title: 今日练习                    # 页头标题
hint: 看拼音，在田字格里写汉字。    # 标题下的一行提示，留空则不显示
copies: 2                          # 每项抄几遍（几组田字格），默认 1
cell: 15                           # 田字格边长（mm），默认 13
gap: 4                             # 项与项的横向间距（mm），默认 5
py: 11                             # 拼音字号（px），默认 11

[生字] 16 课 copies=3               # 区块标题；copies=N 覆盖本区块的抄写遍数
陡=dǒu, 级=jí, 链=liàn

[词语] 15 课
麻雀=má què, 打猎=dǎ liè, 悄悄=qiāo qiāo
```

- 一项写成 `汉字=拼音`，多个音节用空格分开（`麻雀=má què`），项与项用 `,`／`，`／`、` 分隔，可跨行写。
- 田字格数量 = 汉字字数，所以 `麻雀=má què` 自动出 2 格。**音节数必须等于字数**，不符时脚本会报错并提示怎么写。
- 拼音可以省略（`陡, 级`）：装了 `pypinyin` 就自动补，没装则报错。
  **多音字一律手写**——脚本不知道课文语境（`单=dān` 不是 `shàn`、`悄悄=qiāo qiāo` 不是 `qiǎo`）。

## 排版调整

一页装不满就加大 `copies` 或 `cell`；快溢出到第二页就反过来调小。生字比词语更需要练手，
惯例是生字 `copies=3`、词语 `copies=2`。改完重新生成，**Read 生成的 PDF 看排版**，别凭 HTML 源码想象。
