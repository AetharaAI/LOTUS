Venv & Running LOTUS
====================

Problems where different terminals don't have the venv activated can be avoided by using the provided helper script `run_lotus.sh`.

Quick start (zsh):

```zsh
# create venv if you haven't already
python3 -m venv venv
source venv/bin/activate
pip install -r lotus/requirements.txt

# start nucleus with venv activated (recommended)
./run_lotus.sh

# or run a specific command inside the venv
./run_lotus.sh python3 lotus/cli.py chat "hello"
```

The helper activates `./venv` if present and then runs the requested command. This prevents confusion when opening new terminals.
