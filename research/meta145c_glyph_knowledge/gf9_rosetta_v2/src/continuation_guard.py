"""Review-only GF9 R2 adjunct. Does not alter legacy ledger event semantics.
Finite synthetic checks; no I/O other than explicitly passed local receipt paths.
No calibrated physical measurement, authorization or translation is asserted.
"""
from fractions import Fraction
from itertools import product
from pathlib import Path
import hashlib, json, math, zlib
from . import protocol as wire
from . import evolution as evo
from . import compiler as glyph
from . import gf9_reference as ref
from .linguistics import script_record, PROFILES, registry_digest


def require(ok, label):
    if not ok:
        raise ValueError(label)


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_replay(state, paths, *, expected_tip, expected_count):
    """Bind to independently supplied tip/count and replay recorded decisions.
    Does not re-simulate the archived noisy frames or authenticate the signer.
    """
    require(type(expected_count) is int and expected_count >= 0, 'COUNT_TYPE')
    require(state['schema'] == evo.SCHEMA and state['head'] == expected_tip
            and state['next_index'] == expected_count, 'EXTERNAL_ANCHOR_MISMATCH')
    require(state['live_service_connected'] is False, 'HOST_AUTHORITY')
    check = evo.verify_log(state, paths)
    require(check['status'] == 'CHAIN_AND_POLICY_REPLAY_PASS', 'CHAIN_REPLAY')
    counts = dict.fromkeys(('evaluated','accepted','rejected','false_acceptances','postflight_holds'), 0)
    segments = []
    for path in paths:
        before = counts.copy()
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            d = json.loads(line); e = d['event']; i = e['trial']-1
            m, c = i % 144, (i // 144) % 12
            p, q = wire.Policy(**e['old']), wire.Policy(**e['proposed'])
            require(type(e['accepted']) is bool and q == evo.mutate(p,i), 'MUTATION_REPLAY')
            require(e['chapter'] == c+1 and e['trial_seed_sha256'] == evo.sha(list(evo.noise_seeds(m,c,i,3))), 'SEED_REPLAY')
            for result, policy in ((e['old_result'],p),(e['candidate_result'],q)):
                require(all(type(result[k]) is int and result[k]>=0 for k in ('passes','rejected','postflight_holds','false_accepted','frames','wire_bytes')), 'COUNTER_TYPE')
                require(result['frames']==3 and result['passes']+result['rejected']+result['postflight_holds']==3, 'FRAME_CLOSURE')
                require(result['repetition']==policy.repetition and result['quantization']==policy.decimals and result['rate']==wire.channel_rate(m,c), 'POLICY_METADATA')
                score = round(result['passes']/3 - .029*(policy.repetition-1) - .001*max(0,policy.decimals-4),9)
                require(result['score']==score, 'SCORE_REPLAY')
                counts['false_acceptances']+=result['false_accepted']
                counts['postflight_holds']+=result['postflight_holds']
            yes, reason = evo.acceptance(e['old_result'],e['candidate_result'],p,q)
            require(e['accepted']==yes and e['disposition']==reason and e['new_policy']==(e['proposed'] if yes else e['old']), 'DECISION_REPLAY')
            counts['evaluated']+=1; counts['accepted' if yes else 'rejected']+=1
        segments.append({'file':Path(path).name,'sha256':digest_file(path),'counts':{k:counts[k]-before[k] for k in counts}})
    require(counts==state['counts'], 'COUNTER_REPLAY')
    return {'status':'ANCHOR_AND_RECORDED_DECISION_REPLAY_PASS','counts':counts,'head':expected_tip,'segments':segments,'authenticated_signature':False,'historical_frames_resimulated':False}


def recover_bit_majority(frame, policy):
    """Candidate repetition decoder: majority per bit, followed by original CRC.
    Holds on malformed canonical JSON, including non-object or non-finite values.
    CRC is error detection only, never authentication.
    """
    r = policy.repetition
    if type(frame) is not bytes or len(frame)%r or len(frame)>16384:
        return None,'HOLD_BOUNDS'
    if r==1:
        decoded=frame
    elif r==3:
        decoded=bytes((a&b)|(a&c)|(b&c) for a,b,c in zip(frame[::3],frame[1::3],frame[2::3]))
    else:
        decoded=bytes(sum((1<<k) for k in range(8) if sum(bool(b&(1<<k)) for b in frame[i:i+r])>r//2) for i in range(0,len(frame),r))
    try:
        return wire.recover(decoded,wire.Policy(1,policy.decimals))
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None,'HOLD_INVALID_CANONICAL_OBJECT'


def lesson_checks(m):
    """Twelve original synthetic fixtures, separate from raw codec training.
    A passed local calculation is not recipient understanding or permission.
    """
    require(type(m) is int and 0<=m<144,'SPHERE_RANGE')
    p=ref.reference_packet(); body=p['resonator']; plate=body['properties']; modes=wire.physical_problem(m,7)['mode']
    results=[]
    # 1: hypothetical endpoint stop; HOLD must not authorize action.
    allowed=False
    for token in ('OPT_IN','STOP','PAYLOAD'):
        if token=='OPT_IN': allowed=True
        elif token=='STOP': allowed=False
        else: require(not allowed,'STOP_FENCE')
    require(wire.make_message(m,0,wire.Policy(3,6))['status']=='HOLD','HANDSHAKE_HOLD'); results.append('STOP_FENCE')
    # 2: independent cardinality representation.
    require(all(len(set(range(n)))==len(json.loads(json.dumps([1]*n)))==n for n in (1,2,3,5,7)),'COUNT');results.append('COUNT')
    # 3: exact scale-invariant ratios.
    s=m+2; require(Fraction(2*s,s)==2 and Fraction(3*s,2*s)==Fraction(3,2),'RATIO');results.append('RATIO')
    # 4: inverse of right-handed quarter-turn (integer coordinates).
    vertices=list(product((0,1),repeat=3)); rot=lambda v:(-v[1],v[0],v[2]);inv=lambda v:(v[1],-v[0],v[2]);require(all(inv(rot(v))==v for v in vertices),'ROTATION');results.append('ROTATION')
    # 5: normalized reciprocal period/frequency with explicit seconds.
    period=Fraction(m+1,1000); frequency=1/period;require(period*frequency==1,'CLOCK');results.append('CLOCK')
    # 6: element identity separate from the plate.
    require(p['sample']['atomic_number']==14 and p['sample']['symbol']=='Si' and p['sample']['mechanically_coupled_to_plate'] is False,'ELEMENT');results.append('ELEMENT')
    # 7: original illustrative cubic lattice, explicit units and occupancy.
    lattice={'vectors_nm':[[1,0,0],[0,1,0],[0,0,1]],'occupancy_fraction':1,'evidence':'ILLUSTRATIVE_NOT_MEASURED'};require(json.loads(json.dumps(lattice))==lattice,'LATTICE');results.append('LATTICE')
    # 8: independent algebraic form of the thin-plate model.
    a,b=plate['width_m'],plate['height_m'];h=plate['thickness_m'];E=plate['youngs_modulus_pa'];rho=plate['density_kg_m3'];nu=plate['poisson_ratio'];x,y=modes
    expected=math.pi*h/2*math.sqrt(E/(12*rho*(1-nu*nu)))*(x*x/(a*a)+y*y/(b*b));require(math.isclose(expected,ref.frequency_hz(plate,modes),rel_tol=1e-12),'RESONANCE');results.append('RESONANCE')
    # 9: unsupported boundary explicitly rejected.
    try: ref.frequency_hz({**plate,'boundary':'FREE_EDGES'},modes)
    except ValueError as exc: require(str(exc)=='UNSUPPORTED_BOUNDARY','BOUNDARY_REASON')
    else: raise ValueError('BOUNDARY_NOT_HELD')
    results.append('BOUNDARY_HOLD')
    # 10: factor two, all other parameters unchanged.
    require(math.isclose(ref.frequency_hz({**plate,'thickness_m':2*h},modes)/expected,2,rel_tol=1e-12),'THICKNESS');results.append('THICKNESS_RATIO')
    # 11: explicit sonification metadata only.
    son=glyph.sonify_metadata(m,10);require(math.isclose(son['rendered_hz']/son['sonification_scale'],son['input_hz'],rel_tol=1e-8) and son['no_audio_generated'],'SONIFY');results.append('SONIFY')
    # 12: falsify a competing square-law hypothesis on held-out thickness factors.
    factors=(1.125,1.375,1.625); require(all(math.isclose(ref.frequency_hz({**plate,'thickness_m':h*f},modes)/expected,f,rel_tol=1e-12) and not math.isclose(f,f*f,rel_tol=1e-8) for f in factors),'HYPOTHESIS');results.append('PROVISIONAL_MODEL_ONLY')
    # Every chapter must preserve numeric, source, script and original 3D glyph boundaries.
    for c in range(12):
        msg=wire.make_message(m,c,wire.Policy(3,6));require(wire.valid_message(msg,m,c),'NUMERICAL_GATE')
        g=glyph.physical_3d_glyph(m,c,9); bridge=glyph.bridge_equivalence(g,glyph.serialized_earth(g),glyph.serialized_imperial_fiction(g))
        require(bridge['mathematics_reproduced'] and bridge['intention_understood'] is False and bridge['actual_alien_response'] is False,'GLYPH_BOUNDARY')
        meta=script_record(PROFILES[(m+c)%len(PROFILES)].code);require(meta['translation'] is None and meta['not_a_gf9_operator'] is True,'SCRIPT_BOUNDARY')
    return results


def heldout_decoder_check():
    """Fixed threefold, six-decimal policy: identical frames for both decoders.
    One held-out seed per Sphere/chapter. Never used to select raw policies.
    """
    p=wire.Policy(3,6); old=new=old_bad=new_bad=byte_count=0; improvements=regressions=0
    for m in range(144):
        for c in range(12):
            msg=wire.make_message(m,c,p);raw=wire.encode(msg,p)
            seed=int.from_bytes(hashlib.sha256(f'GF9-R2-BIT-MAJORITY-HOLDOUT-01:{m}:{c}'.encode()).digest()[:8],'big')
            frame=wire.physical_noise(raw,p,seed,wire.channel_rate(m,c));byte_count+=len(frame)
            a,_=wire.recover(frame,p);b,_=recover_bit_majority(frame,p)
            ao=a==msg and wire.valid_message(a,m,c);bo=b==msg and wire.valid_message(b,m,c)
            old+=ao;new+=bo;old_bad+=a is not None and a!=msg;new_bad+=b is not None and b!=msg
            improvements+=bo and not ao;regressions+=ao and not bo
    return {'frames_each':1728,'bytes_each':byte_count,'legacy_exact':old,'candidate_exact':new,'legacy_wrong_object':old_bad,'candidate_wrong_object':new_bad,'paired_improvements':improvements,'paired_regressions':regressions,'namespace':'GF9-R2-BIT-MAJORITY-HOLDOUT-01','synthetic_only':True}
