from pathlib import Path
from services.media_detection import MediaDetector

detector=MediaDetector()

def detect(name):
    return detector.detect(Path(name))

def assert_clean(name, season="01", episode="01", episode_end="", episode_title=""):
    r=detect(name)
    assert r.media_type=="series", (name,r)
    assert r.season==season, (name,r.season)
    assert r.episode==episode, (name,r.episode)
    assert r.episode_end==episode_end, (name,r.episode_end)
    assert r.episode_title==episode_title, (name,r.episode_title)

def test_real_world_technical_suffixes():
    names=(
        "show.S01E01.1080p.WEB-DL.DDP5.1.H.265-HDR.mkv",
        "show.S01E01.2160p.WEB-DL.DDP5.1.DV.HDR.HEVC.mkv",
        "show.S01E01.720p.WEBRip.x264.AAC2.0.mkv",
        "show.S01E01.1080i.HDTV.H264.AC3.mkv",
        "show.S01E01.1080p.BluRay.DTS-HD.MA.x264.mkv",
        "show.S01E01.2160p.UHD.BDREMUX.TrueHD.Atmos.HEVC.mkv",
        "show.S01E01.1080p.NF.WEB-DL.DDP5.1.x265.mkv",
        "show.S01E01.1080p.AMZN.WEB-DL.DDP5.1.H264.mkv",
        "show.S01E01.1080p.DSNP.WEB-DL.DDP5.1.H265.mkv",
        "show.S01E01.1080p.10bit.HEVC.mkv",
        "show.S01E01.1080p.Hi10P.x264.mkv",
        "show.S01E01.4K.WEBRip.AV1.mkv",
    )
    for name in names:
        assert_clean(name)

def test_release_flags():
    for token in ("PROPER","REPACK","RERIP","INTERNAL","LIMITED","MULTI","DUAL-AUDIO"):
        assert_clean(f"show.S01E01.1080p.WEB-DL.{token}.x265.mkv")

def test_resolution_tokens():
    for token in ("480p","576p","576i","720p","1080p","1080i","1440p","2160p","4320p","4K","8K"):
        assert_clean(f"show-S01E01-{token}.mkv")

def test_episode_titles_survive():
    cases={
        "show.S01E01.The Beginning.1080p.WEB-DL.x265.mkv":"The Beginning",
        "show.S01E01-A New Hope-2160p-BluRay-HEVC.mkv":"A New Hope",
        "show.S01E01.Der Anfang.720p.HDTV.H264.mkv":"Der Anfang",
    }
    for name,title in cases.items():
        assert_clean(name,episode_title=title)

def test_multi_episode_survives():
    cases={
        "show.S01E01-E02.1080p.WEB-DL.x265.mkv":"02",
        "show.S01E01E02.2160p.BluRay.HEVC.mkv":"02",
        "show.S01E01-02.720p.WEBRip.x264.mkv":"02",
        "show.1x01-02.1080p.HDTV.H264.mkv":"02",
    }
    for name,end in cases.items():
        assert_clean(name,episode_end=end)

def test_previous_480p_problem():
    assert_clean("lim-12monkeys-s03e01-480p.mkv",season="03")
