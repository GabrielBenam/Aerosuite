import json, math, sys
import numpy as np
sys.path.insert(0, '.')
from aerosuite import m19_stall as m19
from aerosuite.flow5_results import collect

def dist(job):
    d = collect(f'evidence/flow5-7.55-win/m19-distribution/{ {"p3-wing-vlm2":"vlm2-ala-sola","p3-wing-llt":"llt-ala-sola"}[job] }/output')
    return d

cr, ct, hb = 1.25, 1.11, 4.72
span = 2 * hb
chords = lambda e: cr + (ct - cr) * e
azl = math.radians(m19.alpha_zl_naca4_deg('2412'))
tw = lambda e: -math.radians(1.5) * e
cla = lambda e: 2 * math.pi
res = {}
for job in ('p3-wing-vlm2', 'p3-wing-llt'):
    d = dist(job)
    rows = []
    for o in sorted(d['operating_points'], key=lambda o: o['scalars']['alpha_deg']):
        a = o['scalars']['alpha_deg']
        sp = o['span']['Main wing']['rows']
        ys = np.array([r['y_m'] for r in sp]); cl5 = np.array([r['Cl'] for r in sp])
        sel = ys >= 0
        eta = ys[sel] / hb
        mm = m19.llt_solve(span, chords, cla, lambda e: azl, tw, math.radians(a + 1.0))
        cl19 = np.array([mm['cl_of'](min(e, 1.0)) for e in eta])
        rows.append({'alpha_deg': a, 'CL_flow5': o['scalars']['CL'], 'CL_m19': mm['cl_total'],
                     'cl_flow5_eta': dict(zip(np.round(eta, 3).tolist(), cl5[sel].round(4).tolist())),
                     'rms_diff': float(np.sqrt(np.mean((cl19 - cl5[sel]) ** 2))), 'max_cl_flow5': float(cl5[sel].max()), 'max_cl_m19': float(cl19.max()),
                     'eta_max_flow5': float(eta[cl5[sel].argmax()]), 'eta_max_m19': float(eta[cl19.argmax()])})
    res[job] = rows
    print(job)
    for r in rows: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != 'cl_flow5_eta'})
json.dump(res, open('evidence/flow5-7.55-win/m19-distribution/m19_vs_flow5.json', 'w'), indent=1)

# ---- stall advance: station cl / clmax(Re) in flow5 LLT against the M19 first-stall criterion with the same foil data
d = collect('evidence/flow5-7.55-win/m19-distribution/llt-ala-sola/output')
fps = sorted(d['foil_polars'], key=lambda f: f['reynolds'])
clmax_re = {f['reynolds']: max(r['CL'] for r in f['rows']) for f in fps}
print('clmax(Re) from flow5/XFoil polars', clmax_re)
res_re = np.array(list(clmax_re.keys())); res_cm = np.array(list(clmax_re.values()))
rows = []
for o in sorted(d['operating_points'], key=lambda o: o['scalars']['alpha_deg']):
    a = o['scalars']['alpha_deg']
    sp = [r for r in o['span']['Main wing']['rows'] if r['y_m'] >= 0]
    ratio = [(r['y_m'] / hb, r['Cl'] / float(np.interp(r['Re'], res_re, res_cm))) for r in sp]
    k = max(ratio, key=lambda t: t[1])
    rows.append((a, round(k[0], 3), round(k[1], 3)))
print('flow5 LLT: alpha, eta of max cl/clmax, ratio', rows)
re_root, re_tip = 1.25 * 58.1 / 1.7779e-5 * 0 + 3.8e6, 3.4e6
cm_root, cm_tip = float(np.interp(re_root, res_re, res_cm)), float(np.interp(re_tip, res_re, res_cm))
print('clmax root/tip', cm_root, cm_tip)
clmax_f = lambda e: cm_root + (cm_tip - cm_root) * e
st = m19.stall_progression(span, chords, cla, lambda e: azl, tw, clmax_f, step_deg=0.25)
f = m19.refine_first_stall(span, chords, cla, lambda e: azl, tw, clmax_f, st['first']['alpha_deg'] - 0.25, st['first']['alpha_deg'])
print('M19 first stall alpha(without the +1 deg incidence) =', f['alpha_deg'], 'eta', f['eta'], 'CL', f['cl_total'], 'flow5-frame alpha', f['alpha_deg'] - 1.0)
