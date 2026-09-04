import random

from experiments.devices import (
    DiodeParameters,
    MosParameters,
    MosRegion,
    SmoothNmosParameters,
    diode_interval,
    diode_point,
    mos_interval,
    mos_point,
    smooth_nmos_interval,
    smooth_nmos_point,
)
from experiments.interval_backend import Interval


def test_diode_random_bias_boxes_contain_values_and_derivatives() -> None:
    generator = random.Random(43)
    parameters = DiodeParameters()
    for _ in range(1_000):
        center = generator.uniform(-1.0, 0.75)
        radius = generator.uniform(0.0, 0.02)
        box = Interval(center - radius, center + radius)
        stamp = diode_interval(box, parameters)
        assert stamp is not None
        for index in range(11):
            voltage = box.lower + index * (box.upper - box.lower) / 10.0
            current, conductance = diode_point(voltage, parameters)
            assert stamp.current.contains(current)
            assert stamp.conductance.contains(conductance)


def test_mos_random_smooth_region_boxes_contain_values_and_derivatives() -> None:
    generator = random.Random(71)
    parameters = MosParameters()
    seen = {region: 0 for region in MosRegion}
    while min(seen.values()) < 1_000:
        region = min(seen, key=seen.get)
        if region is MosRegion.CUTOFF:
            vgs = Interval(generator.uniform(-0.5, 0.2), generator.uniform(0.2, 0.49))
            vds = Interval(generator.uniform(0.0, 0.2), generator.uniform(0.2, 1.5))
        elif region is MosRegion.TRIODE:
            low_vgs = generator.uniform(0.7, 1.2)
            high_vgs = low_vgs + generator.uniform(0.01, 0.1)
            high_vds = generator.uniform(0.01, low_vgs - parameters.threshold - 0.01)
            vgs = Interval(low_vgs, high_vgs)
            vds = Interval(0.0, high_vds)
        else:
            low_vgs = generator.uniform(0.6, 1.0)
            high_vgs = low_vgs + generator.uniform(0.01, 0.1)
            low_vds = high_vgs - parameters.threshold + generator.uniform(0.0, 0.1)
            vgs = Interval(low_vgs, high_vgs)
            vds = Interval(low_vds, low_vds + generator.uniform(0.01, 0.2))
        stamp = mos_interval(vgs, vds, parameters)
        assert stamp is not None
        assert stamp.region is region
        for _ in range(5):
            point_vgs = generator.uniform(vgs.lower, vgs.upper)
            point_vds = generator.uniform(vds.lower, vds.upper)
            current, gm, gds, point_region = mos_point(point_vgs, point_vds, parameters)
            assert point_region is region
            assert stamp.drain_current.contains(current)
            assert stamp.transconductance.contains(gm)
            assert stamp.output_conductance.contains(gds)
        seen[region] += 1


def test_mos_boundary_crossing_returns_unknown() -> None:
    parameters = MosParameters()
    assert mos_interval(Interval(0.49, 0.51), Interval(0.0, 0.1), parameters) is None
    assert mos_interval(Interval(0.9, 1.0), Interval(0.3, 0.6), parameters) is None
    assert mos_interval(Interval(0.9, 1.0), Interval(-0.1, 0.1), parameters) is None


def test_smooth_nmos_boxes_contain_current_and_derivatives() -> None:
    generator = random.Random(109)
    parameters = SmoothNmosParameters()
    for _ in range(1_000):
        gate_center = generator.uniform(-0.2, 1.3)
        drain_center = generator.uniform(-0.1, 1.3)
        gate_radius = generator.uniform(0.0, 0.03)
        drain_radius = generator.uniform(0.0, 0.03)
        vgs = Interval(gate_center - gate_radius, gate_center + gate_radius)
        vds = Interval(drain_center - drain_radius, drain_center + drain_radius)
        stamp = smooth_nmos_interval(vgs, vds, parameters)
        assert stamp is not None
        for index in range(11):
            point_vgs = vgs.lower + index * (vgs.upper - vgs.lower) / 10.0
            point_vds = vds.upper - index * (vds.upper - vds.lower) / 10.0
            current, gm, gds = smooth_nmos_point(point_vgs, point_vds, parameters)
            assert stamp.drain_current.contains(current)
            assert stamp.transconductance.contains(gm)
            assert stamp.output_conductance.contains(gds)
