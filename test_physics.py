from dataclasses import replace
import numpy as np
import pytest
from physics import *

def test_supported_analytic():
    p=Plate(bridge_mass=0)
    f,V=eigensystem(*plate_matrices(p))
    D=p.Es*p.h**3/(12*(1-p.nu**2))
    exact=sorted(np.pi/2*np.sqrt(D/(p.rho*p.h))*((m/p.H)**2+(n/p.W)**2)
                 for m in range(1,p.order+1) for n in range(1,p.order+1))
    np.testing.assert_allclose(f,exact,rtol=1e-10)

def test_clamped_reference_and_constraints():
    p=Plate(boundary='Encastrement',bridge_mass=0)
    f,V=eigensystem(*plate_matrices(p))
    assert abs(f[0]-99.823)<.02
    for edge in (0,p.H):
        np.testing.assert_allclose(basis(p,edge,p.W*.37),0,atol=1e-10)
        np.testing.assert_allclose(basis(p,edge,p.W*.37,1,0),0,atol=1e-10)

def test_scaling():
    p=Plate(bridge_mass=0)
    f,_=eigensystem(*plate_matrices(p))
    f2,_=eigensystem(*plate_matrices(replace(p,h=p.h*2)))
    np.testing.assert_allclose(f2,2*f,rtol=1e-10)

def test_material_rotation_isotropic_invariant():
    p=Plate()
    np.testing.assert_allclose(rigidity(p),rigidity(replace(p,angle=38)),atol=1e-12)

def test_elastic_edge_zero_and_positive():
    p=Plate(bridge_mass=0)
    f,_=eigensystem(*plate_matrices(p))
    f0,_=eigensystem(*plate_matrices(replace(p,boundary='Rotation élastique',rotation=0)))
    f1,_=eigensystem(*plate_matrices(replace(p,boundary='Rotation élastique',rotation=20)))
    np.testing.assert_allclose(f,f0)
    assert np.all(f1>f)

def test_uncoupled_spectrum_and_residual():
    p=Plate(); ss=[replace(s,coupling=0) for s in defaults(2)]
    m=assemble(p,ss)
    exact=np.sort(np.r_[m['fp'],*[string_frequencies(s,8) for s in ss]])
    np.testing.assert_allclose(m['f'],exact,rtol=1e-9)
    m=assemble(p,defaults(2))
    V=m['V']
    np.testing.assert_allclose(V.T@m['M']@V,np.eye(len(V)),atol=1e-10)
    err=np.linalg.norm(m['K']@V-m['M']@V*(2*np.pi*m['f'])**2)/np.linalg.norm(m['K']@V)
    assert err<1e-10

def test_tuning_roundtrip():
    s=String()
    for n in (1,3,8):
        f=string_frequencies(s,n)[-1]
        assert abs(tension_for(s,f,n)-s.T)<1e-10

def test_harmonic_drive_settings_reinforce_target():
    for n in range(1,9):
        s=harmonic_drive_settings(String(),n)
        shape1=np.sin(n*np.pi*s.p1)
        shape2=np.sin(n*np.pi*s.p2)*np.cos(np.deg2rad(s.phase2))
        assert shape1*shape2>0
        assert abs(s.drive-string_frequencies(s,n)[n-1])<1e-10
        assert 0<s.p1<1 and 0<s.p2<1

def test_note_frequency_and_sequence_plan():
    assert abs(note_frequency('A4')-440)<1e-12
    assert abs(note_frequency('La4')-440)<1e-12
    assert abs(note_frequency('Sib3')-note_frequency('Bb3'))<1e-12
    events=[dict(start_s=0,duration_s=.2,note='E4',velocity=.8),
            dict(start_s=.25,duration_s=.3,note='D#4',velocity=.7,string=2,harmonic=5)]
    plan=sequence_plan(defaults(),events,8)
    assert len(plan)==2 and plan[1]['string']==2 and plan[1]['harmonic']==5
    model=assemble(Plate(),defaults())
    wav,y,peak=synthesize_sequence(model,plan)
    assert wav[:4]==b'RIFF' and peak>0 and np.all(np.isfinite(y))

def test_inverse_plate():
    p=Plate(order=4)
    h=target_thickness(p,61)
    f,_=eigensystem(*plate_matrices(replace(p,h=h)))
    assert abs(f[0]-61)<1e-5

def test_static_linear_and_zero_angle():
    p=Plate()
    m=assemble(p,[String()])
    w=static_deflection(m)[2]
    w2=static_deflection(assemble(p,[String(T=32)]))[2]
    np.testing.assert_allclose(w2,w*2,atol=1e-12)
    np.testing.assert_allclose(static_deflection(assemble(p,[String(angle=0)]))[2],0)

def test_force_nodes_and_gap():
    m=assemble(Plate(),[String(p1=.5,gain2=0)])
    F=force_vector(m)[m['np']:]
    assert np.max(np.abs(F[1::2]))<1e-15
    m2=assemble(Plate(),[String(p1=.5,gain2=0,g1=.006)])
    np.testing.assert_allclose(force_vector(m2),force_vector(m)/4)

def test_audio_and_silent_uncoupled():
    for kind in ['Entretenu','Impulsion']:
        m=assemble(Plate(),[String()])
        wav,y,peak=synthesize(m,.2,kind)
        assert wav[:4]==b'RIFF' and len(y)==8820 and peak>0
        assert np.all(np.isfinite(y)) and np.max(np.abs(y))<=.65001
    m=assemble(Plate(),[String(active=False)])
    _,y,_=synthesize(m,.2)
    assert not np.any(y)

def test_bad_inputs():
    with pytest.raises(ValueError): assemble(Plate(h=-1),[])
    with pytest.raises(ValueError): assemble(Plate(),[String(p1=1.)])
    with pytest.raises(ValueError): assemble(Plate(Es=1e9,Eu=100e9),[])

def test_grid_shapes_match_points_for_clamped_and_supported():
    for bc in ['Appuis simples','Encastrement']:
        p=Plate(boundary=bc)
        S,U=np.meshgrid(np.linspace(0,p.H,7),np.linspace(0,p.W,4),indexing='ij')
        B=basis(p,S,U)
        for i,j in [(1,2),(4,1),(5,3)]:
            np.testing.assert_allclose(B[i,j],basis(p,S[i,j],U[i,j]),atol=1e-12)

def test_animation_frames_and_shapes():
    from visuals import scene
    p=Plate(boundary='Encastrement')
    m=assemble(p,defaults(2))
    geo=dict(height=1.524,frame_width=.305,depth=.305,plate_bottom=.42,technical_height=.61)
    f=scene(m,geo,m['V'][:,0],True)
    assert len(f.frames)==32 and len(f.frames[0].traces)==3
    assert np.shape(f.data[0].x)==np.shape(f.data[0].y)==np.shape(f.data[0].z)
    assert 'cdn.plot.ly' not in f.to_html(include_plotlyjs=True).split('<script src=')[-1][:100]
