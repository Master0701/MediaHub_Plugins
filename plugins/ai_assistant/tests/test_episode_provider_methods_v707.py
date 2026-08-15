import os
import services.providers.tmdb_provider as tmdb_mod
import services.providers.tvdb_provider as tvdb_mod
from services.providers.tmdb_provider import TmdbProvider
from services.providers.tvdb_provider import TvdbProvider


def test_tmdb_resolves_concrete_episode(monkeypatch):
    monkeypatch.setenv("MEDIAHUB_TMDB_API_KEY","x")
    p=TmdbProvider({
        "id":"tmdb","name":"TMDb","type":"tmdb","enabled":True,
        "media_types":["series"],"language":"de-DE"
    })
    calls=[]
    def fake(url, **kwargs):
        calls.append(url)
        if "/search/tv" in url:
            return {"results":[{"id":69,"name":"12 Monkeys","first_air_date":"2015-01-16","vote_average":8.0}]}
        if "/tv/69/season/3/episode/2" in url:
            return {"id":1002,"name":"Wächter","air_date":"2017-05-26"}
        raise AssertionError(url)
    monkeypatch.setattr(tmdb_mod,"request_json",fake)
    r=p.resolve_episode({"title":"12 Monkeys","season":3,"episode":2})
    assert r["status"]=="ok"
    assert r["episode_title"]=="Wächter"


def test_tvdb_resolves_concrete_episode(monkeypatch):
    monkeypatch.setenv("MEDIAHUB_TVDB_API_KEY","x")
    p=TvdbProvider({
        "id":"tvdb","name":"TheTVDB","type":"tvdb","enabled":True,
        "media_types":["series"],"language":"de-DE"
    })
    def fake(url, **kwargs):
        if url.endswith("/login"):
            return {"data":{"token":"token"}}
        if url.endswith("/search"):
            return {"data":[{"tvdb_id":"272644","name":"12 Monkeys","type":"series","year":"2015"}]}
        if "/series/272644/episodes/default/deu" in url:
            return {"data":{"episodes":[
                {"id":55,"seasonNumber":3,"number":2,"name":"Wächter"}
            ]}}
        raise AssertionError(url)
    monkeypatch.setattr(tvdb_mod,"request_json",fake)
    r=p.resolve_episode({"title":"12 Monkeys","season":3,"episode":2})
    assert r["status"]=="ok"
    assert r["episode_title"]=="Wächter"
