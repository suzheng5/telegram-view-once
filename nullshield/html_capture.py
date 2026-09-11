"""把生成的 HTML 页面截成图片，供发图粘贴。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

_BROWSERS = (
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    / "Google"
    / "Chrome"
    / "Application"
    / "chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    / "Microsoft"
    / "Edge"
    / "Application"
    / "msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    / "Microsoft"
    / "Edge"
    / "Application"
    / "msedge.exe",
)

_CAPTURE_CSS = """
<style id="ns-capture">
html, body {
  min-height: 0 !important;
  height: auto !important;
  padding: 0 !important;
  margin: 0 !important;
  background: #0b1622 !important;
}
.dossier {
  margin: 0 !important;
  max-width: none !important;
  box-shadow: none !important;
}
.body-grid { align-items: start !important; }
.sidebar { height: auto !important; }
.sidebar-extra { margin-top: 16px !important; }
</style>
"""
_EMPTY_RGB = (11, 22, 34)
_EMPTY_TOLERANCE = 8


def _browser() -> Path | None:
    for path in _BROWSERS:
        if path.is_file():
            return path
    return None


def _wait_file(path: Path, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if path.is_file() and path.stat().st_size > 1000:
                return True
        except OSError:
            pass
        time.sleep(0.12)
    return False


def _qt_ready() -> bool:
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:
        return False
    return QApplication.instance() is not None


def _prepare_html(html_path: Path) -> bytes:
    text = html_path.read_text(encoding="utf-8")
    if "id=\"ns-capture\"" not in text:
        if "</head>" in text:
            text = text.replace("</head>", _CAPTURE_CSS + "</head>", 1)
        else:
            text = _CAPTURE_CSS + text
    return text.encode("utf-8")


def _is_empty(pixel: tuple[int, int, int]) -> bool:
    return all(abs(pixel[i] - _EMPTY_RGB[i]) <= _EMPTY_TOLERANCE for i in range(3))


def crop_empty_margins(image_path: Path) -> None:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    pixels = image.load()
    step = 4

    def row_empty(y: int) -> bool:
        return all(_is_empty(pixels[x, y]) for x in range(0, width, step))

    top = 0
    while top < height - 1 and row_empty(top):
        top += 1
    bottom = height - 1
    while bottom > top and row_empty(bottom):
        bottom -= 1
    pad = 2
    box = (0, max(0, top - pad), width, min(height, bottom + 1 + pad))
    if box[3] - box[1] < 80 or box[3] - box[1] >= height:
        return
    image.crop(box).save(image_path, "PNG", optimize=True)


def capture_html_png(html_path: Path, png_path: Path) -> Path:
    png_path = png_path.resolve()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    browser = _browser()
    if browser:
        _capture_browser(browser, html_path.resolve(), png_path)
    elif _qt_ready():
        _capture_webengine(html_path.resolve(), png_path)
    else:
        raise RuntimeError("找不到 Chrome / Edge，无法把页面复制成图片")
    crop_empty_margins(png_path)
    if not png_path.is_file() or png_path.stat().st_size < 1000:
        raise RuntimeError("页面截图失败，没有生成可用图片")
    return png_path


def _capture_browser(browser: Path, html_path: Path, png_path: Path) -> None:
    tmp_dir = Path(tempfile.gettempdir())
    tmp_html = tmp_dir / "nullshield_capture.html"
    tmp_png = tmp_dir / "nullshield_capture.png"
    tmp_html.write_bytes(_prepare_html(html_path))
    if tmp_png.exists():
        tmp_png.unlink()
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--force-device-scale-factor=2",
        "--window-size=1280,1800",
        "--full-page-screenshot",
        f"--screenshot={tmp_png}",
        tmp_html.resolve().as_uri(),
    ]
    subprocess.run(
        cmd,
        cwd=str(tmp_dir),
        timeout=45,
        check=False,
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_file(tmp_png):
        if _qt_ready():
            _capture_webengine(html_path, png_path)
            crop_empty_margins(png_path)
            return
        raise RuntimeError("浏览器截图超时")
    shutil.copyfile(tmp_png, png_path)


def _capture_webengine(html_path: Path, png_path: Path) -> None:
    from PySide6.QtCore import QEventLoop, QTimer, QUrl, Qt
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        raise RuntimeError("需要先打开主窗口才能截图")

    tmp_html = Path(tempfile.gettempdir()) / "nullshield_capture.html"
    tmp_html.write_bytes(_prepare_html(html_path))
    view = QWebEngineView()
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    view.resize(1280, 900)
    view.show()
    loop = QEventLoop()
    view.loadFinished.connect(lambda _ok: QTimer.singleShot(500, loop.quit))
    QTimer.singleShot(20000, loop.quit)
    view.load(QUrl.fromLocalFile(str(tmp_html)))
    loop.exec()

    height_box = [900]

    def _got_height(value) -> None:
        try:
            height_box[0] = max(600, min(int(value), 4000))
        except (TypeError, ValueError):
            pass
        loop.quit()

    view.page().runJavaScript(
        "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)",
        _got_height,
    )
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    view.resize(1280, height_box[0] + 8)
    QTimer.singleShot(350, loop.quit)
    loop.exec()
    pix = view.grab()
    view.close()
    view.deleteLater()
    if pix.isNull() or not pix.save(str(png_path), "PNG"):
        raise RuntimeError("WebEngine 截图失败")
