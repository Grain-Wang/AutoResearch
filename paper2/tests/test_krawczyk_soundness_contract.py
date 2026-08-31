from experiments.checkers import CheckerVerdict, pointwise_krawczyk
from experiments.interval_backend import Interval


def test_old_singular_c_counterexample_cannot_accept() -> None:
    # F(x)=x+2 has no root in [-1,1].  The old contract permitted a producer to
    # choose C=0 and obtain K={0}.  The executable checker derives C from J=1,
    # obtains K={-2}, and therefore cannot accept.
    result = pointwise_krawczyk(
        (0.0,),
        (Interval(-1.0, 1.0),),
        (Interval.point(2.0),),
        ((Interval.point(1.0),),),
    )
    assert result.verdict is CheckerVerdict.UNKNOWN


def test_singular_midpoint_operator_is_unsupported() -> None:
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
