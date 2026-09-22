#!/usr/bin/env bash
# One-shot setup for the Research Matching Chatbot.
#
# Creates a virtual environment, installs the dependencies, and drops a .env
# file you can fill in later. Everything here is also written out step by step
# in the README under "Getting Started" — this just runs it in one go.
#
#   bash setup.sh
#
# Then start the app with `python main.py` (terminal) or `python app_gradio.py`
# (web). The app runs even without API keys, so filling in .env is optional.

set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

echo "==> Creating virtual environment in .venv"
if [ ! -d .venv ]; then
    "$PY" -m venv .venv
else
    echo "    .venv already exists, reusing it."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --quiet --upgrade pip

echo "==> Installing dependencies from requirements.txt"
python -m pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
    echo "==> Creating .env from .env.example"
    cp .env.example .env
    echo "    Add your keys to .env when you want live LLM, web trends, or email."
    echo "    You can skip this for now — the app still runs without any keys."
else
    echo "==> .env already present, leaving it as is."
fi

echo
echo "All set. To run it:"
echo "    source .venv/bin/activate"
echo "    python main.py          # terminal app"
echo "    python app_gradio.py    # web app at http://127.0.0.1:7860"
