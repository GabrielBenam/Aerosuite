import json,sys,subprocess,numpy as np
from pathlib import Path
sys.path.insert(0,'.')
from aerosuite import m16_stability as m
from aerosuite.m09b_wing import cl_alpha_helmbold
z=float(sys.argv[1]); tag=f'q-tailz-{sys.argv[1]}'
c=json.load(open('examples/flow5-c162-like.json',encoding='utf-8'))
for w in c['wings']:
    if w['type'] in('ELEVATOR','FIN'): w['position_m'][2]=z
a=c['analysis']; a.update(viscous=False,xfoil_on_the_fly=False,alpha_deg=[-2,6,2],method='VLM2')
cfg=Path(f'results/{tag}.json'); cfg.write_text(json.dumps(c),encoding='utf-8')
subprocess.run([sys.executable,'-m','aerosuite','flow5-export','--config',str(cfg),'--out',f'results/{tag}'],capture_output=True)
subprocess.run([sys.executable,'-m','aerosuite','flow5-run','--job',f'results/{tag}','--timeout','300'],capture_output=True)
d=json.load(open(f'results/{tag}/flow5_results.json',encoding='utf-8'));p=d['polars'][0];rows=p['rows']
al=np.radians([r['alpha_deg'] for r in rows]);cl=[r['CL'] for r in rows];cm=[r['Cm'] for r in rows]
xnp=[float(l.split('=')[-1].replace('m','')) for l in p['properties_text'].split('\n') if l.startswith('XNP')][0]
print(z,'CLa',np.polyfit(al,cl,1)[0],'Cma',np.polyfit(al,cm,1)[0],'XNP',xnp)
