"""Mock package to install the dev requirements."""
import pathlib

import setuptools


def parse_requirements_file(path: pathlib.Path) -> list[str]:
    """Parse a requirements file into a list of requirements."""
    dependencies: list[str] = []
    for dependency in pathlib.Path(path).read_text().splitlines():
        comment_index = dependency.find("#")
        if comment_index == 0:
            continue

        if comment_index != -1:  # Remove any comments after the requirement
            dependency = dependency[:comment_index]

        if d := dependency.strip():
            dependencies.append(d)

    return dependencies


def get_normal_requirements(directory: pathlib.Path) -> list[str]:
    """Get all normal requirements in a dev requirements directory."""
    return parse_requirements_file(directory / ".." / "requirements.txt")


def get_extras(directory: pathlib.Path) -> dict[str, list[str]]:
    """Get all extras in a dev requirements directory."""
    all_extras: set[str] = set()
    extras: dict[str, list[str]] = {}

    for path in directory.glob("*.txt"):
        name = path.name.split(".")[0]

        requirements = parse_requirements_file(path)

        all_extras = all_extras.union(requirements)
        extras[name] = requirements

    extras["all"] = list(all_extras)

    return extras


dev_directory = pathlib.Path(__file__).parent
setuptools.setup(
    name="atuyka-dev",
    install_requires=["nox", *get_normal_requirements(dev_directory)],
    extras_require=get_extras(dev_directory),
)
