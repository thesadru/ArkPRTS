"""Nox file."""

from __future__ import annotations

import logging
import pathlib
import typing

import nox
from nox.command import CommandFailed

nox.options.sessions = ["reformat", "lint", "type-check", "verify-types", "test", "prettier"]
nox.options.reuse_existing_virtualenvs = True
PACKAGE = "arkprts"
GENERAL_TARGETS = ["./arkprts", "./tests", "./noxfile.py"]
PRETTIER_TARGETS = ["*.md"]
PYRIGHT_ENV = {"PYRIGHT_PYTHON_FORCE_VERSION": "latest"}

LOGGER = logging.getLogger("nox")


def isverbose() -> bool:
    """Whether the verbose flag is set."""
    return LOGGER.getEffectiveLevel() == logging.DEBUG - 1


def verbose_args() -> typing.Sequence[str]:
    """Return --verbose if the verbose flag is set."""
    return ["--verbose"] if isverbose() else []


def install_requirements(session: nox.Session, *requirements: str, literal: bool = False) -> None:
    """Install requirements."""
    if not literal and all(requirement.isalpha() for requirement in requirements):
        files = ["requirements.txt"]
        files += [f"./dev-requirements/{requirement}.txt" for requirement in requirements]
        requirements = tuple(arg for file in files for arg in ("-r", file))

    session.install("--upgrade", "pip", *requirements, silent=not isverbose())


@nox.session()
def lint(session: nox.Session) -> None:
    """Run this project's modules against ruff."""
    install_requirements(session, "lint")
    session.run("python", "-m", "ruff", "check", *GENERAL_TARGETS, *verbose_args())
    session.run("python", "-m", "slotscheck", "-m", PACKAGE, *verbose_args())


@nox.session()
def reformat(session: nox.Session) -> None:
    """Reformat this project's modules to fit the standard style."""
    install_requirements(session, "reformat")
    session.run("python", "-m", "black", *GENERAL_TARGETS, *verbose_args())
    session.run("python", "-m", "ruff", "check", "--fix-only", "--fixable", "ALL", *GENERAL_TARGETS, *verbose_args())

    session.log("sort-all")
    LOGGER.disabled = True
    session.run("sort-all", *map(str, pathlib.Path(PACKAGE).glob("**/*.py")), success_codes=[0, 1])
    LOGGER.disabled = False


@nox.session(name="test")
def test(session: nox.Session) -> None:
    """Run this project's tests using pytest."""
    install_requirements(session, "pytest")

    args: typing.Sequence[str] = []

    if isverbose():
        args += ["-vv", "--showlocals", "-o", "log_cli=true", "-o", "log_cli_level=DEBUG"]

    session.run(
        "python",
        "-m",
        "pytest",
        "-r",
        "sfE",
        *verbose_args(),
        *args,
        *session.posargs,
        success_codes=[0, 5],
    )


@nox.session(name="type-check")
def type_check(session: nox.Session) -> None:
    """Statically analyse and veirfy this project using pyright and mypy."""
    install_requirements(session, "typecheck")
    session.run("pyright", PACKAGE, *verbose_args(), env=PYRIGHT_ENV)


@nox.session(name="verify-types")
def verify_types(session: nox.Session) -> None:
    """Verify the "type completeness" of types exported by the library using pyright."""
    install_requirements(session, ".", "--force-reinstall", "--no-deps")
    install_requirements(session, "typecheck")

    session.run("pyright", "--verifytypes", PACKAGE, "--ignoreexternal", *verbose_args(), env=PYRIGHT_ENV)


def _try_install_prettier(session: nox.Session) -> bool:
    """Try to install prettier. Return False if failed."""
    if session._runner.global_config.no_install:
        return True

    try:
        session.run("npm", "install", "prettier", "--global", external=True)
    except CommandFailed as exception:
        if exception.reason != "Program npm not found":
            raise
    else:
        return True

    return False


@nox.session(python=False)
def prettier(session: nox.Session) -> None:
    """Run prettier on markdown files."""
    if not _try_install_prettier(session):
        session.skip("Prettier not installed")

    session.run("prettier", "-w", *PRETTIER_TARGETS, external=True)
