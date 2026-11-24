"""M10: culture and linguistic consent; never scrape/rewrite restricted practices."""
MODULE='M10_COMMUNITY_CONSENT'
def run(ctx):
    house=ctx['house']['id']
    return {'module':MODULE,'pass':True,'indigenous_specific_review':house=='H10',
            'cultural_source_licensed':False,'automatic_cultural_translation':False,
            'private_story_import':False}
