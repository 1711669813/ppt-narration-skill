"""Keep task outputs and caches under this package's results directory."""
import os
from pathlib import Path
import tempfile
import sys

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

if getattr(sys, "frozen", False) or os.environ.get("PPT_DESKTOP_MODE") == "1":
    # Packaged resources are temporary/read-only; desktop output must persist.
    RESULTS = Path(os.environ.get("PPT_DESKTOP_RESULTS", str(Path(sys.executable).parent / "results"))).resolve()
else:
    RESULTS = Path(__file__).resolve().parents[1] / "results"


def output_path(value=None, default=None):
    """Resolve relative paths under results; reject paths outside it."""
    path = Path(value or default or RESULTS).expanduser()
    if not path.is_absolute():
        path = RESULTS / path
    path = path.resolve()
    if not path.is_relative_to(RESULTS.resolve()):
        raise ValueError("输出路径必须位于 %s 下：%s" % (RESULTS, path))
    return str(path)


def build_root():
    return output_path(os.environ.get("BUILD_ROOT"))


def delivery_root():
    return output_path(os.environ.get("OUT_DIR"), build_root())


MODEL_CACHE = output_path("cache/huggingface/hub")
TEMP = output_path("tmp")
os.makedirs(TEMP, exist_ok=True)
os.environ["TMP"] = os.environ["TEMP"] = os.environ["TMPDIR"] = TEMP
tempfile.tempdir = TEMP
os.environ["HF_HOME"] = output_path("cache/huggingface")
os.environ["HF_HUB_CACHE"] = MODEL_CACHE
os.environ["HF_XET_CACHE"] = output_path("cache/huggingface/xet")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
