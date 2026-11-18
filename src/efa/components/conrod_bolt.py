"""Connecting-rod big-end bolt joint (equations J1 to J7)."""

import math
from dataclasses import dataclass, field

from efa._checks import require_non_negative, require_positive
from efa.components.common import fmt, markdown_table, report
from efa.loads.cycle import CycleResult, EngineSpec
from efa.loads.inertia import rod_mass_split
from efa.provenance import ResultNote, Status

MPA = 1.0e6
JOINT_FIELDS = ("n_b", "A_t", "k_b", "k_m", "F_i", "S_p", "S_ut", "S_y", "S_e", "m_cap")


def _check_c(c: float) -> float:
    c = float(c)
    if not math.isfinite(c) or not 0.0 < c < 1.0:
        raise ValueError(f"Stiffness ratio C must lie in (0, 1), got {c}.")
    return c


def stiffness_ratio(k_b: float, k_m: float) -> float:
    """J1: joint stiffness ratio C = k_b / (k_b + k_m).

    Symbols:
        k_b: bolt stiffness [N/m].
        k_m: member (clamped parts) stiffness [N/m].
        C: share of the external load taken by the bolt [-], 0 < C < 1.

    Validity: linear-elastic joint before separation.
    Source: SRC-SHIGLEY (verify).
    """
    k_b = require_positive("k_b", k_b)
    k_m = require_positive("k_m", k_m)
    return k_b / (k_b + k_m)


def bolt_and_member_forces(c: float, p: float, f_i: float) -> tuple[float, float]:
    """J2: F_b = C P + F_i; F_m = (1 − C) P − F_i.

    Symbols:
        C: stiffness ratio [-].
        P: external tensile load per bolt [N], >= 0.
        F_i: preload [N], > 0.
        F_b: bolt force, tension positive [N].
        F_m: member force, tension positive (negative = clamped) [N].

    Validity: joint not separated (F_m < 0).
    Source: SRC-SHIGLEY (verify).
    """
    c = _check_c(c)
    p = require_non_negative("P", p)
    f_i = require_positive("F_i", f_i)
    return c * p + f_i, (1.0 - c) * p - f_i


def bolt_stresses(c: float, p: float, f_i: float, a_t: float) -> tuple[float, float]:
    """J3: σ_a = C P / (2 A_t); σ_m = σ_a + F_i / A_t.

    Symbols:
        C: stiffness ratio [-]; P: external load per bolt [N]; F_i: preload [N].
        A_t: tensile stress area [m²].
        σ_a, σ_m: bolt stress amplitude and mean [Pa].

    Validity: external load cycles 0 → P; nominal stresses on A_t (thread
    stress concentration is contained in the bolt endurance limit S_e).
    Source: SRC-SHIGLEY (verify).
    """
    c = _check_c(c)
    p = require_non_negative("P", p)
    f_i = require_positive("F_i", f_i)
    a_t = require_positive("A_t", a_t)
    s_a = c * p / (2.0 * a_t)
    return s_a, s_a + f_i / a_t


def proof_factor(s_p: float, a_t: float, c: float, p: float, f_i: float) -> float:
    """J4: proof-load (yield) factor n_p = S_p A_t / (C P + F_i) (verify).

    Symbols:
        S_p (s_p): proof strength [Pa]; A_t (a_t): tensile stress area [m²];
        C: stiffness ratio [-]; P: external load per bolt [N]; F_i: preload [N].
        n_p: proof-load factor [-].

    Source: SRC-SHIGLEY (verify).
    """
    s_p = require_positive("S_p", s_p)
    a_t = require_positive("A_t", a_t)
    f_b, _ = bolt_and_member_forces(c, p, f_i)
    return s_p * a_t / f_b


def separation_factor(f_i: float, p: float, c: float) -> float:
    """J5: joint separation factor n_0 = F_i / (P (1 − C)) (verify).

    Symbols:
        F_i: preload [N]; P: external load per bolt [N]; C: stiffness ratio [-].
        n_0: separation factor [-]; inf for P = 0.

    Source: SRC-SHIGLEY (verify).
    """
    f_i = require_positive("F_i", f_i)
    p = require_non_negative("P", p)
    c = _check_c(c)
    return math.inf if p == 0.0 else f_i / (p * (1.0 - c))


def bolt_fatigue_factor(
    s_e: float, s_ut: float, sigma_a: float, sigma_m: float, sigma_i: float
) -> float:
    """J6: Goodman factor along the preload load line (verify).

    n_f = S_e (S_ut − σ_i) / (S_ut σ_a + S_e (σ_m − σ_i))

    Symbols:
        S_e (s_e): fully corrected bolt endurance limit [Pa]; no Marin factors
            or K_f are applied again.
        S_ut (s_ut): bolt ultimate tensile strength [Pa].
        σ_a, σ_m: bolt stress amplitude and mean (J3) [Pa].
        σ_i (sigma_i): preload stress F_i / A_t [Pa], < S_ut.
        n_f: fatigue safety factor [-].

    Validity: load cycles 0 → P with constant preload.
    Source: SRC-SHIGLEY (verify).
    """
    s_e = require_positive("S_e", s_e)
    s_ut = require_positive("S_ut", s_ut)
    sigma_a = require_positive("sigma_a", sigma_a)
    if not sigma_i < s_ut:
        raise ValueError("Preload stress F_i/A_t must be below S_ut.")
    return s_e * (s_ut - sigma_i) / (s_ut * sigma_a + s_e * (sigma_m - sigma_i))


