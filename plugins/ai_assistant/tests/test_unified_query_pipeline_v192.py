import sys
from pathlib import Path
PLUGIN_DIR=Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path: sys.path.insert(0,str(PLUGIN_DIR))

from services.query_plan import build_query_plan
from services.multi_query_provider_runner import MultiQueryProviderRunner

class Result:
    def __init__(self,title): self.title=title
    def as_dict(self): return {"provider_id":"fake","provider_name":"Fake","status":"ok","matches":[],"message":"ok"}
class Provider:
    id='fake'; name='Fake'; config={'priority':50}
    def __init__(self): self.titles=[]
    def status(self): return {'priority':50,'trust':.8,'type':'fake'}
    def search(self,q): self.titles.append(q['title']); return Result(q['title'])
class Manager:
    executor=None
    def __init__(self): self.provider=Provider()
    def eligible_providers(self,q): return [self.provider]

def test_only_accepted_query_plan_variants_reach_provider():
    query={
      'title':'pso aqua2 ts',
      'search_variants':[{'title':'pso aqua2 ts','score':.93,'source':'filename','quality_score':.88}],
      'query_reasoning':{'quality_gate':{'rejected':[{'title':'pso aqua'},{'title':'aqua'}]}},
    }
    query['query_plan']=build_query_plan(query)
    manager=Manager(); MultiQueryProviderRunner(manager).run(query)
    assert manager.provider.titles==['pso aqua2 ts']
    assert 'pso aqua' not in manager.provider.titles
    assert 'aqua' not in manager.provider.titles

def test_runner_does_not_invent_primary_fallback_without_plan():
    manager=Manager(); MultiQueryProviderRunner(manager).run({'title':'aqua','search_variants':[]})
    assert manager.provider.titles==[]
