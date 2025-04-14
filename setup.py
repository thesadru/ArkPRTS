"""Run setuptools."""
import pathlib

from setuptools import find_packages, setup

setup(
    name="arkprts",
    version="0.3.14",
    description="Arknights python wrapper.",
    url="https://github.com/thesadru/arkprts",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    package_data={"arkprts": ["py.typed"]},
    install_requires=["aiohttp", "pydantic==2.*"],
    extras_require={
        "all": ["rsa", "pycryptodome", "UnityPy @ git+https://github.com/MooncellWiki/UnityPy@22f5d608c5c92699e83c16f04f854462f3eb2bde", "bson"],
        "rsa": ["rsa"],
        "aes": ["pycryptodome"],
        "assets": ["UnityPy @ git+https://github.com/MooncellWiki/UnityPy@22f5d608c5c92699e83c16f04f854462f3eb2bde", "pycryptodome", "bson"],
    },
    long_description=pathlib.Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    license="MIT",
)
