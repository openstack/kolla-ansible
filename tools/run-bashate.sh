#!/usr/bin/env bash

# Ignore E006 -- line length greater than 80 char
# Error on E005 -- file does not begin with #! or have .sh prefix
# Error on E042 -- local declaration hides errors
# Error on E043 -- arithmetic compound has inconsistent return semantics

ROOT=$(readlink -fn $(dirname $0)/.. )
find $ROOT -not -wholename \*.tox/\* -and -not -wholename \*.test/\* \
    -and -name \*.sh -print0 | xargs -0 bashate -v --ignore E006 --error E005,E042,E043
