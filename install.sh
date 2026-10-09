#!/usr/bin/env bash
# PPT 讲解录屏生成包 —— 一键安装依赖（macOS / Linux）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${1:-python3}"

echo "== 使用的解释器 =="
"$PY" -c "import sys; print(sys.executable)"

echo
echo "== 检查 ffmpeg（必需，需在 PATH）=="
if command -v ffmpeg >/dev/null 2>&1; then ffmpeg -version | head -1; else
  echo "[警告] 未找到 ffmpeg。macOS: brew install ffmpeg；Debian/Ubuntu: sudo apt install ffmpeg"
fi

echo
echo "== 检查页面导出工具（非 Windows 用 LibreOffice）=="
command -v soffice >/dev/null 2>&1 && echo "soffice 已就绪" || \
  echo "[提示] 未找到 soffice：macOS 安装 LibreOffice；Ubuntu: sudo apt install libreoffice"
command -v pdftoppm >/dev/null 2>&1 && echo "pdftoppm 已就绪" || echo "[提示] 建议安装 poppler-utils（提供 pdftoppm）"

echo
echo "== 安装依赖 =="
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r "$HERE/requirements.txt"

echo
echo "== 环境自检 =="
"$PY" "$HERE/scripts/00_check_env.py"
echo
echo "完成。下一步：把本文件夹连同 SKILL.md 里的“最短指令”交给大模型。"
