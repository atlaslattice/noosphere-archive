"""Compiled, revision-bound Ariadne source index; never grants host authorization."""
from __future__ import annotations
from collections import defaultdict
from .shared import terms

class SourceIndex:
    def __init__(self,corpus):
        self.corpus=corpus
        self.ids=tuple(sorted(corpus.nodes))
        self.direct={nid:corpus.nodes[nid] for nid in self.ids}
        self.terms={nid:terms(corpus.nodes[nid]['name']+' '+corpus.spheres[nid[:7]]['name']) for nid in self.ids}
        posting=defaultdict(list)
        for nid in self.ids:
            for t in self.terms[nid]:posting[t].append(nid)
        self.postings={t:tuple(vals) for t,vals in posting.items()}
        self.pathways={sid:tuple(corpus.spheres[sid]['children']) for sid in sorted(corpus.spheres)}
        self.topics={nid:tuple(corpus.topic_edges.get(nid,())) for nid in self.ids}
        self.source_id=(corpus.registry_sha,corpus.topic_sha)
    def indexed_find(self,nid):
        if nid not in self.direct:raise ValueError('COORDINATE_NOT_INDEXED')
        return self.direct[nid],1
    def linear_find(self,nid):
        # Fair baseline: early stop on match, not a forced exhaustive scan.
        for i,key in enumerate(self.ids,1):
            if key==nid:return self.corpus.nodes[key],i
        raise ValueError('COORDINATE_NOT_INDEXED')
    def search(self,query,mode='ANY'):
        if mode not in ('ANY','DOMAIN','METHOD'):raise ValueError('ROLE_SEARCH_UNSUPPORTED')
        tokens=terms(query)
        if not tokens:return []
        counts=defaultdict(int)
        for t in tokens:
            for nid in self.postings.get(t,()):counts[nid]+=1
        def match(nid):
            r=self.corpus.nodes[nid]['kind']
            return mode=='ANY' or mode=='DOMAIN' and r=='DOMAIN_SPECIALIZATION' or mode=='METHOD' and r=='EPISTEMIC_META'
        return sorted(((n,v) for n,v in counts.items() if match(n)),key=lambda p:(-p[1],p[0]))
    def linear_search(self,query,mode='ANY'):
        q=terms(query)
        if not q:return []
        rs=[]
        for nid in self.ids:
            kind=self.corpus.nodes[nid]['kind']
            if mode=='DOMAIN' and kind!='DOMAIN_SPECIALIZATION' or mode=='METHOD' and kind!='EPISTEMIC_META':continue
            n=len(q&self.terms[nid])
            if n:rs.append((nid,n))
        return sorted(rs,key=lambda p:(-p[1],p[0]))
