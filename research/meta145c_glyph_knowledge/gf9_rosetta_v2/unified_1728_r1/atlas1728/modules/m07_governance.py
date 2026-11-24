"""M07: bounded receipt budget, no external spending or utility score."""
from ..source import canon
MODULE='M07_GOVERNANCE_COST'
def run(ctx):
    estimated=len(canon({'id':ctx['coordinate'],'scope':ctx['source_sha'],'chapter':ctx['chapter_index']}))
    if not 0<estimated<=2048:raise ValueError('CANDIDATE_WIRE_TOO_LARGE')
    return {'module':MODULE,'pass':True,'estimated_bytes':estimated,'external_spend_usd':0,
            'welfare_score':'NOT_ESTABLISHED'}
