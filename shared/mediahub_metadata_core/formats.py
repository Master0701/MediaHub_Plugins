from __future__ import annotations

COMMON_FIELDS = {
    "title",
    "description",
    "year",
    "published_at",
}

VIDEO_FIELDS = COMMON_FIELDS | {
    "series",
    "season",
    "episode",
    "episode_title",
    "channel",
    "playlist",
}

AUDIO_FIELDS = COMMON_FIELDS | {
    "artist",
    "album",
    "album_artist",
    "track",
    "disc",
    "genre",
    "composer",
    "comment",
}

AUDIOBOOK_FIELDS = AUDIO_FIELDS | {
    "author",
    "narrator",
    "book_series",
    "book_series_index",
    "publisher",
    "chapters",
}


FORMAT_CAPABILITIES = {
    ".mkv": {
        "kind": "video",
        "container": "matroska",
        "read_backend": "ffprobe",
        "write_backend": "mkvtoolnix",
        "fallback_write_backend": "ffmpeg",
        "read_fields": sorted(VIDEO_FIELDS),
        "write_fields": sorted(VIDEO_FIELDS),
        "direct_write": True,
        "stream_copy_only": True,
    },

    ".webm": {
        "kind": "video",
        "container": "webm",
        "read_backend": "ffprobe",
        "write_backend": "ffmpeg",
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": sorted({
            "title",
            "description",
            "published_at",
        }),
        "direct_write": True,
        "stream_copy_only": True,
        "conservative": True,
    },

    ".mp4": {
        "kind": "video",
        "container": "mp4",
        "read_backend": "ffprobe",
        "write_backend": "ffmpeg",
        "read_fields": sorted(VIDEO_FIELDS),
        "write_fields": sorted({
            "title",
            "description",
            "year",
            "published_at",
            "comment",
        }),
        "direct_write": True,
        "stream_copy_only": True,
        "conservative": True,
    },

    ".m4v": {
        "kind": "video",
        "container": "mp4",
        "read_backend": "ffprobe",
        "write_backend": "ffmpeg",
        "read_fields": sorted(VIDEO_FIELDS),
        "write_fields": sorted({
            "title",
            "description",
            "year",
            "published_at",
            "comment",
        }),
        "direct_write": True,
        "stream_copy_only": True,
        "conservative": True,
    },

    ".mov": {
        "kind": "video",
        "container": "quicktime",
        "read_backend": "ffprobe",
        "write_backend": "ffmpeg",
        "read_fields": sorted(VIDEO_FIELDS),
        "write_fields": sorted({
            "title",
            "description",
            "year",
            "published_at",
            "comment",
        }),
        "direct_write": True,
        "stream_copy_only": True,
        "conservative": True,
    },

    ".avi": {
        "kind": "video",
        "container": "avi",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".wmv": {
        "kind": "video",
        "container": "asf",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".mpg": {
        "kind": "video",
        "container": "mpeg",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".mpeg": {
        "kind": "video",
        "container": "mpeg",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".ts": {
        "kind": "video",
        "container": "mpegts",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".m2ts": {
        "kind": "video",
        "container": "mpegts",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".mp3": {
        "kind": "audio",
        "container": "id3",
        "read_backend": "ffprobe",
        "write_backend": "audio_provider",
        "read_fields": sorted(AUDIO_FIELDS),
        "write_fields": sorted(AUDIO_FIELDS),
        "direct_write": False,
        "provider_required": True,
    },

    ".m4a": {
        "kind": "audio",
        "container": "mp4_audio",
        "read_backend": "ffprobe",
        "write_backend": "audio_provider",
        "read_fields": sorted(AUDIO_FIELDS),
        "write_fields": sorted(AUDIO_FIELDS),
        "direct_write": False,
        "provider_required": True,
    },

    ".m4b": {
        "kind": "audiobook",
        "container": "mp4_audio",
        "read_backend": "ffprobe",
        "write_backend": "audio_provider",
        "read_fields": sorted(AUDIOBOOK_FIELDS),
        "write_fields": sorted(AUDIOBOOK_FIELDS),
        "direct_write": False,
        "provider_required": True,
    },

    ".aac": {
        "kind": "audio",
        "container": "aac",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".flac": {
        "kind": "audio",
        "container": "flac",
        "read_backend": "ffprobe",
        "write_backend": "audio_provider",
        "read_fields": sorted(AUDIO_FIELDS),
        "write_fields": sorted(AUDIO_FIELDS),
        "direct_write": False,
        "provider_required": True,
    },

    ".ogg": {
        "kind": "audio",
        "container": "ogg",
        "read_backend": "ffprobe",
        "write_backend": "audio_provider",
        "read_fields": sorted(AUDIO_FIELDS),
        "write_fields": sorted(AUDIO_FIELDS),
        "direct_write": False,
        "provider_required": True,
    },

    ".opus": {
        "kind": "audio",
        "container": "opus",
        "read_backend": "ffprobe",
        "write_backend": "audio_provider",
        "read_fields": sorted(AUDIO_FIELDS),
        "write_fields": sorted(AUDIO_FIELDS),
        "direct_write": False,
        "provider_required": True,
    },

    ".wav": {
        "kind": "audio",
        "container": "wave",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },

    ".wma": {
        "kind": "audio",
        "container": "asf_audio",
        "read_backend": "ffprobe",
        "write_backend": None,
        "read_fields": sorted(COMMON_FIELDS),
        "write_fields": [],
        "direct_write": False,
    },
}


AUDIO_EXTENSIONS = tuple(
    sorted(
        extension
        for extension, definition in FORMAT_CAPABILITIES.items()
        if definition["kind"] in {"audio", "audiobook"}
    )
)

VIDEO_EXTENSIONS = tuple(
    sorted(
        extension
        for extension, definition in FORMAT_CAPABILITIES.items()
        if definition["kind"] == "video"
    )
)

SUPPORTED_EXTENSIONS = tuple(sorted(FORMAT_CAPABILITIES))


def capability_for_extension(extension: str) -> dict:
    normalized = str(extension or "").strip().lower()

    if normalized and not normalized.startswith("."):
        normalized = "." + normalized

    definition = FORMAT_CAPABILITIES.get(normalized)

    if definition is None:
        return {
            "extension": normalized,
            "supported": False,
            "kind": "unknown",
            "read_backend": None,
            "write_backend": None,
            "read_fields": [],
            "write_fields": [],
            "direct_write": False,
        }

    return {
        "extension": normalized,
        "supported": True,
        **definition,
    }
