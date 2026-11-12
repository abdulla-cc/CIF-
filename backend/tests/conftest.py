import pytest

from cif.eval.detection import serve


@pytest.fixture(scope="session")
def site_url():
    """Serve testsite/ on a free local port for the whole test session."""
    with serve() as url:
        yield url
