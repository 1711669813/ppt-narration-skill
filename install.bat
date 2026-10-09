@echo off
REM PPT 讲解录屏生成包 —— 一键安装依赖（Windows）
setlocal
set PY=%1
if "%PY%"=="" set PY=python

echo == 使用的解释器 ==
%PY% -c "import sys; print(sys.executable)"

echo.
echo == 检查 ffmpeg（必需，需在 PATH）==
where ffmpeg >nul 2>nul && (ffmpeg -version | findstr /b "ffmpeg version") || echo [警告] 未找到 ffmpeg，请安装并加入 PATH

echo.
echo == 安装依赖 ==
%PY% -m pip install --upgrade pip
%PY% -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo [失败] 默认解释器装不了包时，换一个带 pip 的解释器再跑本脚本，例如：
  echo     install.bat D:\anaconda3\python.exe
  echo   （用 py -0 可以列出本机所有 Python 版本）
  exit /b 1
)

echo.
echo == 环境自检 ==
%PY% "%~dp0scripts\00_check_env.py"
echo.
echo 完成。下一步：编辑 SKILL.md 里"最短指令"那段，连同本文件夹一起交给大模型。
endlocal
