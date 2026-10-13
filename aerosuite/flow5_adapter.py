"""Launch a locally built flow5 v7.57 batch executable.

This is an invocation layer: it does not implement XFoil or parse aerodynamic
coefficients. Actual analysis requires an external compiled solver executable.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import math
import subprocess
import time

@dataclass(frozen=True)
class Flow5Job:
    naca: str
    reynolds: tuple[float, ...]
    alpha_start: float = -4.0
    alpha_end: float = 12.0
    alpha_step: float = 1.0
    mach: float = 0.0

    def validate(self) -> None:
        if len(self.naca) != 4 or not self.naca.isascii() or not self.naca.isdigit():
            raise ValueError("NACA must be four ASCII digits")
        m, p, thickness = int(self.naca[0]), int(self.naca[1]), int(self.naca[2:])
        if thickness == 0 or ((m == 0) != (p == 0)):
            raise ValueError("Invalid NACA geometry")
        if not self.reynolds or len(self.reynolds) > 32 or any(not math.isfinite(v) or v <= 0 for v in self.reynolds):
            raise ValueError("Reynolds requires 1-32 finite, positive numbers")
        alphas = (self.alpha_start, self.alpha_end, self.alpha_step, self.mach)
        if any(not math.isfinite(v) for v in alphas):
            raise ValueError("Non-finite operating condition")
        if self.alpha_step <= 0 or self.alpha_end < self.alpha_start or (self.alpha_end-self.alpha_start)/self.alpha_step > 500:
            raise ValueError("Invalid angle of attack sweep")
        if not 0 <= self.mach < 1:
            raise ValueError("Mach must be in [0,1)")

def build_command(executable: Path, job: Flow5Job, output: Path) -> list[str]:
    job.validate()
    return [
        str(executable), "--naca", job.naca,
        "--reynolds", ",".join(format(v, ".12g") for v in job.reynolds),
        "--alpha-start", str(job.alpha_start),
        "--alpha-end", str(job.alpha_end),
        "--alpha-step", str(job.alpha_step),
        "--mach", str(job.mach), "--output", str(output),
    ]

def execute_job(executable: Path, job: Flow5Job, output_dir: Path, timeout_seconds: int = 600) -> dict:
    """Run an explicit trusted local executable; no shell invocation."""
    if not executable.is_file():
        raise FileNotFoundError(f"Solver executable not found: {executable}")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"naca{job.naca}.fl5"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing analysis: {output}")
    command = build_command(executable.resolve(), job, output.resolve())
    started = time.time()
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, shell=False)
    status = {
        "schema_version": 1, "solver": "flow5 XFoilBatch adapter",
        "solver_version_target": "flow5 v7.57",
        "naca": job.naca, "reynolds": list(job.reynolds),
        "alpha": [job.alpha_start, job.alpha_end, job.alpha_step],
        "mach": job.mach, "duration_seconds": round(time.time()-started, 3),
        "returncode": result.returncode,
        "output_project": str(output.resolve()) if output.is_file() else None,
        "aerodynamic_coefficients_verified": False,
        "stdout_tail": result.stdout[-5000:], "stderr_tail": result.stderr[-5000:]
    }
    (output_dir / f"naca{job.naca}.manifest.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Batch execution did not produce a valid non-empty project; see manifest in {output_dir}")
    return status
