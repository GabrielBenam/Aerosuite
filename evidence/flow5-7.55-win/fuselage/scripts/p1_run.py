import json,sys,subprocess,numpy as np
from pathlib import Path
tag,method,fus,thin=sys.argv[1],sys.argv[2],sys.argv[3]=='1',sys.argv[4]=='1'
c=json.load(open('examples/flow5-c162-like-fuselage.json',encoding='utf-8'))
if not fus: c.pop('fuselage')
a=c['analysis']; a.update(viscous=False,xfoil_on_the_fly=False,alpha_deg=[-4,8,2],method=method,thin_surfaces=thin)
cfg=Path(f'results/q-{tag}.json'); cfg.write_text(json.dumps(c),encoding='utf-8')
subprocess.run([sys.executable,'-m','aerosuite','flow5-export','--config',str(cfg),'--out',f'results/q-{tag}'],capture_output=True)
subprocess.run([sys.executable,'-m','aerosuite','flow5-run','--job',f'results/q-{tag}','--timeout','300'],capture_output=True)
d=json.load(open(f'results/q-{tag}/flow5_results.json',encoding='utf-8'))
p=d['polars'][0]; rows=p['rows']
al=np.radians([r['alpha_deg'] for r in rows]); cl=[r['CL'] for r in rows]; cm=[r['Cm'] for r in rows]
print(tag,'dCL/da',np.polyfit(al,cl,1)[0],'dCm/da',np.polyfit(al,cm,1)[0],[l for l in p['properties_text'].split('\n') if 'XNP' in l or 'Static' in l])
print('  Fy_sum max',max(abs(r['Fy_sum']) for r in rows),'CD min',min(r['CD'] for r in rows),'XNP per point',[round(r['XNP_m'],3) for r in rows])
