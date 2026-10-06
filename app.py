"""Lancer : python -m streamlit run app.py --server.address 127.0.0.1"""
from dataclasses import asdict, replace
from pathlib import Path
import io
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from physics import (Plate,Support,String,defaults,assemble,basis,string_frequencies,tension_for,
                     response,target_thickness,synthesize,config_dict,validate,
                     harmonic_drive_settings,plate_observation,sequence_plan,
                     synthesize_sequence)
from materials import MATERIALS
from visuals import scene
from etude_sandra import reference_string,compare_positions,summarize_comparison
from analyse_t12 import audio_info,spectrum,band_power

st.set_page_config(page_title='Harmonie Lab',page_icon='🎛️',layout='wide')
st.markdown("""<style>
.stApp {background:linear-gradient(145deg,#09131d 0%,#101d2a 55%,#0d1722 100%);color:#e8f0f7}
[data-testid="stMetric"] {background:linear-gradient(135deg,#182b3c,#132333);padding:16px;border:1px solid #29445b;border-radius:16px}
[data-testid="stMetricValue"] {color:#79d7c4}
[data-testid="stExpander"] {border:1px solid #29445b;border-radius:14px;background:#101e2b}
.stButton button {border-radius:10px;font-weight:650}
.stTabs [data-baseweb="tab-list"] {gap:8px}
.stTabs [data-baseweb="tab"] {background:#142332;border-radius:10px 10px 0 0;padding:10px 18px}
.stTabs [aria-selected="true"] {background:#1c3548;color:#86e0ce}
h1,h2,h3 {letter-spacing:-.025em}
.small-note {color:#9eb0c0;font-size:.92rem;line-height:1.45}
</style>""",unsafe_allow_html=True)
st.title('Harmonie Lab')
st.caption('Accordage, excitation électromagnétique et écoute de la table d’harmonie')

GEO_DEFAULT=dict(height=1.524,frame_width=.305,depth=.305,plate_bottom=.420,
                 technical_height=.610,installation_height=0.)
PLATE_SCALES=dict(H=1000,W=1000,h=1000,Es=1e-9,Eu=1e-9,G=1e-9,bridge_s=1000,bridge_mass=1000)
SUPPORT_SCALES=dict(width=1000,depth=1000,E=1e-9)
COLS={
 'active':('Active',1),'L':('L (mm)',1000),'d':('d (mm)',1000),'T':('T (N)',1),
 'rho':('rho (kg/m³)',1),'E':('E (GPa)',1e-9),'beta':('Chevalet / L',1),
 'u':('Position / W',1),'coupling':('Couplage (N/m)',1),'damping':('zeta corde',1),
 'angle':('Angle total (°)',1),'drive':('Excitation (Hz)',1),'force':('Force aimant (N)',1),
 'p1':('Aimant 1 / L',1),'p2':('Aimant 2 / L',1),'g1':('Jeu 1 (mm)',1000),
 'g2':('Jeu 2 (mm)',1000),'gain2':('Gain aimant 2',1),'phase':('Phase 1 (°)',1),
 'phase2':('Phase 2 relative (°)',1)}

def to_rows(strings):
    return [{label:asdict(s)[k]*scale if k!='active' else bool(s.active)
             for k,(label,scale) in COLS.items()} for s in strings]
def from_rows(rows):
    return [String(**{k:bool(r[label]) if k=='active' else float(r[label])/scale
                      for k,(label,scale) in COLS.items()}) for r in rows]

def load_config(data):
    if data.get('version')!=1: raise ValueError('Version de configuration inconnue.')
    p=Plate(**data['plate']); strings=[String(**s) for s in data['strings']]
    support=Support(**data.get('support',{}))
    if not 1<=len(strings)<=12: raise ValueError('Il faut 1 à 12 cordes.')
    validate(p,strings)
    limits=dict(H=(.05,5),W=(.05,5),h=(.0002,.03),rho=(50,20000),
                Es=(1e7,1e12),Eu=(1e7,1e12),G=(1e6,5e11),nu=(0,.48),
                angle=(0,180),rotation=(0,100000),bridge_s=(.0001,4.999),
                bridge_mass=(0,2))
    for key,(lo,hi) in limits.items():
        if not lo<=getattr(p,key)<=hi:
            raise ValueError('Paramètre hors des limites de l’interface : '+key)
    if p.boundary not in ['Appuis simples','Rotation élastique','Encastrement']:
        raise ValueError('Condition limite inconnue.')
    geo={**GEO_DEFAULT,**data.get('geometry',{})}
    if any(not np.isfinite(float(v)) or not 0<=float(v)<=30 for v in geo.values()):
        raise ValueError('Géométrie invalide.')
    ns=int(data.get('string_modes',8))
    if not 2<=ns<=16: raise ValueError('Nombre de modes de corde hors limites.')
    harmonics=data.get('harmonics',[])
    if harmonics and (len(harmonics)!=len(strings) or any(int(x)!=x or not 1<=int(x)<=ns for x in harmonics)):
        raise ValueError('Sélection d’harmoniques invalide.')
    validate(p,strings,support)
    return p,strings,geo,ns,support

def queue_plate(p):
    for k,v in asdict(p).items():
        st.session_state['p_'+k]=v*PLATE_SCALES.get(k,1) if isinstance(v,float) else v

if 'rows' not in st.session_state:
    st.session_state.rows=to_rows(defaults())
    st.session_state.revision=0
    st.session_state.material=list(MATERIALS)[0]
if 'pending' in st.session_state:
    pending=st.session_state.pop('pending')
    p0,s0,g0,ns0,support0=load_config(pending)
    queue_plate(p0); st.session_state.rows=to_rows(s0)
    st.session_state.nstrings=len(s0); st.session_state.ns=ns0
    st.session_state.material='Personnalisé'
    for i,rank in enumerate(pending.get('harmonics',[])):
        st.session_state['harmonic_'+str(i)]=int(rank)
    if pending.get('harmonics'):
        st.session_state.harmonics_applied=[int(x) for x in pending['harmonics']]
    for k,v in g0.items(): st.session_state['g_'+k]=v*1000
    for k,v in asdict(support0).items():
        st.session_state['support_'+k]=v*SUPPORT_SCALES.get(k,1)
    st.session_state.project_name=pending.get('scenario','Configuration chargée')
    st.session_state.revision+=1
