#!/usr/bin/env sh
# Commit identity for this repository (local config only). Cloud sessions start from a fresh
# clone whose global config belongs to the environment, so this runs on every session start
# (.claude/settings.json → SessionStart hook). Signing is disabled because the environment's
# signing key does not belong to the maintainer's GitHub account.
set -eu
cd "$(dirname "$0")/.."
git config --local user.name "Mateus Quintão"
git config --local user.email "228027542+mrquintao@users.noreply.github.com"
git config --local commit.gpgsign false
