from experiments.checkers import CheckerVerdict, pointwise_krawczyk
from experiments.interval_backend import (
    Interval,
    IntervalResult,
    IntervalStatus,
    add,
    multiply,
    subtract,
)


def _require_interval(result: IntervalResult) -> Interval:
    assert result.status is IntervalStatus.OK
    assert result.interval is not None
    return result.interval


def _arbitrary_scalar_krawczyk_image(
    center: float,
    tube: Interval,
    residual: Interval,
    jacobian: Interval,
    preconditioner: float,
) -> Interval:
    """Evaluate the scalar Krawczyk formula for an independently chosen C."""

    c_interval = Interval.point(preconditioner)
    centered_tube = _require_interval(subtract(tube, Interval.point(center)))
    c_residual = _require_interval(multiply(c_interval, residual))
    base = _require_interval(subtract(Interval.point(center), c_residual))
    c_jacobian = _require_interval(multiply(c_interval, jacobian))
    linear_operator = _require_interval(subtract(Interval.point(1.0), c_jacobian))
    linear_image = _require_interval(multiply(linear_operator, centered_tube))
    return _require_interval(add(base, linear_image))


def test_zero_preconditioner_image_equals_tube_and_is_not_strict() -> None:
    tube = Interval(-1.0, 1.0)
    image = _arbitrary_scalar_krawczyk_image(
        center=0.0,
        tube=tube,
        residual=Interval.point(2.0),
        jacobian=Interval.point(1.0),
        preconditioner=0.0,
    )

    assert image == tube
    assert not (tube.lower < image.lower and image.upper < tube.upper)


def test_frozen_inverse_profile_rejects_root_excluding_tube() -> None:
    # F(x)=x+2 has no root in [-1,1].  The executable checker uses its frozen
    # implementation profile C=M^{-1}; with M=1 it obtains K={-2} and cannot
    # accept.  This test checks the restricted profile, not a theorem premise.
    result = pointwise_krawczyk(
        (0.0,),
        (Interval(-1.0, 1.0),),
        (Interval.point(2.0),),
        ((Interval.point(1.0),),),
    )
    assert result.verdict is CheckerVerdict.UNKNOWN


def test_singular_midpoint_operator_is_unsupported() -> None:
    # Failing closed when M is singular is a checker-profile decision: this
    # implementation does not expose arbitrary C even though the theorem does.
    result = pointwise_krawczyk(
        (0.0,),
        (Interval(-1.0, 1.0),),
        (Interval.point(2.0),),
        ((Interval.point(0.0),),),
    )
    assert result.verdict is CheckerVerdict.UNSUPPORTED
    assert result.reason is not None
    assert "nonsingular" in result.reason


def test_affine_root_strictly_inside_tube_is_accepted() -> None:
    result = pointwise_krawczyk(
        (0.0,),
        (Interval(-1.0, 1.0),),
        (Interval.point(-0.25),),
        ((Interval.point(1.0),),),
    )
    assert result.verdict is CheckerVerdict.ACCEPT
    assert result.image is not None
    assert result.image[0].contains(0.25)


def test_center_on_tube_boundary_is_not_a_valid_theorem_instance() -> None:
    result = pointwise_krawczyk(
        (-1.0,),
        (Interval(-1.0, 1.0),),
        (Interval.point(-1.25),),
        ((Interval.point(1.0),),),
    )
    assert result.verdict is CheckerVerdict.UNSUPPORTED
