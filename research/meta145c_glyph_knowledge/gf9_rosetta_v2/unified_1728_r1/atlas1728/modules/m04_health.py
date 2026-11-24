"""M04: do not export private case bodies or claim medical expertise."""
MODULE='M04_HEALTH_PRIVACY'
def run(ctx):
    if ctx['mode']!='WORK' or any(k in ctx['input_claims'] for k in ('private_context','patient_data','play_data','resident_secret')):raise ValueError('PRIVATE_MODE_EXPORT_DENIED')
    return {'module':MODULE,'pass':True,'private_payload_fields':0,'medical_authority':'NONE',
            'source_evidence_exposed':'DIGEST_ONLY'}
