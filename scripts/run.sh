#!/bin/bash

export PYTHONPATH="${PYTHONPATH}:/bot:/bot/src"
cd src

poetry run python run.py
