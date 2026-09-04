from experiments.rigorous_backend import backend_info


def test_mpfr_system_library_is_version_4_2_or_newer() -> None:
    info = backend_info()
    assert info is not None
    version = tuple(int(part) for part in info.version.split(".")[:2])
    assert version >= (4, 2)
    assert info.library.startswith("libmpfr")