if 'new_h' in st.session_state:
    st.session_state.p_h=st.session_state.pop('new_h')

def material_change():
    mat=MATERIALS[st.session_state.material]
    for k in ('rho','Es','Eu','G','nu'): st.session_state['p_'+k]=mat[k]

def number(label,key,value,minv,maxv,step,help=None,format=None):
    if key not in st.session_state: st.session_state[key]=value
    options=dict(min_value=minv,max_value=maxv,step=step,key=key,help=help)
    if format is not None: options['format']=format
    return st.number_input(label,**options)

with st.sidebar:
    st.header('Table d’harmonie')
    if st.button('Charger le scénario musée · 5 × 8 pi',type='primary',width='stretch'):
        museum_plate=Plate(H=2.4384,W=1.524,h=.003175,rho=650.,Es=10e9,Eu=10e9,
                           G=10e9/2.6,nu=.30,boundary='Appuis simples',bridge_s=2.19456,
                           bridge_mass=.010,damping=.012,order=6)
        museum_geo=dict(height=2.4384,frame_width=1.524,depth=.305,plate_bottom=0.,
                        technical_height=.610,installation_height=15.)
        museum_support=Support(enabled=True,width=.0381,depth=.0381,rho=500.,E=10e9)
        data=config_dict(museum_plate,from_rows(st.session_state.rows),museum_geo,
                         int(st.session_state.get('ns',8)),museum_support)
        data['scenario']='Table du musée · hypothèses préliminaires'
        st.session_state.pending=data
        st.rerun()
    st.caption('Scénario musée : chevalet placé provisoirement à 10 % sous le bord supérieur.')
    st.selectbox('Matériau',list(MATERIALS),key='material',on_change=material_change)
    mat=MATERIALS[st.session_state.material]
    st.caption(mat['note'])
    p0=Plate()
    H=number('Hauteur libre (mm)','p_H',610.,50.,5000.,10.)/1000
    W=number('Largeur libre (mm)','p_W',305.,50.,5000.,5.)/1000
    h=number('Épaisseur (mm)','p_h',2.,.2,30.,.025,format='%.3f')/1000
    boundary=st.selectbox('Quatre bords', ['Appuis simples','Rotation élastique','Encastrement'],key='p_boundary')
    rotation=number('Raideur de rotation linéique (N)','p_rotation',10.,0.,100000.,1.,
                    'Rotation élastique : w=0 au bord, ressort distribué opposé à la pente. Ne représente pas un joint souple en translation.')
    with st.expander('Propriétés et orientation',expanded=False):
        rho=number('Masse volumique (kg/m³)','p_rho',650.,50.,20000.,10.)
        Es=number('E1 (GPa)','p_Es',10.,.01,1000.,.1)*1e9
        Eu=number('E2 (GPa)','p_Eu',10.,.01,1000.,.1)*1e9
        G=number('G12 (GPa)','p_G',10/2.6,.001,500.,.05)*1e9
        nu=number('nu12','p_nu',.30,0.,.48,.01)
        angle=number('Angle du fil / verticale (°)','p_angle',0.,0.,180.,5.)
        damping=number('Amortissement plaque ζ','p_damping',.012,.0001,.3,.001)
    with st.expander('Chevalet et résolution'):
        bs=number('Chevalet depuis bas de plaque (mm)','p_bridge_s',122.,.1,4999.,1.)/1000
        bm=number('Masse totale du chevalet (g)','p_bridge_mass',10.,0.,2000.,1.)/1000
        order=int(number('Fonctions par axe de plaque','p_order',6,3,10,1))
        ns=int(number('Modes par corde','ns',8,2,16,1))
    with st.expander('Jonction et structure en bois'):
        support_enabled=st.checkbox('Traverse sous la jonction centrale',key='support_enabled',
            help='Représente une pièce de bois verticale collée derrière la jonction des deux panneaux.')
        joint_u=number('Position de la jonction — u/W','support_joint_u',.5,.05,.95,.01)
        support_width=number('Largeur de la traverse (mm)','support_width',38.1,1.,500.,1.)/1000
        support_depth=number('Profondeur supposée (mm)','support_depth',38.1,1.,500.,1.)/1000
        support_rho=number('Masse volumique du bois (kg/m³)','support_rho',500.,100.,1500.,10.)
        support_E=number('Rigidité du bois E (GPa)','support_E',10.,.1,100.,.5)*1e9
        st.caption('La plaque reste continue : le collage est supposé parfait. La traverse ajoute sa masse et sa rigidité. Sa profondeur de 38,1 mm est une hypothèse modifiable.')
    with st.expander('Châssis : vue 3D'):
        geo={}
        labels=dict(height='Hauteur châssis',frame_width='Largeur châssis',depth='Profondeur châssis',
                    plate_bottom='Bas de plaque / châssis',technical_height='Hauteur zone technique',
                    installation_height='Élévation dans le musée')
        for k,v in GEO_DEFAULT.items():
            geo[k]=number(labels[k]+' (mm)','g_'+k,v*1000,0.,30000.,10.)/1000
    if st.button('Réinitialiser le prototype'):
        data=config_dict(Plate(),defaults(),GEO_DEFAULT,8,Support())
        data['scenario']='Prototype de référence'
        st.session_state.pending=data; st.rerun()

p=Plate(H=H,W=W,h=h,rho=rho,Es=Es,Eu=Eu,G=G,nu=nu,angle=angle,boundary=boundary,
        rotation=rotation,order=order,bridge_s=bs,bridge_mass=bm,damping=damping)
support=Support(enabled=support_enabled,joint_u=joint_u,width=support_width,
                depth=support_depth,rho=support_rho,E=support_E)
with st.expander('Réglages avancés des cordes et des électroaimants',expanded=False):
    n=int(number('Nombre de cordes','nstrings',5,1,12,1))
    rows=st.session_state.rows
    if n!=len(rows):
        new=to_rows(defaults(n))
        for i in range(min(len(rows),n)): new[i]=rows[i]
        st.session_state.rows=new; st.session_state.revision+=1
    st.markdown('<div class="small-note">Modifiez ici les valeurs mécaniques et électriques détaillées. Le choix guidé des harmoniques se trouve dans l’onglet Accordage.</div>',unsafe_allow_html=True)
    cc={}
    for k,(label,scale) in COLS.items():
        if k=='active': cc[label]=st.column_config.CheckboxColumn(label)
        else: cc[label]=st.column_config.NumberColumn(label,format='%.4f' if k in ('d','damping','force') else '%.3f')
    edited=st.data_editor(pd.DataFrame(st.session_state.rows),hide_index=True,
                         width='stretch',column_config=cc,num_rows='fixed',
                         key='strings_'+str(st.session_state.revision))
    st.session_state.rows=edited.to_dict('records')