def bolt_external_load(
    f_rod_min: float, m_rot: float, m_cap: float, r: float, omega: float, n_b: int
) -> tuple[float, float]:
    """J7: external load per big-end bolt at TDC (verify).

    P = [|F_rod,min| + (m_rot − m_cap) r ω²] / n_b

    Symbols:
        F_rod,min (f_rod_min): most tensile rod force of the cycle [N]
            (negative in the rod sign convention); only tension loads the bolts.
        m_rot: rotating rod mass (L2) [kg].
        m_cap: big-end cap mass [kg], 0 <= m_cap < m_rot.
        r: crank radius [m]; ω (omega): angular speed [rad/s].
        n_b: number of big-end bolts [-], >= 1.
        P: external load per bolt [N].

    Validity: maximum tensile load at gas-exchange TDC; the cap's own inertia
    is carried by the cap, not by the bolts; joint face perpendicular to the
    rod axis.
    Source: SRC-SHIGLEY bolt-joint model applied to the big end (verify).

    Returns:
        (P total, P per bolt) [N].
    """
    n_b = _check_n_b(n_b)
    m_rot = require_positive("m_rot", m_rot)
    m_cap = require_non_negative("m_cap", m_cap)
    if m_cap >= m_rot:
        raise ValueError(f"m_cap ({m_cap} kg) must be less than m_rot ({m_rot} kg).")
    r = require_positive("r", r)
    omega = require_positive("omega", omega)
    tension = max(0.0, -float(f_rod_min))
    total = tension + (m_rot - m_cap) * r * omega**2
    return total, total / n_b


def _check_n_b(n_b: int) -> int:
    if int(n_b) != n_b or n_b < 1:
        raise ValueError(f"n_b must be an integer >= 1, got {n_b}.")
    return int(n_b)


@dataclass(frozen=True)
class BoltJoint:
    """Big-end bolt joint data (SI units).

    Attributes:
        n_b: number of bolts [-].
        A_t: tensile stress area per bolt [m²].
        k_b, k_m: bolt and member stiffness [N/m].
        F_i: preload per bolt [N].
        S_p, S_ut, S_y: proof, ultimate and yield strength [Pa].
        S_e: fully corrected bolt endurance limit [Pa].
        m_cap: big-end cap mass [kg].
        status: data status applied to every field without an entry in
            ``statuses``.
        statuses: per-field status overrides.
        source_id: source of the joint data, or "".
    """

    n_b: int
    A_t: float
    k_b: float
    k_m: float
    F_i: float
    S_p: float
    S_ut: float
    S_y: float
    S_e: float
    m_cap: float
    status: Status = Status.ASSUMED
    statuses: dict[str, Status] = field(default_factory=dict)
    source_id: str = ""

    def __post_init__(self) -> None:
        _check_n_b(self.n_b)
        for name in ("A_t", "k_b", "k_m", "F_i", "S_p", "S_ut", "S_y", "S_e"):
            require_positive(name, getattr(self, name))
        require_non_negative("m_cap", self.m_cap)
        if self.S_y > self.S_ut:
            raise ValueError("S_y must not exceed S_ut.")
        if self.F_i / self.A_t >= self.S_ut:
            raise ValueError("Preload stress F_i/A_t must be below S_ut.")
        object.__setattr__(self, "status", Status(self.status))
        unknown = set(self.statuses) - set(JOINT_FIELDS)
        if unknown:
            raise ValueError(f"Unknown fields in statuses: {sorted(unknown)}.")

    def status_of(self, name: str) -> Status:
        """Status of one field."""
        return Status(self.statuses.get(name, self.status))


