"""Run setuptools."""
import pathlib

from setuptools import find_packages, setup

setup(
    name="arkprts",
    version="0.1.6",
    description="Arknights python wrapper.",
    url="https://github.com/thesadru/arkprts",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    package_data={"arkprts": ["py.typed"]},
    install_requires=["aiohttp", "pydantic"],
    extras_require={
        "all": ["aiohttp", "pydantic"],
    },
    long_description=pathlib.Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    license="MIT",
)
