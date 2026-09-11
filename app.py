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
from physics import (Plate,String,defaults,assemble,basis,string_frequencies,tension_for,
                     response,target_thickness,synthesize,config_dict,validate,
                     harmonic_drive_settings,plate_observation,sequence_plan,
                     synthesize_sequence)
from materials import MATERIALS
from visuals import scene

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

GEO_DEFAULT=dict(height=1.524,frame_width=.305,depth=.305,plate_bottom=.420,technical_height=.610)
PLATE_SCALES=dict(H=1000,W=1000,h=1000,Es=1e-9,Eu=1e-9,G=1e-9,bridge_s=1000,bridge_mass=1000)
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
    if any(not np.isfinite(float(v)) or not 0<=float(v)<=10 for v in geo.values()):
        raise ValueError('Géométrie invalide.')
    ns=int(data.get('string_modes',8))
    if not 2<=ns<=16: raise ValueError('Nombre de modes de corde hors limites.')
    harmonics=data.get('harmonics',[])
    if harmonics and (len(harmonics)!=len(strings) or any(int(x)!=x or not 1<=int(x)<=ns for x in harmonics)):
        raise ValueError('Sélection d’harmoniques invalide.')
    return p,strings,geo,ns

def queue_plate(p):
    for k,v in asdict(p).items():
        st.session_state['p_'+k]=v*PLATE_SCALES.get(k,1) if isinstance(v,float) else v

if 'rows' not in st.session_state:
    st.session_state.rows=to_rows(defaults())
    st.session_state.revision=0
    st.session_state.material=list(MATERIALS)[0]
if 'pending' in st.session_state:
    pending=st.session_state.pop('pending')
    p0,s0,g0,ns0=load_config(pending)
    queue_plate(p0); st.session_state.rows=to_rows(s0)
    st.session_state.nstrings=len(s0); st.session_state.ns=ns0
    st.session_state.material='Personnalisé'
    for i,rank in enumerate(pending.get('harmonics',[])):
        st.session_state['harmonic_'+str(i)]=int(rank)
    if pending.get('harmonics'):
        st.session_state.harmonics_applied=[int(x) for x in pending['harmonics']]
    for k,v in g0.items(): st.session_state['g_'+k]=v*1000
    st.session_state.revision+=1
if 'new_h' in st.session_state:
    st.session_state.p_h=st.session_state.pop('new_h')

def material_change():
    mat=MATERIALS[st.session_state.material]
    for k in ('rho','Es','Eu','G','nu'): st.session_state['p_'+k]=mat[k]

def number(label,key,value,minv,maxv,step,help=None):
    if key not in st.session_state: st.session_state[key]=value
    return st.number_input(label,min_value=minv,max_value=maxv,step=step,key=key,help=help)

with st.sidebar:
    st.header('Table d’harmonie')
    st.selectbox('Matériau',list(MATERIALS),key='material',on_change=material_change)
    mat=MATERIALS[st.session_state.material]
    st.caption(mat['note'])
    p0=Plate()
    H=number('Hauteur libre (mm)','p_H',610.,50.,5000.,10.)/1000
    W=number('Largeur libre (mm)','p_W',305.,50.,5000.,5.)/1000
    h=number('Épaisseur (mm)','p_h',2.,.2,30.,.1)/1000
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
    with st.expander('Châssis : vue 3D'):
        geo={}
        labels=dict(height='Hauteur châssis',frame_width='Largeur châssis',depth='Profondeur châssis',
                    plate_bottom='Bas de plaque / sol',technical_height='Hauteur zone technique')
        for k,v in GEO_DEFAULT.items():
            geo[k]=number(labels[k]+' (mm)','g_'+k,v*1000,0.,10000.,10.)/1000
    if st.button('Réinitialiser le prototype'):
        st.session_state.pending=config_dict(Plate(),defaults(),GEO_DEFAULT,8); st.rerun()

p=Plate(H=H,W=W,h=h,rho=rho,Es=Es,Eu=Eu,G=G,nu=nu,angle=angle,boundary=boundary,
        rotation=rotation,order=order,bridge_s=bs,bridge_mass=bm,damping=damping)
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
    strings=from_rows(st.session_state.rows); validate(p,strings)
except (ValueError,TypeError) as exc:
    st.error(str(exc)); st.stop()

@st.cache_resource(max_entries=8,show_spinner='Calcul des modes couplés…')
def compute(p,strings,ns):
    return assemble(p,strings,ns)
try: model=compute(p,tuple(strings),ns)
except (ValueError,np.linalg.LinAlgError) as exc:
    st.error('Calcul impossible : '+str(exc)); st.stop()

a,b,c,d=st.columns(4)
a.metric('Plaque seule + masse chevalet',f"{model['fp'][0]:.1f} Hz")
b.metric('Premier mode couplé',f"{model['f'][0]:.1f} Hz")
c.metric('Masse de plaque',f'{p.rho*p.H*p.W*p.h*1000:.0f} g')
d.metric('Traction totale châssis',f'{sum(s.T for s in strings):.1f} N')

tabs=st.tabs(['Prototype 3D','Modes et animations','Réponse et son','Accordage et cibles'])
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
            display=control.rename(columns={
                'start_ms':'Début (ms)','duration_ms':'Durée (ms)','note':'Note',
                'frequency_hz':'Fréquence (Hz)','velocity':'Intensité','string':'Corde',
                'harmonic':'Harmonique','magnet1_channel':'Canal aimant 1',
                'magnet2_channel':'Canal aimant 2','p1':'Position aimant 1 / L',
                'p2':'Position aimant 2 / L','phase2_deg':'Phase aimant 2 (°)'
            })
            visible=['Début (ms)','Durée (ms)','Note','Fréquence (Hz)','Corde','Harmonique',
                     'Canal aimant 1','Canal aimant 2','Position aimant 1 / L',
                     'Position aimant 2 / L','Phase aimant 2 (°)','Intensité']
            with st.expander('Prévisualiser le plan de pilotage',expanded=True):
                st.dataframe(display[visible],hide_index=True,width='stretch')
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
    if st.button('Calculer l’épaisseur correspondante'):
        try:
            thickness=target_thickness(p,pt,pm)
            st.session_state.thickness_result=(thickness,json.dumps(asdict(p),sort_keys=True),pt,pm)
        except ValueError as exc: st.error(str(exc))
    if 'thickness_result' in st.session_state:
        hh,signature,oldtarget,oldmode=st.session_state.thickness_result
        if signature==json.dumps(asdict(p),sort_keys=True) and oldtarget==pt and oldmode==pm:
            st.success(f'Épaisseur proposée : {hh*1000:.3f} mm')
            if st.button('Appliquer cette épaisseur'):
                st.session_state.new_h=hh*1000; st.rerun()

with st.sidebar.expander('Sauvegarder ou ouvrir une configuration'):
    cfg=config_dict(p,strings,geo,ns)
    cfg['harmonics']=[int(st.session_state.get('harmonic_'+str(i),1)) for i in range(n)]
    st.download_button('Télécharger la configuration',json.dumps(cfg,indent=2,ensure_ascii=False),'harmonie.json','application/json')
    upload=st.file_uploader('Ouvrir une configuration',type=['json'])
    if upload is not None and st.button('Charger la configuration'):
        try:
            data=json.loads(upload.getvalue()); load_config(data)
            st.session_state.pending=data; st.rerun()
        except (ValueError,TypeError,KeyError) as exc: st.error('Projet invalide : '+str(exc))
