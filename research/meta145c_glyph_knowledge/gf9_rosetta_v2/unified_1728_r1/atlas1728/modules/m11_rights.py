"""M11: nonoffsettable rights separate from review and publication."""
MODULE='M11_RIGHTS_AND_APPEALS'
def run(ctx):
    if ctx['input_claims'].get('approved') or ctx['input_claims'].get('canon') or ctx['input_claims'].get('host_rights'):raise ValueError('AUTHORITY_LAUNDERING_DENIED')
    return {'module':MODULE,'pass':True,'host_read_return':'HELD','license_review':'REQUIRED',
            'canon_effect':'NONE','review_appeal_possible':True}
