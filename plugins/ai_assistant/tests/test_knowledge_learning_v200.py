import sys
from pathlib import Path
PLUGIN_DIR=Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path: sys.path.insert(0,str(PLUGIN_DIR))
from services.knowledge_learning import KnowledgeLearningService

def analysis(fp='abc'):
 return {'file':{'name':'pso-aqua2-ts-1080p.mkv','path':'X:/pso.mkv'},'identification':{'title_candidate':'pso aqua2 ts','media_type':'unknown'},'decision':{'title_candidate':'pso aqua2 ts','media_type':'unknown','episodes':[]},'in_video':{'agents':{'fingerprint_agent':{'video_fingerprint':fp}}}}

def test_confirmed_correction_learns_alias_and_fingerprint(tmp_path):
 svc=KnowledgeLearningService(tmp_path/'knowledge.sqlite3')
 result=svc.confirm(analysis(),{'title':'Planet Survival OVA','media_type':'movie','aliases':['PSO'],'year':2024})
 assert result['status']=='confirmed_and_learned'
 assert svc.lookup('PSO')[0]['canonical_title']=='Planet Survival OVA'
 assert svc.fingerprints.lookup('abc')['title']=='Planet Survival OVA'

def test_conflicting_alias_is_recorded(tmp_path):
 svc=KnowledgeLearningService(tmp_path/'knowledge.sqlite3')
 svc.confirm(analysis('a'),{'title':'First Title','media_type':'movie','aliases':['PSO']})
 second=svc.confirm(analysis('b'),{'title':'Other Title','media_type':'movie','aliases':['PSO']})
 assert second['conflicts']
 assert svc.conflicts()

def test_audiobook_learning_and_export(tmp_path):
 svc=KnowledgeLearningService(tmp_path/'knowledge.sqlite3')
 svc.confirm(analysis('book'),{'title':'Test Hörbuch','media_type':'audiobook','aliases':['THB']})
 snap=svc.export_snapshot()
 assert 'audiobook' in snap['supports_media_types']
 assert snap['identities'][0]['media_type']=='audiobook'
