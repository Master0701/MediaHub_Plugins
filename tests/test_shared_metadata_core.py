from mediahub_metadata_core import (
    AUDIO_EXTENSIONS,
    FORMAT_CAPABILITIES,
    SAFE_WRITE_POLICY,
    VIDEO_EXTENSIONS,
    capability_for_extension,
)


def test_known_video_formats():
    assert ".mkv" in VIDEO_EXTENSIONS
    assert ".mp4" in VIDEO_EXTENSIONS
    assert ".m4v" in VIDEO_EXTENSIONS


def test_known_audio_formats():
    assert ".mp3" in AUDIO_EXTENSIONS
    assert ".m4a" in AUDIO_EXTENSIONS
    assert ".m4b" in AUDIO_EXTENSIONS
    assert ".flac" in AUDIO_EXTENSIONS
    assert ".ogg" in AUDIO_EXTENSIONS
    assert ".opus" in AUDIO_EXTENSIONS


def test_mkv_prefers_mkvtoolnix():
    capability = capability_for_extension(".mkv")
    assert capability["supported"] is True
    assert capability["write_backend"] == "mkvtoolnix"
    assert capability["fallback_write_backend"] == "ffmpeg"
    assert capability["stream_copy_only"] is True


def test_mp4_has_conservative_write_allowlist():
    capability = capability_for_extension(".mp4")
    assert capability["write_backend"] == "ffmpeg"
    assert capability["conservative"] is True
    assert "title" in capability["write_fields"]
    assert "media_type" not in capability["write_fields"]
    assert "series" not in capability["write_fields"]


def test_audio_requires_provider_for_write():
    for extension in (".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".opus"):
        capability = capability_for_extension(extension)
        assert capability["provider_required"] is True
        assert capability["write_backend"] == "audio_provider"
        assert capability["direct_write"] is False


def test_unsafe_formats_are_read_only():
    for extension in (".avi", ".wmv", ".ts", ".m2ts", ".wav"):
        capability = capability_for_extension(extension)
        assert capability["write_fields"] == []
        assert capability["direct_write"] is False


def test_unknown_format_is_never_writable():
    capability = capability_for_extension(".xyz")
    assert capability["supported"] is False
    assert capability["write_backend"] is None
    assert capability["write_fields"] == []
    assert capability["direct_write"] is False


def test_safe_write_policy():
    assert SAFE_WRITE_POLICY["automatic_apply_allowed"] is False
    assert SAFE_WRITE_POLICY["human_confirmation_required"] is True
    assert SAFE_WRITE_POLICY["backup_required"] is True
    assert SAFE_WRITE_POLICY["verify_after_write"] is True


def test_format_table_is_not_empty():
    assert FORMAT_CAPABILITIES