try:
    strings=from_rows(st.session_state.rows); validate(p,strings,support)
except (ValueError,TypeError) as exc:
    st.error(str(exc)); st.stop()

@st.cache_resource(max_entries=8,show_spinner='Calcul des modes couplés…')
def compute(p,strings,ns,support):
    return assemble(p,strings,ns,support)
try: model=compute(p,tuple(strings),ns,support)
except (ValueError,np.linalg.LinAlgError) as exc:
    st.error('Calcul impossible : '+str(exc)); st.stop()

def level_labels(values):
    values=np.asarray(values,dtype=float)
    peak=max(float(np.max(values)) if len(values) else 0.,1e-30)
    db=20*np.log10(np.maximum(values/peak,1e-8))
    if len(values)==1:
        labels=np.array(['Référence unique'])
    else:
        labels=np.where(db>=-6,'Forte',np.where(db>=-18,'Moyenne','Faible'))
    return db,labels

def current_drive_table(model,listener=None):
    obs=plate_observation(model,listener); rows=[]
    for i,s in enumerate(model['strings']):
        if not s.active: continue
        q=response(model,[s.drive],i)[:,0]
        displacement=float(abs(obs@q))
        nearest=int(np.argmin(abs(model['f']-s.drive)))
        rows.append(dict(Corde=i+1,**{
            'Fréquence imposée (Hz)':s.drive,
            'Mode couplé le plus proche (Hz)':model['f'][nearest],
            'Écart au mode (Hz)':s.drive-model['f'][nearest],
            'Déplacement calculé (µm)':displacement*1e6,
            'Accélération calculée (m/s²)':displacement*(2*np.pi*s.drive)**2}))
    if rows:
        db,labels=level_labels([r['Accélération calculée (m/s²)'] for r in rows])
        for r,d,label in zip(rows,db,labels):
            r['Niveau relatif (dB)']=float(d); r['Réponse relative']=label
    return pd.DataFrame(rows)

if st.session_state.get('project_name'):
    st.info(f"Scénario actif : **{st.session_state.project_name}**")

a,b,c,d=st.columns(4)
a.metric('Plaque + chevalet' + (' + traverse' if support.enabled else ''),f"{model['fp'][0]:.1f} Hz")
b.metric('Premier mode couplé',f"{model['f'][0]:.1f} Hz")
c.metric('Masse de plaque',f'{p.rho*p.H*p.W*p.h*1000:.0f} g')
d.metric('Traction totale châssis',f'{sum(s.T for s in strings):.1f} N')
if support.enabled:
    support_mass=support.rho*support.width*support.depth*p.H
    st.caption(f'Deux panneaux avec collage central supposé parfait · traverse centrale {support.width*1000:.1f} × {support.depth*1000:.1f} mm · masse ajoutée {support_mass:.2f} kg · élévation prévue {geo.get("installation_height",0):g} m.')
st.markdown('**Commande → réponse :** les électroaimants imposent les fréquences des notes ; la table renforce ou atténue chacune d’elles selon sa réponse mécanique.')

tabs=st.tabs(['Prototype 3D','Modes et animations','Réponse et son','Accordage et cibles',
              'Étude Sandra · une corde'])
with tabs[0]:
    st.plotly_chart(scene(model,geo),width='stretch',key='assembly')
    st.caption('Rotation : glisser · zoom : molette · axes en mètres. Volume des aimants, sections du cadre, vis et hauteur du chevalet sont schématiques. Le vide derrière la plaque est conservé.')
with tabs[1]:
    family=st.radio('Système observé',['Plaque + masse chevalet','Ensemble couplé'],horizontal=True)
    coupled=family=='Ensemble couplé'
    f=model['f'] if coupled else model['fp']
    idx=st.selectbox('Mode',list(range(min(40,len(f)))),format_func=lambda i:f'Mode {i+1} · {f[i]:.2f} Hz')
    v=np.zeros(len(model['K']))
    if coupled: v=model['V'][:,idx].copy()
    else: v[:model['np']]=model['Vp'][:,idx]
    amplitude=st.slider('Amplification visuelle maximale (mm)',1,40,12)/1000
    fig=scene(model,geo,v,True,amplitude)
    # Script Plotly inclus dans le HTML : aucune dépendance CDN pour les animations.
    html=fig.to_html(full_html=False,include_plotlyjs=True,auto_play=False)
    if hasattr(st,'iframe'):
        st.iframe(html,height=740)
    else:
        components.html(html,height=740)
    st.caption('Animation ralentie (~2 s par cycle), déplacement amplifié : ni temps réel ni amplitude calculée. Même facteur d’amplification pour plaque et cordes. Le chevalet schématique reste fixe.')
    S,U=np.meshgrid(np.linspace(0,p.H,90),np.linspace(0,p.W,60),indexing='ij')
    field=basis(p,S,U)@v[:model['np']]
    field/=max(np.max(np.abs(field)),1e-20)
    contour=go.Figure(go.Contour(x=U[0]*1000,y=S[:,0]*1000,z=field,colorscale='RdBu',
        zmin=-1,zmax=1,contours=dict(start=-1,end=1,size=.2),colorbar=dict(title='w relatif')))
    contour.add_trace(go.Contour(x=U[0]*1000,y=S[:,0]*1000,z=field,
        contours=dict(start=0,end=0,size=1,coloring='none'),line=dict(color='black',width=3),
        showscale=False,hoverinfo='skip'))
    contour.update_layout(height=450,xaxis_title='u (mm)',yaxis_title='s depuis bas de plaque (mm)')
    st.plotly_chart(contour,width='stretch')
    st.caption('La courbe noire représente w=0 : lignes nodales. Un mode dominé par les cordes peut ne produire presque aucun déplacement de plaque.')
    table=pd.DataFrame({'Mode':np.arange(1,len(f)+1),'Fréquence (Hz)':f})
    if coupled: table['Fraction de masse modale plaque (%)']=100*model['plate_fraction']
    st.dataframe(table.head(40),hide_index=True)
    st.download_button('Exporter les modes CSV',table.to_csv(index=False).encode('utf-8-sig'),'modes.csv','text/csv')
