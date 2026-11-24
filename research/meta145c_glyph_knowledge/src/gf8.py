"""GF8: material/geometry/boundary-aware analytic Chladni modes and driven fields.

This is a bounded, source-only *model* of a simply-supported rectangular,
flat, isotropic, thin Kirchhoff–Love plate. It is NOT a free-edge Chladni
experiment, a GF7 physical calibration, an HSN equivalence, or model training.

A pattern can only be interpreted together with its plate specification,
frequency, excitation position, damping, modal truncation, uncertainty and
calibration source. No sand-grain mechanics or nonlinear coupling is solved.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
from .glyph import GF7_BANDS, GF7_MATERIALS, GF7_MODES, gf7_parts

SOURCE_REFERENCES=(
    'https://pmc.ncbi.nlm.nih.gov/articles/PMC6812332/',
    'https://sandboxphysics.com/labs/chladni-plate/',
    'https://sinestools.univie.ac.at/chladniplates.htm',
)

# Public-source nominal engineering inputs; values are illustrative, not measurements
# of any physical Atlas/GF7 object. Every card declares assumption status.
MATERIALS={
    'aluminum': (70e9, 2700.0, 0.33),
    'steel': (200e9, 7850.0, 0.30),
    'borosilicate': (64e9, 2230.0, 0.20),
}
MODEL='KIRCHHOFF_LOVE_SSSS_RECTANGLE_LINEAR_ISOTROPIC'


def _finite(x,lo,hi)->bool:
    return type(x) in (int,float) and math.isfinite(x) and lo <= x <= hi


@dataclass(frozen=True)
class Plate:
    material:str='steel'
    width_m:float=0.3
    height_m:float=0.3
    thickness_m:float=0.001
    damping_ratio:float=0.012
    boundary:str='SIMPLY_SUPPORTED_ALL_EDGES'

    def validate(self)->None:
        if self.material not in MATERIALS: raise ValueError('UNSUPPORTED_MATERIAL')
        if self.boundary!='SIMPLY_SUPPORTED_ALL_EDGES':raise ValueError('UNSUPPORTED_BOUNDARY_MODEL')
        if not (_finite(self.width_m,0.0001,30) and _finite(self.height_m,0.0001,30)
                and _finite(self.thickness_m,0.000005,0.25)
                and _finite(self.damping_ratio,0.00001,0.25)):
            raise ValueError('PLATE_PARAMETER_INVALID')

    def metadata(self)->dict:
        self.validate()
        e,rho,nu=MATERIALS[self.material]
        return {'material':self.material,'youngs_modulus_pa':e,'density_kg_m3':rho,
                'poisson_ratio':nu,'width_m':self.width_m,'height_m':self.height_m,
                'thickness_m':self.thickness_m,'damping_ratio':self.damping_ratio,
                'boundary':self.boundary,'property_source':'NOMINAL_ASSUMED_NOT_CERTIFIED',
                'model':MODEL}


def plate_rigidity(p:Plate)->float:
    p.validate()
    E,_,nu=MATERIALS[p.material]
    return E*p.thickness_m**3/(12*(1-nu**2))


def mode_hz(p:Plate,m:int,n:int)->float:
    """Plate angular eigenfrequency ω_mn=π² sqrt(D/(ρ h))(m²/a²+n²/b²)."""
    p.validate()
    if type(m)!=int or type(n)!=int or not (1<=m<=24 and 1<=n<=24):
        raise ValueError('MODE_OUT_OF_BOUNDS')
    _,rho,_=MATERIALS[p.material]
    return math.pi/2*math.sqrt(plate_rigidity(p)/(rho*p.thickness_m)) * (
        (m/p.width_m)**2+(n/p.height_m)**2)


def phi(m:int,n:int,x_norm:float,y_norm:float)->float:
    if type(m)!=int or type(n)!=int or m<1 or n<1:raise ValueError('BAD_MODE')
    if not (_finite(x_norm,0,1) and _finite(y_norm,0,1)):
        raise ValueError('POSITION_OUT_OF_RANGE')
    return math.sin(m*math.pi*x_norm)*math.sin(n*math.pi*y_norm)


def validity(p:Plate,m:int,n:int)->dict:
    """Conservative, declared thinness checks: screening, not a certificate."""
    p.validate()
    if type(m)!=int or type(n)!=int or not (1<=m<=24 and 1<=n<=24):
        raise ValueError('MODE_OUT_OF_BOUNDS')
    k=math.pi*math.hypot(m/p.width_m,n/p.height_m)
    wavelength=2*math.pi/k
    aspect_thick=p.thickness_m/min(p.width_m,p.height_m)
    wavelength_thick=p.thickness_m/wavelength
    flags=[]
    if aspect_thick>0.03:flags.append('PLATE_TOO_THICK_FOR_GEOMETRY')
    if wavelength_thick>0.03:flags.append('WAVELENGTH_TOO_SHORT_FOR_THIN_PLATE_MODEL')
    # Engineering range of a bench-top reference plate; NOT a universal physics law.
    if not (0.03<=p.width_m<=2 and 0.03<=p.height_m<=2):
        flags.append('OUTSIDE_DECLARED_BENCH_GEOMETRY')
    return {'status':'SCREENING_MODEL_IN_ENVELOPE' if not flags else 'HOLD_MODEL_ENVELOPE',
            'reasons':flags,'bending_wavelength_m':wavelength,
            'thickness_over_min_edge':aspect_thick,
            'thickness_over_wavelength':wavelength_thick,
            'empirically_validated':False}


def resonance_table(p:Plate,max_m:int=9,max_n:int=9,drive_xy=(0.31,0.43))->list[dict]:
    p.validate()
    if type(max_m)!=int or type(max_n)!=int or not (1<=max_m<=16 and 1<=max_n<=16):
        raise ValueError('MODE_BASIS_INVALID')
    x,y=drive_xy
    if not (_finite(x,0,1) and _finite(y,0,1)):raise ValueError('DRIVE_POSITION_INVALID')
    return sorted([{'m':m,'n':n,'frequency_hz':mode_hz(p,m,n),
            'drive_coupling':phi(m,n,x,y),
            'validity':validity(p,m,n)['status']}
            for m in range(1,max_m+1) for n in range(1,max_n+1)],
            key=lambda q:(q['frequency_hz'],q['m'],q['n']))


def reference_for_gf7(address:str,thickness_m:float=0.002)->dict:
    """Size an illustrative plate to resonate *at* the GF7 band center.

    Inverse design is not a measured mapping; impossible/unsupported sizes HOLD.
    The GF7 address stays in its OWN namespace, not an Ariadne HSN mapping.
    """
    b,m,c=gf7_parts(address)
    lo,hi=GF7_BANDS[b-1];target=math.sqrt(lo*hi)
    mode=GF7_MODES[m-1]
    material,ratio=GF7_MATERIALS[c-1]
    if not _finite(thickness_m,0.000005,0.1):raise ValueError('BAD_THICKNESS')
    temp=Plate(material=material,width_m=1.,height_m=float(ratio),thickness_m=thickness_m)
    width=math.sqrt(mode_hz(temp,*mode)/target)
    spec=Plate(material=material,width_m=width,height_m=width*ratio,thickness_m=thickness_m)
    # Inverse sizing may produce a plate far outside the supported geometric model.
    # Keep its *screening* result instead of crashing or inventing a physical glyph.
    if width>30 or width*ratio>30 or width<0.0001 or width*ratio<0.0001:
        v={'status':'HOLD_MODEL_ENVELOPE','reasons':['OUTSIDE_MODEL_VALIDATION_BOUNDS'],
           'empirically_validated':False}
    else:
        v=validity(spec,*mode)
    predicted=mode_hz(temp,*mode)/width**2
    return {'source_coordinate':address,'frequency_band_hz':[lo,hi],'target_frequency_hz':target,
           'mode':list(mode),'aspect_b_over_a':ratio,'material':material,
           'required_width_m':width,'required_height_m':width*ratio,
           'thickness_m':thickness_m,'analytic_frequency_hz':predicted,
           'relative_design_residual':abs(predicted-target)/target,
           'model_validity':v,'new_glyph_not_yet_observed':True,
           'not_atlas_semantic_mapping':True,'boundary':'SIMPLY_SUPPORTED_ALL_EDGES',
           'status':'INVERSE_DESIGN_SCREENING_NOT_PHYSICAL_MEASUREMENT'}


def nodal_mode_glyph(p:Plate,m:int,n:int,grid:int=49,threshold:float=0.06)->dict:
    """Mode eigenfunction nodal mask; does NOT simulate sand motion."""
    if type(grid)!=int or not 17<=grid<=129 or not _finite(threshold,0.01,0.25):
        raise ValueError('GLYPH_RESOLUTION_INVALID')
    frequency=mode_hz(p,m,n)
    rows=[]
    for j in range(grid):
        y=j/(grid-1)
        rows.append(''.join('1' if abs(phi(m,n,i/(grid-1),y))<=threshold else '0'
                            for i in range(grid)))
    return {'kind':'ANALYTIC_EIGENMODE_NODAL_SET_NOT_SAND_SIMULATION',
            'frequency_hz':frequency,'grid':grid,'bitmap':rows,
            'threshold_normalized':threshold,'model_validity':validity(p,m,n),
            'source_model':MODEL,'source_references':list(SOURCE_REFERENCES),
            'physical_measurement':False}


def driven_glyph(p:Plate,frequency_hz:float,drive_xy=(0.31,0.43),
                 max_mode:int=8,grid:int=49,force_newton:float=1.0)->dict:
    """Linear harmonic forcing with finite sine modes; nodal set is proxy only.

    Modal response Q_mn = F phi_drive / [M(ω_mn²-Ω² + 2i ζ ω_mn Ω)]
    where M=ρ h a b/4 for these unnormalized sine eigenfunctions.
    """
    p.validate()
    if not _finite(frequency_hz,0.1,1e6) or not _finite(force_newton,1e-7,100) or type(max_mode)!=int or not 2<=max_mode<=12 or type(grid)!=int or not 17<=grid<=129:
        raise ValueError('DRIVE_PARAMETERS_INVALID')
    if len(drive_xy)!=2 or not all(_finite(z,0,1) for z in drive_xy):raise ValueError('DRIVE_POSITION_INVALID')
    table=resonance_table(p,max_mode,max_mode,drive_xy)
    nearest=min(table,key=lambda r:abs(r['frequency_hz']-frequency_hz))
    usable=[r for r in table if abs(r['frequency_hz']/frequency_hz-1)<=max(0.035,3*p.damping_ratio)
            and abs(r['drive_coupling'])>=0.04 and r['validity']=='SCREENING_MODEL_IN_ENVELOPE']
    if not usable:
        return {'status':'HOLD_NO_EXCITABLE_RESONANCE_IN_TRUNCATED_MODEL',
                'nearest_mode':nearest,'frequency_hz':frequency_hz,
                'mode_basis_max':max_mode,'field':None,'physical_measurement':False,
                'reason':'Off resonance, nodal drive position, invalid thin-plate regime, or insufficient basis'}
    _,rho,_=MATERIALS[p.material]
    mass=rho*p.thickness_m*p.width_m*p.height_m/4
    omega=2*math.pi*frequency_hz
    xs=[[math.sin(math.pi*m*i/(grid-1)) for i in range(grid)] for m in range(1,max_mode+1)]
    ys=[[math.sin(math.pi*n*j/(grid-1)) for j in range(grid)] for n in range(1,max_mode+1)]
    field=[[0j]*grid for _ in range(grid)]
    for r in table:
        m,n=r['m'],r['n'];wn=2*math.pi*r['frequency_hz']
        amp=force_newton*r['drive_coupling']/(mass*(wn*wn-omega*omega+2j*p.damping_ratio*wn*omega))
        if abs(amp)<1e-20:continue
        xrow=xs[m-1];yrow=ys[n-1]
        for j in range(grid):
            scale=amp*yrow[j]
            target=field[j]
            for i in range(grid):target[i]+=scale*xrow[i]
    maximum=max(abs(z) for row in field for z in row)
    if maximum==0:raise ValueError('ZERO_DRIVEN_FIELD')
    normalized=[[round(abs(z)/maximum,6) for z in row] for row in field]
    nodal=[''.join('1' if v<=0.06 else '0' for v in row) for row in normalized]
    maxvalid=min((validity(p,r['m'],r['n']) for r in usable),key=lambda v:len(v['reasons']))
    return {'status':'ANALYTIC_DRIVEN_FIELD_NEAR_RESONANCE',
            'frequency_hz':frequency_hz,'drive_xy':list(drive_xy),'force_newton':force_newton,
            'grid':grid,'amplitude_proxy':normalized,'nodal_proxy_bitmap':nodal,
            'nearby_excitable_modes':usable[:16],
            'max_mode':max_mode,'nearest_mode':nearest,'model_validity':maxvalid,
            'peak_complex_displacement_m_per_unit_forcing':maximum,
            'model':MODEL,'model_scope':'LINEAR_STEADY_STATE_NOT_GRAIN_TRANSPORT',
            'physical_measurement':False,'science_grade':'ANALYTIC_UNCALIBRATED'}


def measurement_comparison(p:Plate,m:int,n:int,measured_hz:float,source_ref:str,
                           measurement_digest:str)->dict:
    if not _finite(measured_hz,0.1,1e6) or not isinstance(source_ref,str) or not source_ref.startswith(('https://','urn:atlas:')) or not isinstance(measurement_digest,str) or len(measurement_digest)!=64 or any(c not in '0123456789abcdef' for c in measurement_digest):
        raise ValueError('UNPROVEN_MEASUREMENT_SOURCE')
    predicted=mode_hz(p,m,n)
    residual=measured_hz-predicted
    return {'status':'MEASUREMENT_USER_REPORTED_NOT_INDEPENDENTLY_VERIFIED',
            'source_ref':source_ref,'source_digest':measurement_digest,'measured_hz':measured_hz,
            'predicted_hz':predicted,'signed_residual_hz':residual,
            'relative_abs_error':abs(residual)/measured_hz,'source_model':MODEL,
            'observed_raw_data_read':False,'calibration_done':False,
            'semantic_or_canon_effect':'NONE'}


def gfpayload_hash(payload:dict)->str:
    if type(payload)!=dict:raise ValueError('PAYLOAD_INVALID')
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))
    return hashlib.sha256(raw.encode()).hexdigest()
