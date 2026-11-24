"""M06: independent source/epoch guard; local status never authenticates a host."""
MODULE='M06_SOURCE_SECURITY'
def run(ctx):
    if ctx['source_sha']!=ctx['corpus'].registry_sha or ctx['rights_epoch'] not in (None,):raise ValueError('UNTRUSTED_HOST_EPOCH')
    if ctx['node']['source_record_sha256']!=ctx['node_digest']:raise ValueError('SOURCE_RECORD_DRIFT')
    return {'module':MODULE,'pass':True,'source_pin':ctx['source_sha'][:12],
            'host_authorized':False,'return_epoch_verified':False}
