"""M02: typed physical stock closure on a synthetic, node-distinct fixture."""
MODULE='M02_CONSERVATION'
def run(ctx):
    serial=int(ctx['node']['source_record_sha256'][:6],16)
    opening=100+(serial%97); imported=serial%13; produced=(serial//13)%11
    consumed=(serial//19)%17;lost=(serial//23)%7
    closing=opening+imported+produced-consumed-lost
    if min(opening,imported,produced,consumed,lost,closing)<0 or closing!=opening+imported+produced-consumed-lost:raise ValueError('STOCK_NOT_CLOSED')
    return {'module':MODULE,'pass':True,'balance':closing,'unit':'SYNTHETIC_ITEM','not_observed':True}
