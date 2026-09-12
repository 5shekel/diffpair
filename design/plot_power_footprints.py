"""Plot actual saved copper geometry exported by check_power_footprints.py."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

out=Path(__file__).resolve().parents[1]/'kicad/usb3_sfp_hub/validation'
data=json.loads((out/'power_footprints.json').read_text())['footprints']
fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
for ax,(name,item) in zip(axes,data.items()):
    is_ti=name.startswith('TI')
    width,height=(1.5,2) if is_ti else (4,4)
    ax.add_patch(Rectangle((-width/2,-height/2),width,height,fill=False,linestyle='--',edgecolor='#697985',lw=1.5))
    for n,p in item['pads'].items():
        ax.add_patch(Rectangle((p['x']-p['w']/2,p['y']-p['h']/2),p['w'],p['h'],facecolor='#db7938',edgecolor='#703b18'))
        ax.text(p['x'],p['y'],n,ha='center',va='center',color='white',weight='bold',fontsize=10)
    ax.set_aspect('equal'); extent=1.5 if is_ti else 2.5
    ax.set_xlim(-extent,extent); ax.set_ylim(extent,-extent)
    ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)'); ax.grid(alpha=.15)
    ax.set_title(('TI RPJ0009A — nine pads' if is_ti else 'Coilcraft XGL4020 — two pads')+'\nPCB top view',fontsize=12)
fig.suptitle('Saved footprint copper geometry • dashed outline = nominal body',fontsize=13)
fig.savefig(out/'power_footprints.png',dpi=170)
fig.savefig(out/'power_footprints.svg')