with tabs[2]:
    st.subheader('Écouter la table d’harmonie')
    active_count=sum(s.active for s in strings)
    st.write(f'Le son entretenu réunit les deux électroaimants de chacune des **{active_count} cordes actives**. Chaque corde conserve sa fréquence et sa phase.')
    listen_mode=st.radio('Prise de son virtuelle',['Table entière','Point précis sur la plaque'],horizontal=True,
                         help='Table entière mélange le mouvement de toute la surface. Le point précis permet de comparer différentes zones de la plaque.')
    l,r=st.columns(2)
    with l:
        os=st.slider('Hauteur du point d’observation — s/H',.01,.99,.53,.01,
                     help='s/H est la hauteur relative : 0 correspond au bas de la plaque et 1 au haut.',
                     disabled=listen_mode=='Table entière')
    with r:
        ou=st.slider('Position horizontale — u/W',.01,.99,.43,.01,
                     help='u/W est la position relative dans la largeur : 0 correspond au bord gauche et 1 au bord droit.',
                     disabled=listen_mode=='Table entière')
    with st.expander('Que signifient s/H, u/W et la limite du balayage ?'):
        st.write('**s/H** place le point du bas vers le haut de la table. **u/W** le place de gauche à droite. Ces deux valeurs n’affectent que la mesure en un point et son écoute associée, pas le comportement mécanique calculé.')
        st.write('La **limite du balayage** est la fréquence la plus haute affichée dans le graphique. Une valeur plus grande explore davantage d’aigus, avec un calcul un peu plus long.')
    listener=None if listen_mode=='Table entière' else (os,ou)
    obs=plate_observation(model,listener)
    drive_table=current_drive_table(model,listener)
    with st.expander('Quelles fréquences la table joue-t-elle ?',expanded=True):
        if drive_table.empty:
            st.warning('Aucune corde active.')
        else:
            st.dataframe(drive_table,hide_index=True,width='stretch',column_config={
                'Fréquence imposée (Hz)':st.column_config.NumberColumn(format='%.2f Hz'),
                'Mode couplé le plus proche (Hz)':st.column_config.NumberColumn(format='%.2f Hz'),
                'Écart au mode (Hz)':st.column_config.NumberColumn(format='%+.2f Hz'),
                'Déplacement calculé (µm)':st.column_config.NumberColumn(format='%.4g'),
                'Accélération calculée (m/s²)':st.column_config.NumberColumn(format='%.4g'),
                'Niveau relatif (dB)':st.column_config.NumberColumn(format='%.1f dB')})
            st.caption('La fréquence jouée reste la fréquence imposée. « Forte », « moyenne » ou « faible » compare uniquement les cordes actives de cette configuration ; ce n’est pas un niveau acoustique réel. Le mode voisin influence l’amplitude, mais n’ajoute pas sa fréquence au son entretenu.')
    fmax=st.slider('Limite du balayage (Hz)',100,4000,1000,50,
                   help='Borne supérieure de l’analyse fréquentielle affichée ci-dessous.')
    if st.button('Calculer la réponse fréquentielle'):
        freq=np.unique(np.r_[np.linspace(5,fmax,1200),model['f'][model['f']<fmax]])
        transfer=obs@response(model,freq)
        frf=pd.DataFrame({'Fréquence (Hz)':freq,'Déplacement crête (µm)':np.abs(transfer)*1e6})
        st.plotly_chart(go.Figure(go.Scatter(x=freq,y=frf.iloc[:,1])).update_layout(
            xaxis_title='Fréquence commune imposée (Hz)',yaxis_title='Déplacement (µm)',yaxis_type='log'),width='stretch')
        st.download_button('Exporter la réponse CSV',frf.to_csv(index=False).encode(),'reponse.csv')
        st.caption('Le balayage applique une fréquence commune à tous les aimants afin de repérer les résonances. L’écoute entretenue utilise au contraire la fréquence choisie pour chaque corde.')
    kind_label=st.radio('Type d’écoute',['Électroaimants entretenus','Résonance après une impulsion'],horizontal=True)
    duration=st.slider('Durée (s)',1,10,4)
    if st.button('Créer le son combiné',type='primary'):
        kind='Entretenu' if kind_label=='Électroaimants entretenus' else 'Impulsion'
        wav,y,peak=synthesize(model,duration,kind,listener)
        st.audio(wav,format='audio/wav')
        st.download_button('Télécharger le son WAV',wav,'table_harmonie.wav','audio/wav')
        if peak<=1e-15: st.info('Signal nul : vérifier les cordes actives, les forces et le couplage.')
        else:
            spec=np.abs(np.fft.rfft(y*np.hanning(len(y))))
            freq=np.fft.rfftfreq(len(y),1/44100); sel=(freq>10)&(freq<5000)
            db=20*np.log10(np.maximum(spec/max(np.max(spec),1e-20),1e-8))
            st.plotly_chart(go.Figure(go.Scatter(x=freq[sel],y=db[sel])).update_layout(
                xaxis_title='Fréquence (Hz)',yaxis_title='Spectre relatif (dB)',height=300),width='stretch')
    st.info('Le volume est normalisé pour l’écoute. Le résultat permet de comparer les réglages entre eux, mais ne prédit pas le niveau sonore réel dans la pièce.')
