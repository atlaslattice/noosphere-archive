"""M08: reversible authored glyph and distinct synthetic cymatic namespace."""
from ..shared import identity_address,reverse_address
MODULE='M08_GLYPH_NAVIGATION'
def run(ctx):
    nid=ctx['coordinate'];root=ctx['source_sha']
    glyph=identity_address(nid,root)
    if reverse_address(glyph,root)!=nid:raise ValueError('GLYPH_NOT_REVERSIBLE')
    h,s,n=(int(nid[1:3]),int(nid[5:7]),int(nid[9:11]))
    gf=f'GF7.B{h:02d}.M{s:02d}.C{n:02d}'
    return {'module':MODULE,'pass':True,'axg1':glyph,'gf7_positional_analogy':gf,
            'physics_equivalence':False,'semantics_equivalence':False}
