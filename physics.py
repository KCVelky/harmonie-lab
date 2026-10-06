"""Modèle réduit énergétique, unités SI. Aucun accès réseau."""
from dataclasses import dataclass, asdict, replace
from functools import lru_cache
import io
import re
import numpy as np
from numpy.polynomial import Polynomial, Legendre
from numpy.polynomial.legendre import leggauss
from scipy.linalg import eigh, solve, block_diag
from scipy.optimize import brentq
from scipy.io.wavfile import write

@dataclass(frozen=True)
class Plate:
    H: float = .610
    W: float = .305
    h: float = .002
    rho: float = 650.
    Es: float = 10e9
    Eu: float = 10e9
    G: float = 10e9/2.6
    nu: float = .30
    angle: float = 0.
    boundary: str = 'Appuis simples'
    rotation: float = 10.  # raideur de rotation par longueur de bord, N
    order: int = 6
    bridge_s: float = .122
    bridge_mass: float = .010
    damping: float = .012

@dataclass(frozen=True)
class Support:
    """Traverse en bois collée derrière la jonction centrale des panneaux."""
    enabled: bool = False
    joint_u: float = .5
    width: float = .0381
    depth: float = .0381
    rho: float = 500.
    E: float = 10e9

@dataclass(frozen=True)
class String:
    active: bool = True
    L: float = 1.
    d: float = .000762
    T: float = 16.
    rho: float = 7861.
    E: float = 206.843e9
    beta: float = .28
    u: float = .5
    coupling: float = 500.
    damping: float = .004
    angle: float = 3.
    drive: float = 61.
    force: float = .01  # force crête étalonnée au jeu de référence 3 mm
    p1: float = .12
    p2: float = .20
    g1: float = .003
    g2: float = .003
    gain2: float = 1.
    phase: float = 0.
    phase2: float = 0.

def defaults(n=5):
    return [String(L=float(L),u=(i+1)/(n+1)) for i,L in enumerate(np.linspace(.8,1.2,n))]

def validate(p, strings, support=None):
    vals=list(asdict(p).values())
    if any(not np.isfinite(v) for v in vals if isinstance(v,(int,float))):
        raise ValueError('Les paramètres doivent être finis.')
    if min(p.H,p.W,p.h,p.rho,p.Es,p.Eu,p.G)<=0 or not 0<=p.nu<.49:
        raise ValueError('Dimensions, rigidités et masse volumique doivent être positives.')
    if p.nu**2*p.Eu/p.Es>=.98:
        raise ValueError('Matériau instable : nu_su² × Eu/Es doit être inférieur à 1.')
    if not 0 < p.bridge_s < p.H or p.bridge_mass<0 or p.rotation<0:
        raise ValueError('Chevalet hors plaque, masse ou raideur négative.')
    if not 3<=p.order<=14 or not .0001<=p.damping<=.3:
        raise ValueError('Ordre ou amortissement hors limites.')
    if support is not None:
        vals=list(asdict(support).values())
        if any(not np.isfinite(v) for v in vals if isinstance(v,(int,float))):
            raise ValueError('Les paramètres de la structure doivent être finis.')
        if not 0<support.joint_u<1 or min(support.width,support.depth,support.rho,support.E)<=0:
            raise ValueError('Position de jonction ou propriétés de la traverse invalides.')
    for s in strings:
        if any(not np.isfinite(v) for v in asdict(s).values()):
            raise ValueError('Une cellule de corde est vide ou non numérique.')
        if min(s.L,s.d,s.T,s.rho,s.E,s.g1,s.g2)<=0 or s.coupling<0 or s.force<0:
            raise ValueError('Longueur, diamètre, tension, E, densité et jeux doivent être positifs.')
        if not all(0<x<1 for x in (s.beta,s.u,s.p1,s.p2)):
            raise ValueError('Les positions relatives doivent être strictement entre 0 et 1.')
        if not .0001<=s.damping<=.3 or not 0<=s.angle<=30 or not 1<=s.drive<=12000:
            raise ValueError('Amortissement, angle ou fréquence de corde hors limites.')

@lru_cache(maxsize=32)
def poly_basis(order):
    x=Polynomial([0,1]); envelope=x*x*(1-x)*(1-x)
    return tuple(envelope*Legendre.basis(i).convert(kind=Polynomial)(2*x-1) for i in range(order))

