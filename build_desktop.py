"""Build a self-contained Windows executable in results/desktop-dist."""
from pathlib import Path
import shutil
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"


def main():
    if sys.platform != "win32":
        raise SystemExit("请在 Windows x64 上构建桌面版。")
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(OUT / "cache" / "pyinstaller")
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--console", "--noupx", "--name", "PPTNarration-v0.1.0-Windows-x64",
            "--distpath", str(OUT / "desktop-dist"), "--workpath", str(OUT / "desktop-build"),
            "--specpath", str(OUT / "desktop-build"),
            "--add-data", str(ROOT / "scripts") + ";scripts",
            "--add-data", str(ROOT / "references") + ";references",
            "--add-data", str(ROOT / "docs" / "desktop-guide.md") + ";docs",
            "--add-data", str(ROOT / "docs" / "third-party-notices.txt") + ";docs"]
    args += ["--add-data", str(ROOT / "docs" / "FFmpeg-GPLv3.txt") + ";docs"]
    for exe in ("ffmpeg", "ffprobe"):
        path = shutil.which(exe)
        if not path:
            raise SystemExit("请先安装 FFmpeg 并将其加入 PATH。")
        args += ["--add-binary", path + ";bin"]
    for module in ("pptx", "edge_tts", "PIL", "mutagen", "numpy", "win32com", "requests"):
        args += ["--collect-all", module]
    args += ["--hidden-import", "pythoncom", "--hidden-import", "pywintypes",
             "--hidden-import", "win32timezone", "--hidden-import", "win32gui", "--hidden-import", "win32ui",
             "--hidden-import", "tkinter", "--hidden-import", "tkinter.ttk",
             "--hidden-import", "tkinter.filedialog", "--hidden-import", "tkinter.messagebox",
             "--hidden-import", "PIL._tkinter_finder", str(ROOT / "desktop_app.py")]
    subprocess.run(args, cwd=ROOT, check=True)
    print("EXE 已生成：", OUT / "desktop-dist")


if __name__ == "__main__":
    main()
