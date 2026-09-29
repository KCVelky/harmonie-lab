import numpy as np
import plotly.graph_objects as go
from physics import basis

BLUE='#378cff'
GOLD='#e8b36d'

def line(points,name,color=GOLD,width=5):
    a=np.array(points)
    return go.Scatter3d(x=a[:,0],y=a[:,1],z=a[:,2],mode='lines',
                       line=dict(color=color,width=width),name=name,showlegend=False)

def box(fig,x0,x1,y0,y1,z0,z1,color,name,opacity=.6):
    x=[x0,x1,x1,x0,x0,x1,x1,x0]; y=[y0,y0,y1,y1,y0,y0,y1,y1]; z=[z0]*4+[z1]*4
    fig.add_trace(go.Mesh3d(x=x,y=y,z=z,
        i=[0,0,4,4,0,0,1,1,2,2,3,3],j=[1,2,5,6,1,5,2,6,3,7,0,4],
        k=[2,3,6,7,5,4,6,5,7,6,4,7],color=color,opacity=opacity,name=name,hoverinfo='name',showlegend=False))

def scene(model,geo,vector=None,animation=False,amplitude=.012):
    p=model['p']; support=model.get('support'); strings=model['strings']; off=geo['plate_bottom']
    S,U=np.meshgrid(np.linspace(0,p.H,38),np.linspace(0,p.W,23),indexing='ij')
    if vector is None: vector=np.zeros(len(model['K']))
    wp=basis(p,S,U)@vector[:model['np']]
    shapes=[]; xi=np.linspace(0,1,100)
    for i,s in enumerate(strings):
        sl=slice(model['np']+i*model['ns'],model['np']+(i+1)*model['ns'])
        shapes.append(np.sin(xi[:,None]*np.arange(1,model['ns']+1)*np.pi)@vector[sl])
    scale=max(float(np.max(np.abs(wp))),max((np.max(np.abs(q)) for q in shapes),default=0),1e-20)
    wp=np.real(wp)/scale*amplitude
    shapes=[np.real(q)/scale*amplitude for q in shapes]
    fig=go.Figure()
    # Tous les objets animés sont en tête de la liste des traces.
    fig.add_trace(go.Surface(x=U-p.W/2,y=wp,z=S+off,surfacecolor=wp,
        colorscale='RdBu',cmin=-amplitude,cmax=amplitude,showscale=False,
        name='Plaque',hovertemplate='u=%{x:.3f} m<br>s global=%{z:.3f} m<extra>Plaque</extra>'))
    basepaths=[]
    for i,s in enumerate(strings):
        s0=off+p.bridge_s-s.beta*s.L
        # Déviation symétrique : alpha total, hauteur de contact 20 mm (visuel).
        y=.020-np.abs(xi-s.beta)*s.L*np.tan(np.deg2rad(s.angle)/2)
        basepaths.append(y)
        fig.add_trace(go.Scatter3d(x=np.full_like(xi,(s.u-.5)*p.W),y=y+shapes[i],z=s0+xi*s.L,
            mode='lines',line=dict(color='#f0be62' if s.active else '#78899c',width=4),
            name=f'Corde {i+1}',showlegend=False))
    if support is not None and support.enabled:
        joint_x=(support.joint_u-.5)*p.W
        fig.add_trace(line([[joint_x,.001,off],[joint_x,.001,off+p.H]],
                           'Jonction collée des panneaux','#d9edf7',4))
    framew=geo['frame_width']; depth=geo['depth']; height=geo['height']
    for x in (-framew/2+.012,framew/2-.012):
        box(fig,x-.012,x+.012,-depth,0,0,height,'#80654b','Montant du châssis')
    for z in (.02,height-.02):
        box(fig,-framew/2,framew/2,-depth,0,z-.012,z+.012,'#80654b','Traverse structurelle')
    # Cadre périphérique : la condition de bord porte son effet mécanique.
    edge_w=support.width if support is not None and support.enabled else .015
    edge_d=support.depth if support is not None and support.enabled else .027
    for x in (-p.W/2-edge_w/2,p.W/2+edge_w/2):
        box(fig,x-edge_w/2,x+edge_w/2,-edge_d-.003,-.003,
            off-edge_w,off+p.H+edge_w,'#947453','Cadre périphérique')
    for z in (off-edge_w/2,off+p.H+edge_w/2):
        box(fig,-p.W/2,p.W/2,-edge_d-.003,-.003,
            z-edge_w/2,z+edge_w/2,'#947453','Cadre périphérique')
    if support is not None and support.enabled:
        joint_x=(support.joint_u-.5)*p.W
        box(fig,joint_x-support.width/2,joint_x+support.width/2,
            -support.depth-.003,-.003,off,off+p.H,'#75583f','Traverse centrale modélisée',.85)
    box(fig,-p.W*.47,p.W*.47,0,.020,off+p.bridge_s-.004,off+p.bridge_s+.004,'#edc580','Chevalet : masse répartie, rigidité non modélisée')
    screws=[]
    for z in np.linspace(off,off+p.H,max(3,int(p.H/.08)+1)):
        screws.extend([[-p.W/2-.0075,0,z],[p.W/2+.0075,0,z]])
    for x in np.linspace(-p.W/2,p.W/2,max(3,int(p.W/.08)+1)):
        screws.extend([[x,0,off-.0075],[x,0,off+p.H+.0075]])
    a=np.array(screws)
    fig.add_trace(go.Scatter3d(x=a[:,0],y=a[:,1],z=a[:,2],mode='markers',marker=dict(size=2,color='#ccd5df'),name='Vis périphériques',showlegend=False))
    for i,s in enumerate(strings):
        x=(s.u-.5)*p.W; s0=off+p.bridge_s-s.beta*s.L
        fig.add_trace(line([[x,-.08,s0],[x,-.08,s0+s.L]],'Rail indépendant','#64798d',2))
        for j,(pos,g,gain) in enumerate([(s.p1,s.g1,1),(s.p2,s.g2,s.gain2)]):
            z=s0+pos*s.L; wire_y=.020-abs(pos-s.beta)*s.L*np.tan(np.deg2rad(s.angle)/2)
            box(fig,x-.009,x+.009,wire_y-g-.018,wire_y-g,z-.013,z+.013,
                BLUE if gain else '#596473',f'Électroaimant {i+1}.{j+1} / g={g*1e3:.1f} mm')
            fig.add_trace(line([[x,-.08,z],[x,wire_y-g-.018,z]],'Support aimant','#7b8998',3))
        for t in (0.,1.):
            y=.020-abs(t-s.beta)*s.L*np.tan(np.deg2rad(s.angle)/2)
            fig.add_trace(line([[x,y,s0+t*s.L],[x,-depth/2,s0+t*s.L]],'Ancrage structurel','#c8d1dc',5))
    fig.add_trace(line([[-framew/2,0,geo['technical_height']],[framew/2,0,geo['technical_height']]],'Limite zone technique','#3d7788',2))
    elevation=geo.get('installation_height',0.)
    title=f'Installation prévue à environ {elevation:g} m dans le musée' if elevation else None
    fig.update_layout(height=680,margin=dict(l=0,r=0,t=15,b=0),paper_bgcolor='#101923',
        title=dict(text=title,x=.5,font=dict(size=15)) if title else None,
        font=dict(color='#c5d2e1'),scene=dict(bgcolor='#101923',
        xaxis_title='u : largeur (m)',yaxis_title='z : normale (m)',zaxis_title='s : verticale (m)',
        aspectmode='data',camera=dict(eye=dict(x=1.7,y=2.7,z=.7))),uirevision='geometry')
    if animation:
        frames=[]
        for k,t in enumerate(np.linspace(0,2*np.pi,32,endpoint=False)):
            c=np.cos(t)
            traces=[go.Surface(y=wp*c)]
            traces.extend(go.Scatter3d(y=y+q*c) for y,q in zip(basepaths,shapes))
            frames.append(go.Frame(data=traces,traces=list(range(len(strings)+1)),name=str(k)))
        fig.frames=frames
        fig.update_layout(updatemenus=[dict(type='buttons',x=.02,y=.98,
            buttons=[dict(label='▶ Animer au ralenti',method='animate',args=[None,dict(frame=dict(duration=65,redraw=True),transition=dict(duration=0),fromcurrent=True,mode='immediate')]),
                     dict(label='Pause',method='animate',args=[[None],dict(frame=dict(duration=0,redraw=False),mode='immediate')])])])
    return fig
