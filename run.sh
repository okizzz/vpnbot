#!/bin/sh

set -e

python3 bot.py "-docker" &
python3 vpns.py
