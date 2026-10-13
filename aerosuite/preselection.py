"""Selección solo por geometría; NO estima prestaciones aerodinámicas."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Requirements:
    min_thickness_ratio: float = 0.10
    max_thickness_ratio: float = 0.18
    max_camber_ratio: float = 0.05

    def validate(self) -> None:
        if not 0 < self.min_thickness_ratio <= self.max_thickness_ratio < 1:
            raise ValueError("Invalid thickness range")
        if not 0 <= self.max_camber_ratio < 1:
            raise ValueError("Invalid maximum camber")

def evaluate_naca4(codes: list[str], req: Requirements) -> list[dict]:
    req.validate()
    results = []
    for code in codes:
        if len(code) != 4 or not code.isascii() or not code.isdigit():
            raise ValueError(f"Invalid NACA designation: {code!r}")
        camber, position, thickness = int(code[0])/100, int(code[1])/10, int(code[2:])/100
        valid = ((camber == 0 and position == 0) or (camber > 0 and position > 0)) and thickness > 0
        reasons = []
        if not valid:
            reasons.append("invalid NACA camber/thickness geometry")
        if thickness < req.min_thickness_ratio:
            reasons.append("below minimum relative thickness")
        if thickness > req.max_thickness_ratio:
            reasons.append("above maximum relative thickness")
        if camber > req.max_camber_ratio:
            reasons.append("above maximum relative camber")
        results.append({"code":code,"thickness_ratio":thickness,"camber_ratio":camber,"passes_geometry_constraints":not reasons,"reasons":reasons})
    return sorted(results, key=lambda r: (not r["passes_geometry_constraints"],r["code"]))
