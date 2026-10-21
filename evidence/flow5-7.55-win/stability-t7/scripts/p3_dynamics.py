"""P-3: M16 dynamic contrast with a flow5 type 7 polar. Usage (repo root): python evidence/flow5-7.55-win/stability-t7/scripts/p3_dynamics.py <job_dir> <config.json> <out.json>"""
import glob, json, sys
sys.path.insert(0, ".")
from aerosuite import m16_flow5_contrast as mc

job, cfg_path, out = sys.argv[1:4]
cfg = json.load(open(cfg_path, encoding="utf-8"))
res = json.load(open(f"{job}/flow5_results.json", encoding="utf-8"))
log = open(glob.glob(f"{job}/output/*/*.log")[0], encoding="utf-8", errors="replace").read()
rep = mc.contrast(res["operating_points"][0], res["polars"][0]["rows"][0], cfg, log_text=log)
json.dump(rep, open(out, "w", encoding="utf-8"), indent=1)
print(json.dumps({k: rep[k] for k in ("derivatives", "modes_flow5", "modes_from_flow5_state_matrices", "modes_flow5_derivatives_in_m16_matrices",
                                      "modes_m16_with_flow5_lateral_derivatives", "modes_m16_without_alpha_dot_longitudinal",
                                      "longitudinal_eigenvalues_m16", "longitudinal_eigenvalues_m16_without_alpha_dot")}, indent=1))
