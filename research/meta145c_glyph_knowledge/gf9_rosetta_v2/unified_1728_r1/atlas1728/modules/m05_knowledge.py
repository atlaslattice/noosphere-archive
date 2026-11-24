"""M05: compiled source vocabulary and full historical topic scope, not SAME_AS."""
MODULE='M05_RESEARCH_RETRIEVAL'
def run(ctx):
    idx=ctx['index'];nid=ctx['coordinate'];roles=idx.topics[nid]
    pos=sum(x['role']=='PRIMARY' for x in roles);alt=len(roles)-pos
    if not all(x['status']=='UNREVIEWED_HEURISTIC_NOT_SEMANTIC_EQUIVALENCE' for x in roles):raise ValueError('UNREVIEWED_TOPIC_REQUIRED')
    return {'module':MODULE,'pass':True,'token_count':len(idx.terms[nid]),'topic_candidates':len(roles),'primary':pos,'alternate':alt,
            'semantic_equivalence':'NOT_ESTABLISHED','untruncated':True}
