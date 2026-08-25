# 我的语文小屋 · 本地预览
#
#   make up      启动本地预览（电脑 + 同一 WiFi 下的手机/iPad 都能访问）
#   make open    用默认浏览器打开
#   make stop    停止占用端口的预览进程
#   make help    查看全部命令

PORT ?= 8001
HOST ?= 0.0.0.0

.PHONY: up open stop practice recite check outline help
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "  语文小屋 · 本地预览"
	@echo "  ─────────────────────────────"
	@echo "  make up        启动本地预览服务（默认端口 $(PORT)）"
	@echo "  make open      用浏览器打开预览页"
	@echo "  make stop      停止预览服务"
	@echo "  make practice  用 specs/ 里最新的 spec 生成今日练习单（HTML + PDF）"
	@echo "  make recite    用 specs/ 里最新的 spec 生成朗读打卡单（HTML + PDF）"
	@echo "  make check     生成每一课的抽查单（题面版 + 家长版）"
	@echo "  make outline   生成课文要求总表（A4 打印单 + 网页速查页）"
	@echo "  make up PORT=9000   指定端口启动"
	@echo ""

up:
	@ip=$$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null); \
	echo ""; \
	echo "  📖 语文小屋预览已启动（Ctrl+C 退出）"; \
	echo "  ─────────────────────────────────────────"; \
	echo "  电脑：              http://localhost:$(PORT)/"; \
	if [ -n "$$ip" ]; then \
	  echo "  手机/iPad（同 WiFi）：http://$$ip:$(PORT)/"; \
	  if command -v qrencode >/dev/null 2>&1; then \
	    echo ""; echo "  手机扫码直达 👇"; echo ""; \
	    qrencode -t ANSIUTF8 "http://$$ip:$(PORT)/"; \
	  else \
	    echo "  （想要扫码二维码可先安装：brew install qrencode）"; \
	  fi; \
	fi; \
	echo ""; \
	python3 -m http.server $(PORT) --bind $(HOST)

open:
	@open "http://localhost:$(PORT)/"

stop:
	@pids=$$(lsof -ti tcp:$(PORT) 2>/dev/null); \
	if [ -n "$$pids" ]; then \
	  echo "$$pids" | xargs kill && echo "  已停止端口 $(PORT) 上的预览服务"; \
	else \
	  echo "  端口 $(PORT) 上没有在运行的预览服务"; \
	fi

practice:
	@cd practice && python3 generate_practice.py --pdf

recite:
	@cd recite && python3 generate_recite.py --pdf

check:
	@cd check && python3 generate_check.py --all --pdf

outline:
	@cd outline && python3 generate_outline.py --pdf
