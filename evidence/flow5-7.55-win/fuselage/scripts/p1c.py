import json,sys,subprocess,numpy as np
from pathlib import Path
tag,method,hoop,xp,thin=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),sys.argv[5]=='1'
c=json.load(open('examples/flow5-c162-like-fuselage.json',encoding='utf-8'))
c['fuselage'].update(hoop_panels=hoop,x_panels=xp)
if len(sys.argv)>6 and sys.argv[6]=='nofin': c['wings']=[w for w in c['wings'] if w['type']!='FIN']
if len(sys.argv)>7 and sys.argv[7]=='nofus': c.pop('fuselage')
a=c['analysis']; a.update(include_fuse_moments=True,viscous=False,xfoil_on_the_fly=False,alpha_deg=[-4,8,2],method=method,thin_surfaces=thin)
cfg=Path(f'results/q-{tag}.json'); cfg.write_text(json.dumps(c),encoding='utf-8')
subprocess.run([sys.executable,'-m','aerosuite','flow5-export','--config',str(cfg),'--out',f'results/q-{tag}'],capture_output=True)
subprocess.run([sys.executable,'-m','aerosuite','flow5-run','--job',f'results/q-{tag}','--timeout','300'],capture_output=True)
d=json.load(open(f'results/q-{tag}/flow5_results.json',encoding='utf-8'))
p=d['polars'][0]; rows=p['rows']
al=np.radians([r['alpha_deg'] for r in rows])
print(tag,'dCL/da',round(np.polyfit(al,[r['CL'] for r in rows],1)[0],3),'dCm/da',round(np.polyfit(al,[r['Cm'] for r in rows],1)[0],3),'Fy',max(abs(r['Fy_sum']) for r in rows),'XNP',[round(r['XNP_m'],3) for r in rows][:3])
