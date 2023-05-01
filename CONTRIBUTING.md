# arkprts contributing guide

## Setting up the environment

Set up a virtual environment - [venv](https://docs.python.org/3/library/venv.html) is recommended - and install the dev dependencies.

```sh
python -m venv .venv
source .venv/bin/activate

pip install ./dev-requirements[all]
```

### VSCode

Install the following extensions:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)
- [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)

`.vscode/settings.json`

```json
{
  "editor.formatOnSave": true,
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.formatting.provider": "black",
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.fixAll": true
    }
  }
}
```

### PyCharm

`¯\_(ツ)_/¯`

## Pipelines

CI is run using [`nox`](https://nox.thea.codes/). Before creating a PR make sure all default pipelines have passed.

### How to use nox

Nox must be downloaded with `pip install nox`.

You can run all default pipelines with just `nox` or specific ones with `nox -s foo bar`. To see all available pipelines run `nox -l`.

If you have a slow connection use `nox --no-install` to skip installing dependencies.

## Style-guide

Formatting is done by [black](https://github.com/psf/black) and is checked by [ruff](https://github.com/charliermarsh/ruff). The project loosely follows [pep8](https://www.python.org/dev/peps/pep-0008/), but anything that is not covered by black or ruff is up to the developer.

Refer to [pyright's type-completness guidelines](https://github.com/microsoft/pyright/blob/main/docs/typed-libraries.md) and [standard typing library's type-completness guidelines](https://github.com/python/typing/blob/master/docs/libraries.md) to see how to properly type your code.
