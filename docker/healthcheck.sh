#!/usr/bin/env sh
set -eu

# Required persistent directories must exist.
[ -d /data/tools ]
[ -d /data/templates ]
[ -d /data/users ]

# Require at least one loaded tool and template.
ls /data/tools/*.py >/dev/null 2>&1
ls /data/templates/*.md >/dev/null 2>&1

exit 0