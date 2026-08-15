from pathlib import Path
from services.media_detection import MediaDetector

detector=MediaDetector()

def detect(name):
    return detector.detect(Path(name))

def test_exact_480p_case():
    r=detect("lim-12monkeys-s03e01-480p.mkv")
    assert (r.media_type,r.season,r.episode,r.episode_end,r.episode_title)==("series","03","01","","")

def test_resolution_tokens():
    for token in ("480p","576p","576i","720p","1080p","1080i","1440p","2160p","4320p","4K"):
        r=detect(f"show-s03e01-{token}.mkv")
        assert (r.season,r.episode,r.episode_end,r.episode_title)==("03","01","",""), token

def test_x_style_resolution_tokens():
    for token in ("480p","576i","720p","1080p","1440p","2160p","4320p","4K"):
        r=detect(f"show-3x01-{token}.mkv")
        assert (r.season,r.episode,r.episode_end,r.episode_title)==("03","01","",""), token

def test_real_multi_episode_syntax():
    cases={
        "show-s03e01-02.mkv":"02",
        "show-s03e01-e02.mkv":"02",
        "show-s03e01e02.mkv":"02",
        "show-s03e01-to-02.mkv":"02",
        "show-3x01-02.mkv":"02",
        "show-3x01x02.mkv":"02",
    }
    for name,end in cases.items():
        r=detect(name)
        assert (r.season,r.episode,r.episode_end)==("03","01",end), name

def test_quality_tokens():
    for token in ("WEB-DL","WEBRip","BluRay","HDR","DV","HEVC","x264","x265","H264","H265"):
        r=detect(f"show-s03e01-{token}.mkv")
        assert r.episode_end=="", token
        assert r.episode_title=="", token