with tabs[3]:
    st.subheader('Choisir les harmoniques à faire entendre')
    st.write('Sélectionnez un harmonique pour chaque corde, puis appliquez la configuration. Les fréquences d’excitation, les positions des deux aimants et leur phase relative seront réglées ensemble.')
    if st.button('Charger l’exemple : corde 2 au 5e, les autres au 2e'):
        for i in range(n): st.session_state['harmonic_'+str(i)]=min(ns,5) if i==1 else min(ns,2)
        st.rerun()
    header=st.columns([1.25,1.2,3,1.4])
    header[0].markdown('**Corde**'); header[1].markdown('**Dans le son**')
    header[2].markdown('**Harmonique visé**'); header[3].markdown('**Fréquence**')
    selected=[]
    for i,s in enumerate(strings):
        hk='harmonic_'+str(i); ak='play_'+str(i)
        if hk not in st.session_state or not 1<=int(st.session_state[hk])<=ns:
            st.session_state[hk]=min(ns,max(1,int(st.session_state.get(hk,1))))
        if ak not in st.session_state: st.session_state[ak]=bool(s.active)
        freqs=string_frequencies(s,ns)
        row=st.columns([1.25,1.2,3,1.4])
        row[0].write(f'Corde {i+1}')
        row[1].checkbox(f'Inclure la corde {i+1}',key=ak,label_visibility='collapsed')
        rank=row[2].selectbox(f'Harmonique corde {i+1}',range(1,ns+1),key=hk,label_visibility='collapsed',
                              format_func=lambda x:f'{x}ᵉ harmonique')
        row[3].write(f'**{freqs[rank-1]:.2f} Hz**')
        selected.append(rank)
    if st.button('Configurer tous les électroaimants',type='primary',width='stretch'):
        configured=[]
        for i,(s,rank) in enumerate(zip(strings,selected)):
            tuned=harmonic_drive_settings(s,rank)
            configured.append(replace(tuned,active=bool(st.session_state['play_'+str(i)])))
        st.session_state.rows=to_rows(configured)
        st.session_state.revision+=1
        st.session_state.harmonics_applied=selected
        st.rerun()
    applied=st.session_state.get('harmonics_applied')
    if applied and len(applied)==n:
        st.success('Configuration appliquée. Ouvrez « Réponse et son » puis cliquez sur « Créer le son combiné ».')
    summary=pd.DataFrame([{
        'Corde':i+1,'État':'active' if s.active else 'muette',
        'Harmonique':applied[i] if applied and i<len(applied) else '—',
        'Excitation (Hz)':round(s.drive,2),'Aimant 1 (% L)':round(100*s.p1,1),
        'Aimant 2 (% L)':round(100*s.p2,1),'Phase relative (°)':round(s.phase2)
    } for i,s in enumerate(strings)])
    with st.expander('Voir la configuration calculée',expanded=bool(applied)):
        st.dataframe(summary,hide_index=True,width='stretch')
        st.caption('Les aimants sont placés sur deux ventres du mode visé. Une phase relative de 180° inverse le second aimant lorsque les deux ventres se déplacent en sens opposés.')

    st.divider()
    st.subheader('Jouer une séquence de notes')
    st.write('Chargez une partition CSV. Pour chaque note, l’instrument choisit la corde et l’harmonique les plus proches, puis crée la chronologie de commande des deux électroaimants.')
    example_bytes=Path(__file__).with_name('exemple_fur_elise.csv').read_bytes()
    example_col,load_col=st.columns(2)
    example_col.download_button('Télécharger l’exemple Für Elise',example_bytes,
                                'exemple_fur_elise.csv','text/csv',width='stretch')
    if load_col.button('Utiliser cet exemple maintenant',width='stretch'):
        st.session_state.score_data=example_bytes
        st.session_state.score_name='exemple_fur_elise.csv'
    score_upload=st.file_uploader('Déposer une partition CSV',type=['csv'],key='score_upload')
    if score_upload is not None:
        st.session_state.score_data=score_upload.getvalue()
        st.session_state.score_name=score_upload.name
    with st.expander('Format du fichier de lecture'):
        st.write('Colonnes obligatoires : **start_s**, **duration_s**, **note** et **velocity**. Les notes acceptent C4, F#4, Bb3, Do4, Fa#4 ou Sib3. L’intensité velocity va de 0 à 1.')
        st.write('Les colonnes facultatives **string** et **harmonic** permettent d’imposer une corde ou un harmonique. Sans elles, l’affectation est automatique.')
    if st.session_state.get('score_data'):
        try:
            score=pd.read_csv(io.BytesIO(st.session_state.score_data),sep=None,engine='python')
            plan=sequence_plan(strings,score.to_dict('records'),ns)
            st.caption(f'{st.session_state.get("score_name","Séquence")} · {len(plan)} notes · durée {max(x["start_s"]+x["duration_s"] for x in plan):.2f} s')
            st.dataframe(score,hide_index=True,width='stretch',height=min(360,80+35*len(score)))
            control=pd.DataFrame(plan)
            obs_sequence=plate_observation(model,None)
            sequence_acceleration=[]
            for event in plan:
                si=int(event['string'])-1
                setting=harmonic_drive_settings(strings[si],int(event['harmonic']))
                setting=replace(setting,drive=event['frequency_hz'],
                                force=setting.force*event['velocity'])
                event_strings=list(strings); event_strings[si]=setting
                event_model={**model,'strings':tuple(event_strings)}
                q=response(event_model,[event['frequency_hz']],si)[:,0]
                sequence_acceleration.append(float(abs(obs_sequence@q)*(2*np.pi*event['frequency_hz'])**2))
            relative_db,quality=level_labels(sequence_acceleration)
            control['table_acceleration_m_s2']=sequence_acceleration
            control['table_relative_db']=relative_db
            control['table_response']=quality
            display=control.rename(columns={
                'start_ms':'Début (ms)','duration_ms':'Durée (ms)','note':'Note',
                'frequency_hz':'Fréquence (Hz)','velocity':'Intensité','string':'Corde',
                'harmonic':'Harmonique','magnet1_channel':'Canal aimant 1',
                'magnet2_channel':'Canal aimant 2','p1':'Position aimant 1 / L',
                'p2':'Position aimant 2 / L','phase2_deg':'Phase aimant 2 (°)',
                'detune_cents':'Écart à la corde (cents)',
                'table_relative_db':'Réponse table (dB relatif)',
                'table_response':'Transmission estimée'
            })
            visible=['Début (ms)','Durée (ms)','Note','Fréquence (Hz)','Corde','Harmonique',
                     'Canal aimant 1','Canal aimant 2','Position aimant 1 / L',
                     'Position aimant 2 / L','Phase aimant 2 (°)','Intensité',
                     'Écart à la corde (cents)','Réponse table (dB relatif)','Transmission estimée']
            with st.expander('Prévisualiser le plan de pilotage',expanded=True):
                st.dataframe(display[visible],hide_index=True,width='stretch')
                weak=int(np.sum(np.asarray(quality)=='Faible'))
                if len(plan)==1:
                    st.info('Une seule note : sa réponse calculée est affichée, mais aucune autre note ne permet une comparaison relative.')
                elif weak:
                    st.warning(f'{weak} événement(s) présentent une réponse de table faible par rapport à la note la plus forte de cette séquence.')
                else:
                    st.success('Aucune note n’est fortement atténuée par rapport aux autres dans cette simulation.')
                st.caption('Cette évaluation compare les accélérations calculées de la table entière. Elle ne prédit ni le volume réel dans le musée, ni les limites électriques des bobines.')
            dl1,dl2=st.columns(2)
            dl1.download_button('Télécharger le pilotage CSV',control.to_csv(index=False).encode('utf-8-sig'),
                                'pilotage_electroaimants.csv','text/csv',width='stretch')
            dl2.download_button('Télécharger le pilotage JSON',json.dumps(plan,indent=2,ensure_ascii=False),
                                'pilotage_electroaimants.json','application/json',width='stretch')
            if st.button('Écouter cette séquence sur la table',type='primary',width='stretch'):
                wav,y,peak=synthesize_sequence(model,plan)
                st.audio(wav,format='audio/wav')
                st.download_button('Télécharger cette interprétation',wav,'sequence_table_harmonie.wav','audio/wav')
                if peak<=1e-15: st.warning('Le réglage produit un signal trop faible avec la configuration actuelle.')
            st.info('Le fichier de pilotage fournit le temps, la fréquence, les canaux, les positions, les phases et les amplitudes relatives. L’électronique de commande doit ensuite convertir ces consignes selon les limites de vos bobines et de vos amplificateurs.')
        except (ValueError,KeyError,UnicodeError,pd.errors.ParserError) as exc:
            st.error('Partition illisible : '+str(exc))

    st.divider()
    st.subheader('Accorder une corde à une fréquence précise')
    ci=st.selectbox('Corde à accorder',range(n),format_func=lambda i:f'Corde {i+1}')
    target=st.number_input('Fréquence souhaitée (Hz)',min_value=1.,max_value=12000.,value=61.,step=1.,
                           help='Fréquence exacte que doit atteindre l’harmonique sélectionné.')
    harmonic=st.number_input('Harmonique à accorder',min_value=1,max_value=16,value=1)
    tension=tension_for(strings[ci],target,harmonic)
    st.metric('Tension nécessaire',f'{tension:.3f} N')
    if tension<=0: st.warning('Cible impossible en traction positive pour cette longueur, ce diamètre et ce partiel.')
    elif st.button('Appliquer cette tension à la corde'):
        ss=list(strings); ss[ci]=harmonic_drive_settings(replace(ss[ci],T=tension),harmonic)
        st.session_state.rows=to_rows(ss); st.session_state.revision+=1; st.rerun()
    ct=pd.DataFrame([{'Corde':i+1,'Fondamental isolé (Hz)':string_frequencies(s,1)[0],
            'Tension (N)':s.T,'Masse linéique (g/m)':s.rho*np.pi*s.d*s.d/4*1000,
            'Contrainte axiale (MPa)':s.T/(np.pi*s.d*s.d/4)/1e6} for i,s in enumerate(strings)])
    with st.expander('Voir les caractéristiques des cordes'):
        st.dataframe(ct,hide_index=True,width='stretch')

    st.divider()
    st.subheader('Ajuster l’épaisseur de la table à une résonance cible')
    pt=st.number_input('Résonance souhaitée de la plaque (Hz)',min_value=5.,max_value=3000.,value=61.)
    pm=st.selectbox('Mode de plaque à ajuster',range(min(12,len(model['fp']))),format_func=lambda i:f'Mode {i+1} · actuellement {model["fp"][i]:.1f} Hz')
    thickness_signature=json.dumps(dict(plate=asdict(p),support=asdict(support)),sort_keys=True)
    if st.button('Calculer l’épaisseur correspondante'):
        try:
            thickness=target_thickness(p,pt,pm,support)
            st.session_state.thickness_result=(thickness,thickness_signature,pt,pm)
        except ValueError as exc: st.error(str(exc))
    if 'thickness_result' in st.session_state:
        hh,signature,oldtarget,oldmode=st.session_state.thickness_result
        if signature==thickness_signature and oldtarget==pt and oldmode==pm:
            st.success(f'Épaisseur proposée : {hh*1000:.3f} mm')
            if st.button('Appliquer cette épaisseur'):
                st.session_state.new_h=hh*1000; st.rerun()

