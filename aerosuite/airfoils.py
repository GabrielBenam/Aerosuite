"""Geometría de perfiles NACA de cuatro dígitos; sin predicción aerodinámica."""
from __future__ import annotations
import csv
import math
from pathlib import Path

def naca4(code: str, n: int = 81, closed_te: bool = True) -> list[tuple[float, float]]:
    """Puntos TE superior -> LE -> TE inferior; 2*n-1 coordenadas normalizadas."""
    if len(code) != 4 or not code.isascii() or not code.isdigit():
        raise ValueError("NACA code must contain exactly four ASCII digits")
    m, p, t = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    if (m == 0 and p != 0) or (m > 0 and p == 0) or t <= 0:
        raise ValueError("Invalid NACA designation")
    return naca4_mpt(m, p, t, n, closed_te)


def naca4_mpt(m: float, p: float, t: float, n: int = 81, closed_te: bool = True) -> list[tuple[float, float]]:
    """NACA 4-digit family with continuous parameters (max camber m, its position p, thickness t; fractions of chord).

    Same thickness and camber-line equations as naca4(); used by the 2D optimizer so that
    m, p, t can vary continuously. Reference: Sobester & Forrester, Ch. 6 (NACA four-digit section).
    """
    if n < 5:
        raise ValueError("n must be >= 5")
    if not (0 <= m < 0.2 and 0 < t < 0.5) or (m > 0 and not 0 < p < 1):
        raise ValueError("Invalid NACA parameters")
    upper, lower = [], []
    a4 = -0.1036 if closed_te else -0.1015
    for i in range(n):
        x = (1 - math.cos(math.pi * i / (n - 1))) / 2
        yt = 5*t*(0.2969*math.sqrt(x)-0.1260*x-0.3516*x*x+0.2843*x**3+a4*x**4)
        if m == 0:
            yc = dyc = 0.0
        elif x < p:
            yc = m/(p*p)*(2*p*x-x*x)
            dyc = 2*m/(p*p)*(p-x)
        else:
            yc = m/((1-p)**2)*((1-2*p)+2*p*x-x*x)
            dyc = 2*m/((1-p)**2)*(p-x)
        theta = math.atan(dyc)
        upper.append((x-yt*math.sin(theta), yc+yt*math.cos(theta)))
        lower.append((x+yt*math.sin(theta), yc-yt*math.cos(theta)))
    return list(reversed(upper)) + lower[1:]


def write_csv(code: str, output: Path, n: int = 81) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["x_over_c", "y_over_c"])
        writer.writerows((f"{x:.9f}", f"{y:.9f}") for x, y in naca4(code, n))

def write_dat(code: str, output: Path, n: int = 81) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="\n", encoding="utf-8") as handle:
        handle.write(f"NACA {code}\n")
        for x, y in naca4(code, n):
            handle.write(f"{x:.9f} {y:.9f}\n")
