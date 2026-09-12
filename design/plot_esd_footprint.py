"""Plot dimensions read back from the saved native ESD footprint checker."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'kicad/usb3_sfp_hub/validation'
data=json.loads((OUT/'esd_footprint.json').read_text())
fig,ax=plt.subplots(figsize=(5,7),layout='constrained')
ax.add_patch(Rectangle((-.5,-1.25),1,2.5,fill=False,color='gray',linestyle='--'))
for p in data['pads']:
    x,y,w,h=p['x_mm'],p['y_mm'],p['width_mm'],p['height_mm']
    ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='#b9742b'))
    ph=p['paste_height_mm']
    ax.add_patch(Rectangle((x-w/2,y-ph/2),w,ph,fill=False,color='#00a6bd',linewidth=1.5))
    ax.text(x+(-.45 if x<0 else .45),y,str(p['pin']),ha='center',va='center')
ax.set(xlim=(-1.2,1.2),ylim=(1.6,-1.6),aspect='equal',xlabel='x (mm)',ylabel='y (mm)',
       title='TI DQA0010A — PCB top view\nCopper brown; paste outline cyan\nPads 3/8: ground; no separate EP')
ax.grid(alpha=.2)
fig.savefig(OUT/'esd_footprint.png',dpi=160)
fig.savefig(OUT/'esd_footprint.svg')
