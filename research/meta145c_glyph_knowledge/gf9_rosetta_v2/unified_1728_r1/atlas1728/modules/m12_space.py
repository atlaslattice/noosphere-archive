"""M12: finite authentic bit-level checksum plus synthetic GF9 physics referent."""
from ..shared import synthetic_plate_frequency,CHAPTER_OPS,strict_wire,read_wire
MODULE='M12_GF9_TRANSPORT'
def run(ctx):
    ref=synthetic_plate_frequency(ctx['module_index'],ctx['chapter_index'])
    obj={'hsn':ctx['coordinate'],'op':CHAPTER_OPS[ctx['chapter_index']],
         'ratio':ref['frequency_ratio'],'scope':'SIMULATION_ONLY','source_digest':ctx['source_sha'][:12]}
    packet=strict_wire(obj)
    if read_wire(packet)!=obj:raise ValueError('GF9_PACKET_PARITY')
    return {'module':MODULE,'pass':True,'bytes':len(packet),'checksum':'CRC32_DETECTS_ERRORS_NOT_AUTH',
            'meaning_understood':False,'packet_verified':True}
