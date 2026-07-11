#!/bin/sh
set -eu

alembic upgrade head
exec dog-excuses