@dataclass(frozen=True)
class BoltResult:
    """Big-end bolt assessment (SI units)."""

    F_rod_min_abs: float
    rotating_load: float
    P_total: float
    P: float
    C: float
    F_b_max: float
    F_m: float
    sigma_a: float
    sigma_m: float
    sigma_i: float
    n_p: float
    n_0: float
    n_f: float
    governing: tuple[str, float]
    inputs: tuple[tuple[str, str, str, str, str], ...]
    note: ResultNote

    def as_markdown(self) -> str:
        """Markdown report of inputs, equations, results and warnings."""
        rows = [
            ("|F_rod,min|", fmt(self.F_rod_min_abs, 9), "N"),
            ("(m_rot − m_cap) r ω²", fmt(self.rotating_load, 9), "N"),
            ("P total / per bolt", f"{fmt(self.P_total, 9)} / {fmt(self.P, 9)}", "N"),
            ("C", fmt(self.C), "-"),
            ("F_b max", fmt(self.F_b_max, 9), "N"),
            ("F_m", fmt(self.F_m, 9), "N"),
            ("σ_a / σ_m", f"{fmt(self.sigma_a / MPA)} / {fmt(self.sigma_m / MPA)}",
             "MPa"),
            ("n_p (proof)", fmt(self.n_p), "-"),
            ("n_0 (separation)", fmt(self.n_0), "-"),
            ("n_f (J6)", fmt(self.n_f), "-"),
        ]  # fmt: skip
        table = markdown_table(("Quantity", "Value", "Unit"), rows)
        gov = f"**Governing:** {self.governing[0]}, n = {fmt(self.governing[1])}"
        return report("Connecting-rod bolt assessment", self.inputs,
                      f"{table}\n\n{gov}", self.note)  # fmt: skip


def assess_bolts(cycle: CycleResult, spec: EngineSpec, joint: BoltJoint) -> BoltResult:
    """Assess the big-end bolts (J1 to J7) for the cycle of ``spec``.

    Args:
        cycle: result of evaluate_cycle for ``spec`` (0..719 grid).
        spec: engine data (rod mass split, crank radius, speed).
        joint: bolt joint data.
    """
    _, m_rot = rod_mass_split(spec.m_rod, spec.l_g, spec.rod_length)
    f_min = cycle.F_rod_max_tension
    p_total, p = bolt_external_load(f_min, m_rot, joint.m_cap, cycle.r, cycle.omega,
                                    joint.n_b)  # fmt: skip
    c = stiffness_ratio(joint.k_b, joint.k_m)
    f_b, f_m = bolt_and_member_forces(c, p, joint.F_i)
    s_a, s_m = bolt_stresses(c, p, joint.F_i, joint.A_t)
    s_i = joint.F_i / joint.A_t
    n_p = proof_factor(joint.S_p, joint.A_t, c, p, joint.F_i)
    n_0 = separation_factor(joint.F_i, p, c)
    if p > 0.0:
        n_f = bolt_fatigue_factor(joint.S_e, joint.S_ut, s_a, s_m, s_i)
    else:
        n_f = math.inf
    gov = min((("proof load", n_p), ("separation", n_0), ("fatigue (J6)", n_f)),
              key=lambda it: it[1])  # fmt: skip

    warnings = []
    if n_p < 1.0:
        warnings.append("n_p < 1: bolt load exceeds the proof load.")
    if n_0 < 1.0:
        warnings.append("n_0 < 1: joint separation; J2 to J6 no longer valid.")
    if n_f < 1.0:
        warnings.append("n_f < 1: bolt fatigue failure predicted.")
    if f_min >= 0.0:
        warnings.append("Rod is never in tension over the cycle; only the "
                        "rotating-mass load acts on the bolts.")  # fmt: skip
    validity = [
        "J7: maximum tensile load at gas-exchange TDC from the cycle plus the "
        "rotating big-end mass outside the cap ((m_rot − m_cap) r ω²).",
        "External load cycles 0 → P per bolt; preload constant (J3).",
        "S_e is the fully corrected bolt endurance limit; no Marin factors or "
        "K_f applied again (J6).",
        "J6 Goodman along the preload load line is used instead of M1–M3.",
        "Bolt bending from big-end ovalisation and joint-face slip not modelled.",
    ]
    statuses = {n: joint.status_of(n) for n in JOINT_FIELDS}
    statuses["cylinder pressure"] = cycle.note.input_statuses.get(
        "cylinder pressure", Status.ASSUMED
    )
    note = ResultNote(
        equation_ids=("L2", "J1", "J2", "J3", "J4", "J5", "J6", "J7"),
        validity_notes=tuple(validity),
        verify_flags=(
            "J1 to J7 (SRC-SHIGLEY): verify edition, equation numbers and the "
            "bolt data (S_p, S_e) against cited tables.",
        ),
        input_statuses=statuses,
        warnings=tuple(warnings),
    )
    units = {"n_b": ("-", 1.0), "A_t": ("mm²", 1e6), "k_b": ("N/m", 1.0),
             "k_m": ("N/m", 1.0), "F_i": ("kN", 1e-3), "S_p": ("MPa", 1e-6),
             "S_ut": ("MPa", 1e-6), "S_y": ("MPa", 1e-6), "S_e": ("MPa", 1e-6),
             "m_cap": ("kg", 1.0)}  # fmt: skip
    inputs = tuple(
        (n, fmt(getattr(joint, n) * units[n][1]), units[n][0],
         joint.status_of(n).value, joint.source_id)
        for n in JOINT_FIELDS
    )  # fmt: skip
    return BoltResult(
        max(0.0, -f_min), p_total - max(0.0, -f_min), p_total, p, c, f_b, f_m,
        s_a, s_m, s_i, n_p, n_0, n_f, gov, inputs, note,
    )  # fmt: skip