def basis1(x,L,n,clamped,deriv=0):
    t=np.asarray(x)/L
    if clamped:
        return np.stack([q.deriv(deriv)(t)/L**deriv for q in poly_basis(n)],axis=-1)
    k=np.arange(1,n+1)*np.pi/L
    return np.sin(t[...,None]*np.arange(1,n+1)*np.pi+deriv*np.pi/2)*k**deriv

def basis(p,s,u,ds=0,du=0):
    s,u=np.broadcast_arrays(s,u)
    a=basis1(s,p.H,p.order,p.boundary=='Encastrement',ds)
    b=basis1(u,p.W,p.order,p.boundary=='Encastrement',du)
    return (a[..., :, None]*b[...,None,:]).reshape(s.shape+(p.order**2,))

def quadrature(p):
    x,w=leggauss(max(28,4*p.order))
    s,u=np.meshgrid((x+1)*p.H/2,(x+1)*p.W/2,indexing='ij')
    wt=np.outer(w,w).ravel()*p.H*p.W/4
    return s.ravel(),u.ravel(),wt

def rigidity(p):
    nu_us=p.nu*p.Eu/p.Es
    fac=p.h**3/12/(1-p.nu*nu_us)
    D=np.array([[p.Es,p.nu*p.Eu,0],[p.nu*p.Eu,p.Eu,0],[0,0,p.G*(1-p.nu*nu_us)]])*fac
    c=np.cos(np.deg2rad(p.angle)); s=np.sin(np.deg2rad(p.angle))
    R=np.array([[c*c,s*s,c*s],[s*s,c*c,-c*s],[-2*c*s,2*c*s,c*c-s*s]])
    return R.T@D@R

def plate_matrices(p,support=None):
    validate(p,[],support)
    s,u,wt=quadrature(p)
    B=basis(p,s,u)
    curv=np.stack([basis(p,s,u,2,0),basis(p,s,u,0,2),2*basis(p,s,u,1,1)],axis=1)
    K=np.einsum('qai,ab,qbj,q->ij',curv,rigidity(p),curv,wt,optimize=True)
    M=(B.T*wt)@B*p.rho*p.h
    x,w=leggauss(max(28,4*p.order))
    bridge=basis(p,np.full_like(x,p.bridge_s),(x+1)*p.W/2)
    M+=(bridge.T*w)@bridge*p.bridge_mass/2
    if support is not None and support.enabled:
        # Poutre d'Euler-Bernoulli verticale, solidaire de la plaque sur la jonction.
        # Sa profondeur est mesurée suivant la normale à la table.
        ss=(x+1)*p.H/2
        uu=np.full_like(x,support.joint_u*p.W)
        beam=basis(p,ss,uu)
        beam_curv=basis(p,ss,uu,2,0)
        area=support.width*support.depth
        inertia=support.width*support.depth**3/12
        M+=(beam.T*w)@beam*p.H/2*support.rho*area
        K+=(beam_curv.T*w)@beam_curv*p.H/2*support.E*inertia
    if p.boundary=='Rotation élastique':
        for edge in (0.,p.H):
            edgeB=basis(p,np.full_like(x,edge),(x+1)*p.W/2,1,0)
            K+=(edgeB.T*w)@edgeB*p.W/2*p.rotation
        for edge in (0.,p.W):
            edgeB=basis(p,(x+1)*p.H/2,np.full_like(x,edge),0,1)
            K+=(edgeB.T*w)@edgeB*p.H/2*p.rotation
    return (K+K.T)/2,(M+M.T)/2

def eigensystem(K,M):
    scale=1/np.sqrt(np.diag(M))
    val,v=eigh(K*scale[:,None]*scale[None,:],M*scale[:,None]*scale[None,:])
    if np.min(val)<=0:
        raise ValueError('Matrice non positive : vérifier les paramètres et la convergence.')
    v=scale[:,None]*v
    return np.sqrt(val)/(2*np.pi),v

def string_frequencies(s,n=8):
    A=np.pi*s.d**2/4; I=np.pi*s.d**4/64; k=np.arange(1,n+1)*np.pi/s.L
    return np.sqrt((s.T*k*k+s.E*I*k**4)/(s.rho*A))/(2*np.pi)

