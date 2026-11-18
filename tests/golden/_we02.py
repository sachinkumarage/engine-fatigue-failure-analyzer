"""WE-02 engine and cycle shared by the component worked examples."""

from functools import cache

from efa.loads.cycle import EngineSpec, evaluate_cycle
from efa.loads.gas import PressureTable
from efa.provenance import Status
from efa.units import bar_to_pa

ANGLES = [0, 180, 300, 340, 360, 370, 380, 400, 450, 540, 720]
P_BAR = [1.0, 1.0, 5.0, 25.0, 45.0, 60.0, 50.0, 30.0, 10.0, 3.0, 1.0]


def we02_spec() -> EngineSpec:
    table = PressureTable(ANGLES, bar_to_pa(P_BAR), "WE-02", Status.ASSUMED)
    return EngineSpec(
        bore=0.086, stroke=0.086, rod_length=0.143, speed_rpm=4000.0,
        m_piston=0.40, m_pin=0.10, m_rings=0.03, m_rod=0.55, l_g=0.040,
        p_crankcase=101325.0, pressure_table=table,
    )  # fmt: skip


@cache
def we02_cycle():
    return evaluate_cycle(we02_spec())
