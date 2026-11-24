"""M09: semantic-role and uncertainty gate, never coerces methods to topics."""
from ..source import DOMAIN,METHOD
MODULE='M09_EPISTEMIC_INTEGRITY'
def run(ctx):
    sphere_kinds={ctx['corpus'].nodes[n]['kind'] for n in ctx['sphere']['children']}
    if len(sphere_kinds)!=1 or ctx['node']['kind'] not in sphere_kinds:raise ValueError('METHOD_ROLE_MISMATCH')
    ismethod=ctx['node']['kind']==METHOD
    return {'module':MODULE,'pass':True,'role':ctx['node']['kind'],
            'epistemic_method_requires_subject':ismethod,'candidate_not_proof':True}
