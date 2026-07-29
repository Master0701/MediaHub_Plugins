import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.tool_resolver import ToolResolver


def test_finds_tools_in_sibling_mediahub_project(tmp_path):
    workspace = tmp_path / "workspace"
    plugin_path = workspace / "MediaHub-Plugins" / "plugins" / "ai_assistant"
    tool_dir = workspace / "MediaHub" / "tools" / "ffmpeg" / "bin"
    tool_dir.mkdir(parents=True)
    plugin_path.mkdir(parents=True)

    ffprobe = tool_dir / "ffprobe.exe"
    ffmpeg = tool_dir / "ffmpeg.exe"
    ffprobe.write_bytes(b"test")
    ffmpeg.write_bytes(b"test")

    resolver = ToolResolver(plugin_path, plugin_path)

    assert resolver.find("ffprobe") == ffprobe.resolve()
    assert resolver.find("ffmpeg") == ffmpeg.resolve()


def test_finds_mediainfo_and_tesseract_in_nested_tool_folders(tmp_path):
    workspace = tmp_path / "workspace"
    plugin_path = workspace / "MediaHub-Plugins" / "plugins" / "ai_assistant"
    tools = workspace / "MediaHub" / "tools"
    plugin_path.mkdir(parents=True)

    mediainfo = tools / "MediaInfo" / "MediaInfo.exe"
    tesseract = tools / "Tesseract-OCR" / "tesseract.exe"
    mediainfo.parent.mkdir(parents=True)
    tesseract.parent.mkdir(parents=True)
    mediainfo.write_bytes(b"test")
    tesseract.write_bytes(b"test")

    resolver = ToolResolver(plugin_path, plugin_path)

    assert resolver.find("mediainfo") == mediainfo.resolve()
    assert resolver.find("tesseract") == tesseract.resolve()


def test_plugin_local_tools_remain_supported(tmp_path):
    plugin_path = tmp_path / "standalone" / "ai_assistant"
    local_tool = plugin_path / "tools" / "ffprobe.exe"
    local_tool.parent.mkdir(parents=True)
    local_tool.write_bytes(b"test")

    resolver = ToolResolver(plugin_path, plugin_path)

    assert resolver.find("ffprobe") == local_tool.resolve()
