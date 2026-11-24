"""GF8 offline measurement-comparison contract (candidate, no lab attestation).

Observed geometry must be explicitly registered and binarized by a trusted
laboratory pipeline. This module compares nodal masks and frequency only; it
cannot verify instrument calibration, provenance of the image, registration,
actual source authorization or the correctness of the segmentation.
"""
from __future__ import annotations
import math
import re
from .gf8 import Plate, mode_hz, gfpayload_hash


def _check_bitmap(mask, name):
    if type(mask)!=list or not 17<=len(mask)<=129 or any(type(row)!=str or len(row)!=len(mask)
        or any(c not in '01' for c in row) for row in mask):
        raise ValueError(name+'_INVALID')
    if not any('1' in row for row in mask):raise ValueError(name+'_NO_NODES')


def compare_nodal_masks(predicted:list[str],observed:list[str])->dict:
    """IoU and directed Chamfer distance in *pixel units*, not a lab calibration."""
    _check_bitmap(predicted,'PREDICTION');_check_bitmap(observed,'OBSERVATION')
    if len(predicted)!=len(observed):raise ValueError('NO_COMMON_REGISTERED_GRID')
    a={(x,y) for y,row in enumerate(predicted) for x,c in enumerate(row) if c=='1'}
    b={(x,y) for y,row in enumerate(observed) for x,c in enumerate(row) if c=='1'}
    intersect=len(a&b);union=len(a|b)
    iou=intersect/union
    # Distance on a grid: shortest Euclidean pixel distance to the other nodal set.
    # Bounded to 129x129 and run only against deliberately small, registered images.
    def directed(src,dst):
        return sum(math.sqrt(min((x-u)**2+(y-v)**2 for u,v in dst)) for x,y in src)/len(src)
    # Avoid huge O(N^2) sets by requiring a sensible sparse contour.
    if max(len(a),len(b))>3000:raise ValueError('SEGMENTATION_TOO_DENSE_OR_NOT_SKELETONIZED')
    chamfer=0.5*(directed(a,b)+directed(b,a))
    return {'schema':'atlas.gf8.mask-comparison/v1',
            'intersection_over_union':round(iou,8),
            'symmetric_chamfer_pixels':round(chamfer,8),
            'observed_node_pixels':len(b),'predicted_node_pixels':len(a),
            'registration':'CALLER_REPORTED_NOT_ATTESTED',
            'validated_experiment':False,'model_weights_changed':False}


def calibration_candidate(plate:Plate,m:int,n:int,measured_frequency_hz:float,
                          predicted_bitmap:list[str],observed_bitmap:list[str],
                          *,raw_capture_sha256:str,source_ref:str,registration_method:str)->dict:
    if type(measured_frequency_hz) not in (int,float) or not math.isfinite(measured_frequency_hz) or not 0.1<=measured_frequency_hz<=1e6:
        raise ValueError('MEASURED_FREQUENCY_INVALID')
    if not re.fullmatch('[0-9a-f]{64}',raw_capture_sha256 or '') or not isinstance(source_ref,str) or not source_ref.startswith(('https://','urn:atlas:synthetic:')):
        raise ValueError('MEASUREMENT_PROVENANCE_INVALID')
    if registration_method not in ('FIDUCIAL_AFFINE','METROLOGY_REGISTERED_PHYSICAL_GRID'):
        raise ValueError('REGISTRATION_NOT_DECLARED')
    predicted=mode_hz(plate,m,n)
    mask_result=compare_nodal_masks(predicted_bitmap,observed_bitmap)
    info={'schema':'atlas.gf8.calibration-candidate/v1','source_model':'KIRCHHOFF_LOVE_SSSS',
          'predicted_frequency_hz':predicted,'user_reported_measured_frequency_hz':measured_frequency_hz,
          'relative_frequency_error':abs(predicted-measured_frequency_hz)/measured_frequency_hz,
          'nodal_metrics':mask_result,'material_spec':plate.metadata(),
          'mode':(m,n),'raw_capture_sha256':raw_capture_sha256,'source_ref':source_ref,
          'registration_method':registration_method,
          'status':'SOURCE_PROPOSED_MEASUREMENT_NOT_INDEPENDENTLY_CERTIFIED',
          'instrument_verified':False,'image_read_or_registered_by_this_module':False,
          'expert_accepted':False,'calibrated':False,'canon_effect':'NONE'}
    info['receipt_sha256']=gfpayload_hash(info)
    return info