with tabs[4]:
    st.subheader('Une corde longue · comparer deux positions du chevalet')
    st.write('Le calcul garde la même corde et la même force. Seule la position du chevalet sur la table change : **10 % ou 22,5 % depuis le haut**.')
    if st.button('Charger le cas de référence · 10 m, 12 Hz, un aimant'):
        study_plate=Plate(H=2.4384,W=1.524,h=.003175,rho=650.,Es=10e9,Eu=10e9,
                          G=10e9/2.6,nu=.30,boundary='Appuis simples',bridge_s=2.19456,
                          bridge_mass=.010,damping=.012,order=6)
        study_geo=dict(height=2.4384,frame_width=1.524,depth=.305,plate_bottom=0.,
                       technical_height=.610,installation_height=15.)
        study_support=Support(enabled=True,width=.0381,depth=.0381,rho=500.,E=10e9)
        data=config_dict(study_plate,[reference_string()],study_geo,12,study_support)
        data['scenario']='Sandra · une corde de 10 m · hypothèses préliminaires'
        data['harmonics']=[5]
        st.session_state.pending=data
        st.rerun()
    st.caption('Cas de départ : fil de 0,762 mm, tension calculée pour 12 Hz, aimant unique à 10 % de la corde. Contact corde–chevalet à 5 % de L, couplage 500 N/m, force harmonique 0,01 N, masse de chevalet 10 g et propriétés du bois : hypothèses non mesurées.')
    if len(strings)!=1:
        st.warning('Chargez le cas de référence ci-dessus, ou réglez le nombre de cordes à 1 dans les paramètres avancés.')
    else:
        wire=strings[0]
        targets=string_frequencies(wire,7)
        st.markdown(f'**Corde actuelle :** L = {wire.L:.2f} m · d = {wire.d*1000:.3f} mm · '
                    f'T = {wire.T:.1f} N · f₁ = {targets[0]:.2f} Hz · '
                    f'f₅ = {targets[4]:.2f} Hz · f₇ = {targets[6]:.2f} Hz.')
        st.caption(f'Le point de contact sur la corde reste fixé à {100*wire.beta:.1f} % de L et l’aimant 1 à {100*wire.p1:.1f} % de L dans les deux cas. '
                   f'La comparaison utilise la plaque {p.H:.3f} × {p.W:.3f} m, avec les propriétés et fixations actuellement saisies.')
    comparison_signature=json.dumps(dict(plate=asdict(p),support=asdict(support),
                                         strings=[asdict(s) for s in strings]),sort_keys=True)
    if st.button('Comparer 10 % et 22,5 %',type='primary',disabled=len(strings)!=1):
        try:
            with st.spinner('Calcul aux résolutions 10, 12 et 14…'):
                st.session_state.sandra_comparison=compare_positions(p,strings[0],support)
                st.session_state.sandra_comparison_signature=comparison_signature
        except (ValueError,np.linalg.LinAlgError) as exc:
            st.error('Comparaison impossible : '+str(exc))
    study_rows=(st.session_state.get('sandra_comparison')
                if st.session_state.get('sandra_comparison_signature')==comparison_signature else None)
    study_summary=summarize_comparison(study_rows) if study_rows else None
    if study_summary:
        display=pd.DataFrame([{
            'Harmonique':r['harmonic'],'Force (Hz)':r['force_hz'],
            'Vibration globale · 10 % (m/s²)':r['rms_10'],
            'Vibration globale · 22,5 % (m/s²)':r['rms_22_5'],
            'Rapport 10 % / 22,5 %':r['ratio_10_over_22_5'],
            'Variation max. de résolution · 10 %':r['convergence_10'],
            'Variation max. de résolution · 22,5 %':r['convergence_22_5'],
            'Lecture':r['verdict']
        } for r in study_summary])
        st.dataframe(display,hide_index=True,width='stretch',column_config={
            'Force (Hz)':st.column_config.NumberColumn(format='%.2f'),
            'Vibration globale · 10 % (m/s²)':st.column_config.NumberColumn(format='%.4g'),
            'Vibration globale · 22,5 % (m/s²)':st.column_config.NumberColumn(format='%.4g'),
            'Rapport 10 % / 22,5 %':st.column_config.NumberColumn(format='%.3f'),
            'Variation max. de résolution · 10 %':st.column_config.NumberColumn(format='%.1%'),
            'Variation max. de résolution · 22,5 %':st.column_config.NumberColumn(format='%.1%')})
        bars=go.Figure()
        for label,key in [('10 %','rms_10'),('22,5 %','rms_22_5')]:
            bars.add_bar(name=label,x=[f'{r["force_hz"]:.1f} Hz' for r in study_summary],
                         y=[r[key] for r in study_summary])
        bars.update_layout(barmode='group',height=330,
                           yaxis_title='Accélération spatiale quadratique (m/s²)',
                           legend_title='Chevalet depuis le haut')
        st.plotly_chart(bars,width='stretch')
        if any(not r['stable'] for r in study_summary):
            st.warning('Au moins une réponse varie encore de plus de 10 % entre deux résolutions : résultat non concluant pour cette fréquence.')
        with st.expander('Détails : convergence et mouvement moyen cohérent'):
            st.dataframe(pd.DataFrame(study_rows),hide_index=True,width='stretch')
            coherent=pd.DataFrame([{
                'Force (Hz)':r['force_hz'],
                'Moyenne cohérente · 10 % (m/s²)':r['coherent_10'],
                'Moyenne cohérente · 22,5 % (m/s²)':r['coherent_22_5'],
                'Variation max. · 10 %':r['coherent_convergence_10'],
                'Variation max. · 22,5 %':r['coherent_convergence_22_5']
            } for r in study_summary])
            st.dataframe(coherent,hide_index=True,width='stretch')
            st.caption('La vibration globale est une moyenne quadratique spatiale : elle ne s’annule pas lorsque deux zones vibrent en sens opposés. La moyenne cohérente peut au contraire se compenser ; ni l’une ni l’autre ne prédit à elle seule le son dans la salle.')
        st.download_button('Télécharger la comparaison CSV',
                           pd.DataFrame(study_rows).to_csv(index=False).encode('utf-8-sig'),
                           'comparaison_chevalet_sandra.csv','text/csv')
        st.info('Les chiffres supposent la même force harmonique aux deux positions. « Plus élevé » décrit seulement le mouvement mécanique calculé, pas une différence de volume sonore au musée.')
        with st.expander('Vérifier l’effet des fixations supposées'):
            st.write('Une traverse ou un bord plus rigide peut déplacer les résonances et inverser le classement. Ces variantes servent à mesurer cette sensibilité, pas à décrire trois constructions confirmées.')
            if st.button('Comparer avec et sans traverse, puis bords encastrés'):
                try:
                    with st.spinner('Calcul des variantes de fixation…'):
                        cases=[('Réglage actuel',p,support),
                               ('Sans traverse',p,replace(support,enabled=False)),
                               ('Bords encastrés',replace(p,boundary='Encastrement'),support)]
                        sensitivity=[]
                        for name,case_plate,case_support in cases:
                            variant=summarize_comparison(compare_positions(
                                case_plate,strings[0],case_support,orders=(12,14)))
                            for item in variant:
                                sensitivity.append({'Hypothèse':name,
                                    'Force (Hz)':item['force_hz'],
                                    'Rapport vibration 10 % / 22,5 %':item['ratio_10_over_22_5'],
                                    'Convergence':('suffisante' if item['stable'] else 'insuffisante')})
                        st.session_state.sandra_sensitivity=sensitivity
                        st.session_state.sandra_sensitivity_signature=comparison_signature
                except (ValueError,np.linalg.LinAlgError) as exc:
                    st.error('Test de sensibilité impossible : '+str(exc))
            if st.session_state.get('sandra_sensitivity_signature')==comparison_signature:
                st.dataframe(pd.DataFrame(st.session_state.sandra_sensitivity),hide_index=True,
                             width='stretch',column_config={
                    'Rapport vibration 10 % / 22,5 %':st.column_config.NumberColumn(format='%.3f')})
                st.caption('Rapport > 1 : plus de vibration globale à 10 % ; rapport < 1 : plus à 22,5 %. Une convergence insuffisante interdit un verdict pour cette ligne.')

    st.divider()
    st.subheader('Confronter ces cibles à l’enregistrement T12')
    uploaded_t12=st.file_uploader('Déposer le WAV T12 ou son archive ZIP',type=['wav','zip'],key='sandra_t12_upload')
    st.caption('Le fichier est transmis au serveur Streamlit et analysé en mémoire pour cette session ; il n’est pas ajouté au dépôt du projet. Le WAV fourni par Sandra est exploratoire et non étalonné récemment.')
    if uploaded_t12 is not None:
        try:
            t12_data=uploaded_t12.getvalue()
            t12_info=audio_info(t12_data,uploaded_t12.name)
            st.write(f'**{t12_info["name"]}** · {t12_info["duration"]:.1f} s · '
                     f'{t12_info["sample_rate"]} Hz · {t12_info["channels"]} canal(aux)')
            chosen_channel=st.selectbox('Canal à analyser',range(t12_info['channels']),
                                        format_func=lambda i:f'Canal {i+1}',key='sandra_t12_channel')
            force_mapping=st.selectbox('Relation supposée entre courant et force',
                ['Force à la fréquence du courant · biais/linéarisation à vérifier',
                 'Force à deux fois la fréquence du courant · sans biais idéalisé'],
                key='sandra_t12_force_mapping')
            if st.button('Analyser les fréquences de T12'):
                with st.spinner('Lecture et analyse du signal…'):
                    st.session_state.sandra_t12=spectrum(t12_data,uploaded_t12.name,chosen_channel)
                    st.session_state.sandra_t12_signature=(uploaded_t12.name,len(t12_data),chosen_channel)
            current_audio=st.session_state.get('sandra_t12')
            if (current_audio is not None and
                st.session_state.get('sandra_t12_signature')==(uploaded_t12.name,len(t12_data),chosen_channel)):
                frequencies=current_audio['frequency_hz']; power=current_audio['power']
                selected=(frequencies>=5)&(frequencies<=150)
                reference_power=max(float(np.max(power[selected])),1e-30)
                spectrum_db=10*np.log10(np.maximum(power/reference_power,1e-12))
                plot=go.Figure(go.Scatter(x=frequencies[selected],y=spectrum_db[selected],
                                          mode='lines',name='T12'))
                plot.update_layout(height=350,xaxis_title='Fréquence du signal électrique (Hz)',
                                   yaxis_title='Densité spectrale relative (dB)')
                st.plotly_chart(plot,width='stretch')
                st.caption(f'{current_audio["analyzed_seconds"]:.1f} s analysées sur le canal {chosen_channel+1}. '
                           'Ces dB sont relatifs au fichier numérique : ils ne sont pas une accélération étalonnée du bâtiment.')
                if len(strings)==1:
                    factor=2 if force_mapping.startswith('Force à deux') else 1
                    target_rows=[]
                    for rank in (5,7):
                        mechanical=float(string_frequencies(strings[0],rank)[-1])
                        electrical=mechanical/factor
                        density=band_power(current_audio,electrical)
                        target_rows.append(dict(Harmonique=rank,
                            **{'Force recherchée (Hz)':mechanical,
                               'Fréquence à chercher dans T12 (Hz)':electrical,
                               'T12 relatif (dB)':10*np.log10(max(density/reference_power,1e-12)),
                               'poids':density}))
                    t12_targets=pd.DataFrame(target_rows)
                    st.dataframe(t12_targets.drop(columns='poids'),hide_index=True,width='stretch')
                    st.caption('Le scénario « force à deux fois la fréquence du courant » est une approximation d’un aimant attractif sans biais. Le comportement de la bobine réelle doit être mesuré.')
                    if study_summary:
                        weights={int(r['Harmonique']):float(r['poids']) for r in target_rows}
                        total=sum(weights.values())
                        if total>0:
                            combined={label:np.sqrt(sum(weights[r['harmonic']]*r[key]**2
                                for r in study_summary)/total)
                                for label,key in [('10 %','rms_10'),('22,5 %','rms_22_5')]}
                            combined_ratio=combined['10 %']/max(combined['22,5 %'],1e-30)
                            st.metric('Indice mécanique pondéré par T12 · 10 % / 22,5 %',
                                      f'{combined_ratio:.2f} ×')
                            if all(r['stable'] for r in study_summary):
                                if combined_ratio>=1.15:
                                    st.write('Selon cet indice mécanique, **10 %** donne la réponse globale la plus élevée pour ce fichier et ces hypothèses.')
                                elif combined_ratio<=1/1.15:
                                    st.write('Selon cet indice mécanique, **22,5 %** donne la réponse globale la plus élevée pour ce fichier et ces hypothèses.')
                                else:
                                    st.write('Selon cet indice mécanique, les deux positions donnent des réponses globales proches.')
                            else:
                                st.warning('La convergence d’au moins une fréquence est insuffisante : ne pas interpréter ce rapport comme un verdict.')
                            st.caption('Indice exploratoire : chaque fréquence reçoit un poids selon son énergie dans T12, avec le même gain inconnu pour les deux positions. Un pic électrique ou de chantier peut fausser ce poids. Ce rapport ne prédit pas le niveau sonore réel.')
        except (ValueError,TypeError,KeyError) as exc:
            st.error('Analyse T12 impossible : '+str(exc))

with st.sidebar.expander('Sauvegarder ou ouvrir une configuration'):
    cfg=config_dict(p,strings,geo,ns,support)
    cfg['harmonics']=[int(st.session_state.get('harmonic_'+str(i),1)) for i in range(n)]
    cfg['scenario']=st.session_state.get('project_name','Configuration personnalisée')
    st.download_button('Télécharger la configuration',json.dumps(cfg,indent=2,ensure_ascii=False),'harmonie.json','application/json')
    upload=st.file_uploader('Ouvrir une configuration',type=['json'])
    if upload is not None and st.button('Charger la configuration'):
        try:
            data=json.loads(upload.getvalue()); load_config(data)
            st.session_state.pending=data; st.rerun()
        except (ValueError,TypeError,KeyError) as exc: st.error('Projet invalide : '+str(exc))
