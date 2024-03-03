"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    import sphinx.application
    from autoapi.mappers.python import objects as autoapi_objects


# -- Project information -----------------------------------------------------

project = "arkprts"

# -- General configuration ---------------------------------------------------

extensions = [
    # Sphinx own extensions
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    # Docs generation
    "autoapi.extension",
    "numpydoc",
    "myst_parser",
]

default_role = "py:obj"

# -- HTML output --------------------------------------------------------------

# originally we would use sphinx_material but that's broken af
html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/thesadru/arkprts",
    "source_branch": "master",
}
html_show_sourcelink = False


# -- AutoAPI options ----------------------------------------------------------

autoapi_root = "reference"
autoapi_dirs = ["../arkprts"]
autoapi_ignore = ["__main__.py"]

autoapi_options = ["members", "special-members"]

autoapi_add_toctree_entry = False
autoapi_keep_files = True

# -- AutoDoc options ----------------------------------------------------------

autodoc_typehints = "signature"
autodoc_class_signature = "separated"
autodoc_preserve_defaults = True
autoclass_content = "both"

# -- Intersphinx options ------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}


def skip_member(
    app: sphinx.application.Sphinx,
    what: typing.Literal["attribute", "class", "data", "exception", "function", "method", "module", "package"],
    name: str,
    obj: autoapi_objects.PythonPythonMapper,
    skip: bool,
    options: typing.Sequence[str],
) -> bool:
    """Decide what members to skip during autoapi collection."""
    sname = name.split(".")[-1]

    if sname.startswith("__") and sname.endswith("__"):
        if what == "method":
            return True
        if what == "attribute" and sname == "__slots__":
            return True

    if what == "module" and sname == "__main__":
        return True

    return skip


def setup(sphinx: sphinx.application.Sphinx) -> None:
    """Sphinx setup entry point."""
    sphinx.connect("autoapi-skip-member", skip_member)  # pyright: ignore[reportUnknownMemberType]
