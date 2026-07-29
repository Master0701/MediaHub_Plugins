from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from services.knowledge_engine.models import RelationType


class GraphReasoner:
    """Leitet vorsichtige, erklärbare Erkenntnisse aus vorhandenen Graphdaten ab.

    Ableitungen werden nicht automatisch gespeichert. Dadurch bleiben importierte
    und vom Benutzer bestätigte Daten klar von maschinellen Vorschlägen getrennt.
    """

    GROUP_RELATIONS = {
        RelationType.FRANCHISE.value,
        RelationType.UNIVERSE.value,
        RelationType.SPIN_OFF.value,
        RelationType.PREQUEL.value,
        RelationType.SEQUEL.value,
        RelationType.CONTINUES_IN.value,
        RelationType.REBOOT.value,
        RelationType.REMAKE.value,
        RelationType.ALTERNATE_TIMELINE.value,
        RelationType.PART_OF.value,
    }

    def __init__(self, store: Any):
        self.store = store

    def analyze(self, query_or_id: str | None = None, *, max_depth: int = 8) -> dict[str, Any]:
        entities = self.store.all_entities()
        relations = self.store.all_relations()
        if query_or_id:
            root = self.store.get_entity(str(query_or_id))
            if root is None:
                matches = self.store.find_entities(str(query_or_id))
                root = matches[0] if matches else None
            if root:
                allowed = self._component_ids(str(root['id']), relations, max_depth=max_depth)
                entities = [e for e in entities if str(e.get('id')) in allowed]
                relations = [r for r in relations if str(r.get('source_id')) in allowed and str(r.get('target_id')) in allowed]
        clusters = self._clusters(entities, relations)
        suggestions = []
        suggestions.extend(self._infer_group_relations(clusters, relations))
        suggestions.extend(self._infer_story_relations(entities, relations))
        suggestions.extend(self._order_gaps())
        return {
            'schema_version': 1,
            'strategy': 'knowledge_graph_intelligence_v1',
            'query': query_or_id,
            'clusters': clusters,
            'suggestions': suggestions,
            'suggestion_count': len(suggestions),
            'persisted': False,
        }

    def _component_ids(self, root_id: str, relations: list[dict[str, Any]], *, max_depth: int) -> set[str]:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for relation in relations:
            if str(relation.get('relation_type')) not in self.GROUP_RELATIONS | {
                RelationType.STARTS_IN_EPISODE.value, RelationType.BACKDOOR_PILOT.value,
                RelationType.EPISODE_OF.value, RelationType.SEASON_OF.value,
                RelationType.CROSSOVER.value, RelationType.CROSSOVER_EVENT.value,
            }:
                continue
            a, b = str(relation.get('source_id')), str(relation.get('target_id'))
            adjacency[a].add(b); adjacency[b].add(a)
        seen={root_id}; queue=deque([(root_id,0)])
        while queue:
            current, depth=queue.popleft()
            if depth >= max_depth: continue
            for nxt in adjacency.get(current, set()):
                if nxt not in seen:
                    seen.add(nxt); queue.append((nxt, depth+1))
        return seen

    def _clusters(self, entities: list[dict[str, Any]], relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids={str(e.get('id')) for e in entities}; adjacency={i:set() for i in ids}
        relation_types: dict[frozenset[str], set[str]] = defaultdict(set)
        for r in relations:
            rt=str(r.get('relation_type')); a=str(r.get('source_id')); b=str(r.get('target_id'))
            if rt not in self.GROUP_RELATIONS or a not in ids or b not in ids: continue
            adjacency[a].add(b); adjacency[b].add(a); relation_types[frozenset((a,b))].add(rt)
        by_id={str(e.get('id')):e for e in entities}; seen=set(); result=[]
        for start in sorted(ids):
            if start in seen: continue
            stack=[start]; component=[]; types=set()
            while stack:
                current=stack.pop()
                if current in seen: continue
                seen.add(current); component.append(current)
                for nxt in adjacency[current]:
                    types.update(relation_types[frozenset((current,nxt))]); stack.append(nxt)
            if len(component) < 2: continue
            members=[by_id[x] for x in component]
            explicit_universe=RelationType.UNIVERSE.value in types
            explicit_franchise=RelationType.FRANCHISE.value in types
            confidence=min(.98, .62 + .06*len(component) + (.12 if explicit_universe or explicit_franchise else 0))
            result.append({
                'member_ids': sorted(component),
                'titles': sorted(str(e.get('title') or '') for e in members),
                'relation_types': sorted(types),
                'classification': 'universe' if explicit_universe else 'franchise',
                'confidence': round(confidence, 4),
                'reason': f"{len(component)} verbundene Medien über {', '.join(sorted(types))}",
            })
        return result

    def _infer_group_relations(self, clusters: list[dict[str, Any]], relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        existing={(str(r.get('source_id')),str(r.get('target_id')),str(r.get('relation_type'))) for r in relations}
        suggestions=[]
        for cluster in clusters:
            ids=cluster['member_ids']; classification=cluster['classification']
            relation_type=RelationType.UNIVERSE.value if classification=='universe' else RelationType.FRANCHISE.value
            anchor=ids[0]
            for member in ids[1:]:
                if (anchor,member,relation_type) in existing or (member,anchor,relation_type) in existing: continue
                suggestions.append({
                    'kind':'derived_relation','source_id':anchor,'target_id':member,
                    'relation_type':relation_type,'confidence':cluster['confidence'],
                    'reason':cluster['reason'],'requires_confirmation':True,
                })
        return suggestions

    def _infer_story_relations(self, entities: list[dict[str, Any]], relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id={str(e.get('id')):e for e in entities}; episode_parent={}
        existing={(str(r.get('source_id')),str(r.get('target_id')),str(r.get('relation_type'))) for r in relations}
        for r in relations:
            if str(r.get('relation_type'))==RelationType.EPISODE_OF.value:
                episode_parent[str(r.get('source_id'))]=str(r.get('target_id'))
        suggestions=[]
        for r in relations:
            rt=str(r.get('relation_type'))
            if rt not in {RelationType.STARTS_IN_EPISODE.value, RelationType.BACKDOOR_PILOT.value}: continue
            target=str(r.get('target_id')); parent=episode_parent.get(target)
            if not parent: continue
            source=str(r.get('source_id'))
            if (source,parent,RelationType.SPIN_OFF.value) not in existing:
                episode=by_id.get(target,{}); parent_entity=by_id.get(parent,{})
                suggestions.append({
                    'kind':'derived_relation','source_id':source,'target_id':parent,
                    'relation_type':RelationType.SPIN_OFF.value,'confidence':.9,
                    'reason':f"Start/Backdoor-Pilot in {parent_entity.get('title','Serie')} – {episode.get('title','Episode')}",
                    'evidence_relation_id':r.get('id'),'requires_confirmation':True,
                })
        return suggestions

    def _order_gaps(self) -> list[dict[str, Any]]:
        suggestions=[]
        for order in self.store.all_orders():
            entries=sorted(order.get('entries') or [], key=lambda e:int(e.get('position') or 0))
            positions=[int(e.get('position') or 0) for e in entries]
            expected=list(range(1,len(entries)+1))
            if positions != expected:
                suggestions.append({'kind':'order_gap','order_id':order.get('id'),'order_name':order.get('name'),
                    'positions':positions,'expected_positions':expected,'confidence':1.0,
                    'reason':'Reihenfolge enthält fehlende oder doppelte Positionen','requires_confirmation':False})
        return suggestions