def tension_for(s,f,harmonic=1):
    k=harmonic*np.pi/s.L; A=np.pi*s.d*s.d/4; I=np.pi*s.d**4/64
    return float((2*np.pi*f)**2*s.rho*A/k**2-s.E*I*k**2)

def harmonic_drive_settings(s,harmonic):
    """Réglage à deux aimants renforçant un harmonique de corde isolée."""
    harmonic=int(harmonic)
    if harmonic<1:
        raise ValueError('Le rang harmonique doit être supérieur ou égal à 1.')
    if harmonic==1:
        p1,p2=.25,.75
    else:
        p1=1/(2*harmonic)
        p2=1-p1
    phase2=0. if np.sin(harmonic*np.pi*p1)*np.sin(harmonic*np.pi*p2)>0 else 180.
    drive=float(string_frequencies(s,harmonic)[harmonic-1])
    return replace(s,active=True,drive=drive,p1=p1,p2=p2,gain2=1.,phase=0.,phase2=phase2)

def note_frequency(note):
    text=str(note).strip().replace('♯','#').replace('♭','b')
    french={'DO':'C','RÉ':'D','RE':'D','MI':'E','FA':'F','SOL':'G','LA':'A','SI':'B'}
    upper=text.upper()
    for name,letter in sorted(french.items(),key=lambda x:-len(x[0])):
        if upper.startswith(name):
            text=letter+text[len(name):]
            break
    match=re.fullmatch(r'([A-Ga-g])([#b]?)(-?\d+)',text)
    if not match:
        raise ValueError(f'Note inconnue : {note}. Utiliser par exemple C4, F#4 ou Sib3.')
    letter,accidental,octave=match.groups()
    semitones={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[letter.upper()]
    semitones+=1 if accidental=='#' else -1 if accidental=='b' else 0
    midi=(int(octave)+1)*12+semitones
    return float(440*2**((midi-69)/12))

def sequence_plan(strings,events,ns=8):
    """Associe chaque note à une corde et à un mode spatial d'excitation."""
    plan=[]
    for index,event in enumerate(events):
        try:
            start=float(event['start_s']); duration=float(event['duration_s'])
            velocity=float(event.get('velocity',1.))
        except (KeyError,TypeError,ValueError):
            raise ValueError(f'Ligne {index+1} : début, durée ou intensité invalide.')
        if not np.isfinite(start+duration+velocity) or start<0 or duration<=0 or not 0<=velocity<=1:
            raise ValueError(f'Ligne {index+1} : valeurs hors limites.')
        note=str(event.get('note','')).strip()
        if note.upper() in ('R','REST','SILENCE','-'):
            continue
        frequency=note_frequency(note)
        requested_string=event.get('string')
        requested_harmonic=event.get('harmonic')
        has_string=requested_string is not None and not (isinstance(requested_string,float) and np.isnan(requested_string))
        has_harmonic=requested_harmonic is not None and not (isinstance(requested_harmonic,float) and np.isnan(requested_harmonic))
        string_indexes=[int(requested_string)-1] if has_string else range(len(strings))
        harmonic_indexes=[int(requested_harmonic)] if has_harmonic else range(1,ns+1)
        candidates=[]
        for si in string_indexes:
            if not 0<=si<len(strings):
                raise ValueError(f'Ligne {index+1} : numéro de corde invalide.')
            natural=string_frequencies(strings[si],ns)
            for harmonic in harmonic_indexes:
                if not 1<=harmonic<=ns:
                    raise ValueError(f'Ligne {index+1} : harmonique hors de la résolution actuelle.')
                cents=1200*np.log2(frequency/natural[harmonic-1])
                candidates.append((abs(cents),si,harmonic,natural[harmonic-1],cents))
        _,si,harmonic,natural,cents=min(candidates,key=lambda x:x[0])
        setting=replace(harmonic_drive_settings(strings[si],harmonic),drive=frequency)
        plan.append(dict(start_s=start,duration_s=duration,start_ms=round(start*1000),
                         duration_ms=round(duration*1000),note=note,frequency_hz=frequency,
                         velocity=velocity,string=si+1,harmonic=harmonic,
                         magnet1_channel=2*si+1,magnet2_channel=2*si+2,
                         natural_frequency_hz=float(natural),detune_cents=float(cents),
                         p1=setting.p1,p2=setting.p2,phase1_deg=setting.phase,
                         phase2_deg=setting.phase2,gain1=1.,gain2=setting.gain2,
                         gap1_mm=setting.g1*1000,gap2_mm=setting.g2*1000,
                         force1_N=setting.force*velocity,
                         force2_N=setting.force*setting.gain2*velocity))
    if not plan:
        raise ValueError('La séquence ne contient aucune note à jouer.')
    return plan

def assemble(p,strings,ns=8,support=None):
    if support is None: support=Support()
    validate(p,strings,support)
    Kp,Mp=plate_matrices(p,support); fp,Vp=eigensystem(Kp,Mp)
    np_=len(Kp)
    masses=[s.rho*np.pi*s.d**2/4*s.L/2*np.ones(ns) for s in strings]
    M=block_diag(Mp,*[np.diag(m) for m in masses])
    K=block_diag(Kp,*[np.diag(m*(2*np.pi*string_frequencies(s,ns))**2) for m,s in zip(masses,strings)])
    for i,s in enumerate(strings):
        link=np.zeros(len(K)); link[:np_]=-basis(p,p.bridge_s,s.u*p.W)
        link[np_+i*ns:np_+(i+1)*ns]=np.sin(np.arange(1,ns+1)*np.pi*s.beta)
        K+=s.coupling*np.outer(link,link)
    f,V=eigensystem(K,M)
    plate_fraction=np.sum(V[:np_]*(Mp@V[:np_]),axis=0)
    zeta=p.damping*plate_fraction
    for i,(s,m) in enumerate(zip(strings,masses)):
        sl=slice(np_+i*ns,np_+(i+1)*ns)
        zeta+=s.damping*np.sum(m[:,None]*V[sl]**2,axis=0)
    return dict(p=p,support=support,strings=strings,ns=ns,np=np_,K=K,M=M,Kp=Kp,Mp=Mp,fp=fp,Vp=Vp,f=f,V=V,zeta=zeta,plate_fraction=plate_fraction)

def force_vector(model,index=None):
    vec=np.zeros(len(model['K']),dtype=complex); ns=model['ns']; n=np.arange(1,ns+1)
    for i,s in enumerate(model['strings']):
        if not s.active or (index is not None and i!=index): continue
        v=s.force*np.exp(1j*np.deg2rad(s.phase))*(np.sin(n*np.pi*s.p1)*(.003/s.g1)**2+s.gain2*np.exp(1j*np.deg2rad(s.phase2))*np.sin(n*np.pi*s.p2)*(.003/s.g2)**2)
        offset=model['np']+i*ns; vec[offset:offset+ns]=v
    return vec

def response(model,frequencies,index=None):
    f=np.atleast_1d(frequencies); om=2*np.pi*f; wn=2*np.pi*model['f']
    den=wn[:,None]**2-om[None,:]**2+2j*model['zeta'][:,None]*wn[:,None]*om[None,:]
    q=(model['V'].T@force_vector(model,index))[:,None]/den
    return model['V']@q

def static_deflection(model):
    p=model['p']; F=np.zeros(model['np']); total=0.
    for s in model['strings']:
        force=2*s.T*np.sin(np.deg2rad(s.angle)/2)
        total+=force; F+=force*basis(p,p.bridge_s,s.u*p.W)
    q=solve(model['Kp'],F,assume_a='pos')
    S,U=np.meshgrid(np.linspace(0,p.H,55),np.linspace(0,p.W,33),indexing='ij')
    return S,U,basis(p,S,U)@q,total

def target_thickness(p,target,mode=0,support=None):
    def residual(h):
        K,M=plate_matrices(replace(p,h=h),support); return eigensystem(K,M)[0][mode]-target
    low,high=.0002,.030
    if residual(low)*residual(high)>0:
        raise ValueError('Cible hors de la plage 0,2–30 mm pour ce mode et ces paramètres.')
    return brentq(residual,low,high,xtol=1e-10)

def plate_observation(model,listener=None):
    p=model['p']; obs=np.zeros(len(model['K']))
    if listener is None or listener=='Table entière':
        s,u,wt=quadrature(p)
        distance=np.sqrt((s-.57*p.H)**2+(u-.38*p.W)**2+.35**2)
        weights=wt/distance
        obs[:model['np']]=weights@basis(p,s,u)/np.sum(weights)
    else:
        obs[:model['np']]=basis(p,p.H*listener[0],p.W*listener[1])
    return obs

def synthesize(model,duration=4.,kind='Entretenu',listener=None,sr=44100):
    """Sonification de l'accélération de la plaque."""
    obs=plate_observation(model,listener)
    t=np.arange(int(duration*sr))/sr; y=np.zeros_like(t)
    if kind=='Entretenu':
        for i,s in enumerate(model['strings']):
            if s.active and s.drive<.45*sr:
                q=response(model,[s.drive],i)[:,0]
                amp=-(2*np.pi*s.drive)**2*(obs@q)
                y+=np.real(amp*np.exp(2j*np.pi*s.drive*t))
    else:
        F=np.zeros(len(model['K']))
        for i,s in enumerate(model['strings']):
            if not s.active: continue
            n=np.arange(1,model['ns']+1)
            offset=model['np']+i*model['ns']
            F[offset:offset+model['ns']]=.001*s.force*(
                np.sin(n*np.pi*s.p1)*(.003/s.g1)**2+
                s.gain2*np.sin(n*np.pi*s.p2)*(.003/s.g2)**2)
        wn=2*np.pi*model['f']; z=model['zeta']; wd=wn*np.sqrt(1-z*z)
        coeff=(obs@model['V'])*(model['V'].T@F)/wd
        for a,w,d,k in zip(coeff,wn,wd,z):
            if w/(2*np.pi)>.45*sr: continue
            decay=k*w
            y+=a*np.exp(-decay*t)*((decay**2-d*d)*np.sin(d*t)-2*decay*d*np.cos(d*t))
    fade=min(int(.025*sr),len(y)//2)
    y[:fade]*=np.linspace(0,1,fade); y[-fade:]*=np.linspace(1,0,fade)
    peak=float(np.max(np.abs(y)))
    if peak>1e-15: y=y/peak*.65
    else: y[:]=0
    buf=io.BytesIO(); write(buf,sr,(np.clip(y,-1,1)*32767).astype(np.int16))
    return buf.getvalue(),y,peak

def synthesize_sequence(model,plan,listener=None,sr=44100):
    obs=plate_observation(model,listener)
    total=max(x['start_s']+x['duration_s'] for x in plan)+.12
    y=np.zeros(int(np.ceil(total*sr)))
    for event in plan:
        start=int(round(event['start_s']*sr))
        length=max(1,int(round(event['duration_s']*sr)))
        stop=min(len(y),start+length)
        length=stop-start
        if length<=0: continue
        si=int(event['string'])-1; harmonic=int(event['harmonic'])
        setting=harmonic_drive_settings(model['strings'][si],harmonic)
        setting=replace(setting,drive=event['frequency_hz'],force=setting.force*event['velocity'])
        strings=list(model['strings']); strings[si]=setting
        event_model={**model,'strings':tuple(strings)}
        q=response(event_model,[event['frequency_hz']],si)[:,0]
        amplitude=-(2*np.pi*event['frequency_hz'])**2*(obs@q)
        t=np.arange(length)/sr
        envelope=np.ones(length)
        attack=min(max(1,int(.012*sr)),length//2)
        release=min(max(1,int(.045*sr)),length//2)
        envelope[:attack]=np.linspace(0,1,attack)
        envelope[-release:]=np.linspace(1,0,release)
        y[start:stop]+=np.real(amplitude*np.exp(2j*np.pi*event['frequency_hz']*t))*envelope
    peak=float(np.max(np.abs(y)))
    if peak>1e-15: y=y/peak*.65
    buf=io.BytesIO(); write(buf,sr,(np.clip(y,-1,1)*32767).astype(np.int16))
    return buf.getvalue(),y,peak

def config_dict(p,strings,geometry,ns,support=None):
    if support is None: support=Support()
    return dict(version=1,plate=asdict(p),strings=[asdict(s) for s in strings],
                geometry=geometry,string_modes=ns,support=asdict(support))
