"""M03: dependency ancestry with fail-closed scope and no inferred causality."""
MODULE='M03_INFRA_DEPENDENCIES'
def run(ctx):
    nid=ctx['coordinate'];sphere=ctx['sphere'];house=ctx['house']
    if ctx['node']['parent']!=sphere['id'] or sphere['parent']!=house['id'] or nid not in sphere['children'] or sphere['id'] not in house['children']:raise ValueError('DEPENDENCY_ANCESTRY')
    return {'module':MODULE,'pass':True,'chain':[house['id'],sphere['id'],nid],
            'edge_type':'SOURCE_HIERARCHY_NOT_CAUSAL_DEPENDENCY'}
