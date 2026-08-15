from services.episode_title_resolver import EpisodeTitleResolver
from services.multi_source_fusion import MultiSourceFusion


class Sources:
    def __init__(self, results):
        self.results=results
    def resolve_episode_candidates(self, query):
        return list(self.results)


def test_two_agreeing_sources_are_accepted():
    r=EpisodeTitleResolver(
        Sources([
            {"status":"ok","provider":"tmdb","episode_title":"Wächter","confidence":0.96},
            {"status":"ok","provider":"tvdb","episode_title":"Wächter","confidence":0.96},
        ]),
        MultiSourceFusion(),
    ).resolve({"title":"12 Monkeys","season":3,"episode":2})
    assert r["accepted"] is True
    assert r["episode_title"]=="Wächter"
    assert r["confidence"] > 0.9


def test_one_strong_tmdb_source_can_pass_threshold():
    r=EpisodeTitleResolver(
        Sources([
            {"status":"ok","provider":"tmdb","episode_title":"Wächter","confidence":0.96},
        ]),
        MultiSourceFusion(),
    ).resolve({"title":"12 Monkeys","season":3,"episode":2})
    assert r["accepted"] is True
    assert r["episode_title"]=="Wächter"


def test_no_provider_result_keeps_title_empty():
    r=EpisodeTitleResolver(
        Sources([
            {"status":"not_configured","provider":"tmdb","message":"key fehlt"},
            {"status":"not_configured","provider":"tvdb","message":"key fehlt"},
        ]),
        MultiSourceFusion(),
    ).resolve({"title":"12 Monkeys","season":3,"episode":2})
    assert r["accepted"] is False
    assert r["episode_title"]==""
