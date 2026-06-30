"""nox build configuration for Documenteer."""

import os
import shutil
from pathlib import Path

import nox
from nox_uv import session

# Default sessions (run when nox is invoked without -s) stay lean: lint, the
# Sphinx 8/9 test runs on the latest supported Python, Sphinx 8 typing, and a
# docs build. The full Python x Sphinx grid (and the Sphinx "dev" runs) are
# opt-in via ``nox -s test`` / ``nox -s typing``.
nox.options.sessions = [
    "lint",
    "typing-3.13(sphinx='8')",
    "test-3.13(sphinx='8')",
    "test-3.13(sphinx='9')",
    "docs",
]

# Other nox defaults
nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

# Extras carrying the Sphinx themes and extensions for guides and technotes.
# These cover everything needed to test, type-check, and build the docs.
_EXTRAS = ["guide", "technote"]

# The three demo technote projects built by the ``demo`` session.
_DEMOS = ["rst-technote", "md-technote", "ipynb-technote"]

# Map each Sphinx parametrize ID to the pip requirement that overrides the
# Sphinx version resolved from uv.lock in the session environment.
_SPHINX_SPECS = {
    "8": "sphinx==8.*",
    "9": "sphinx==9.*",
    "dev": "git+https://github.com/sphinx-doc/sphinx.git#egg=sphinx",
}


def _override_sphinx(session: nox.Session, sphinx: str) -> None:
    """Install a specific Sphinx version over the resolved environment.

    nox_uv installs the project with the locked Sphinx; this then pins the
    parametrized Sphinx version on top via ``uv pip install``, reproducing the
    per-factor ``deps`` of the old tox test/typing environments.
    """
    session.install(_SPHINX_SPECS[sphinx])


@session(uv_only_groups=["lint"], uv_no_install_project=True)
def lint(session: nox.Session) -> None:
    """Run the prek hooks (incl. the prettier web-asset hook)."""
    session.run("prek", "run", "--all-files", *session.posargs)


@session(python=["3.12", "3.13"], uv_groups=["test"], uv_extras=_EXTRAS)
@nox.parametrize("sphinx", ["8", "9", "dev"])
def test(session: nox.Session, sphinx: str) -> None:
    """Run the test suite with pytest.

    Coverage is opt-in: set the ``DOCUMENTEER_COVERAGE`` environment variable
    to run under coverage and emit a combined report after the test sessions.
    In CI, where each matrix cell uploads its raw ``.coverage.*`` for a central
    combine job, also set ``DOCUMENTEER_COVERAGE_NO_COMBINE`` to skip the
    per-invocation combine and preserve the un-combined data files.
    """
    _override_sphinx(session, sphinx)
    if os.environ.get("DOCUMENTEER_COVERAGE"):
        session.run("coverage", "run", "-m", "pytest", *session.posargs)
        if not os.environ.get("DOCUMENTEER_COVERAGE_NO_COMBINE"):
            session.notify("coverage-report")
    else:
        session.run("pytest", *session.posargs)


@session(python=["3.12", "3.13"], uv_groups=["typing"], uv_extras=_EXTRAS)
@nox.parametrize("sphinx", ["8", "9", "dev"])
def typing(session: nox.Session, sphinx: str) -> None:
    """Check type annotations with mypy."""
    _override_sphinx(session, sphinx)
    session.run("mypy", "src", "tests", *session.posargs)


@session(
    name="coverage-report", uv_only_groups=["test"], uv_no_install_project=True
)
def coverage_report(session: nox.Session) -> None:
    """Combine and report coverage from the test sessions.

    Triggered automatically after the ``test`` sessions when
    ``DOCUMENTEER_COVERAGE`` is set; may also be run directly to re-display the
    most recent combined report.
    """
    if list(Path.cwd().glob(".coverage.*")):
        session.run("coverage", "combine")
    session.run("coverage", "report")


@session(uv_groups=["docs"], uv_extras=_EXTRAS)
def docs(session: nox.Session) -> None:
    """Build the Sphinx documentation."""
    if Path("docs/_build").exists():
        shutil.rmtree("docs/_build")
    if Path("docs/dev/api/contents").exists():
        shutil.rmtree("docs/dev/api/contents")
    session.run("make", "-C", "docs", "html", external=True)


@session(name="docs-linkcheck", uv_groups=["docs"], uv_extras=_EXTRAS)
def docs_linkcheck(session: nox.Session) -> None:
    """Check links in the Sphinx documentation."""
    session.run("make", "-C", "docs", "linkcheck", external=True)


@session(python=["3.12", "3.13"], uv_groups=["test"], uv_extras=_EXTRAS)
@nox.parametrize("sphinx", ["8", "9", "dev"])
def demo(session: nox.Session, sphinx: str) -> None:
    """Build the demo technote projects as an end-to-end smoke test.

    Parametrized over Python and Sphinx like ``test``/``typing`` so the demo
    build is exercised across the full matrix in CI.
    """
    _override_sphinx(session, sphinx)
    for demo_name in _DEMOS:
        build_dir = Path("demo") / demo_name / "_build"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        doctree_dir = (session.cache_dir / "doctrees" / demo_name).absolute()
        session.run(
            "sphinx-build",
            "--keep-going",
            "-n",
            "-W",
            "-T",
            "-b",
            "html",
            "-d",
            str(doctree_dir),
            f"demo/{demo_name}",
            f"demo/{demo_name}/_build/html",
        )


@nox.session(name="packaging")
def packaging(session: nox.Session) -> None:
    """Check the PyPI package build with twine."""
    if Path("dist").exists():
        shutil.rmtree("dist")
    session.install("build", "twine")
    session.run("python", "-m", "build")
    session.run("twine", "check", *[str(p) for p in Path("dist").glob("*")])


@nox.session(name="scriv-create")
def scriv_create(session: nox.Session) -> None:
    """Create a changelog fragment."""
    session.install("scriv")
    session.run("scriv", "create")


@nox.session(name="scriv-collect")
def scriv_collect(session: nox.Session) -> None:
    """Collect changelog fragments into the changelog."""
    session.install("scriv")
    session.run("scriv", "collect", "--add", "--version", *session.posargs)
