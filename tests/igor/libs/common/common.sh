#!/bin/bash
# vim:set sw=2:

#
# A magic script, it looks for callable (functions) in a python file
# and defines wrappers for those files in this bash file.
# This way it's possible to call python function "natively" from bash.
#

# Wrap all top-level functions of the following module:
PYMODULE=common.common

# Prefix all wrapped functions with this string:
WRAPPER_PREFIX=igor_


# Fetches all callables (top-level functions) from a module
# These get exported
_pyc_cmds()
{
cat <<EOP | python -
import $PYMODULE
for f in $PYMODULE.__dict__:
  if callable($PYMODULE.__dict__[f]):
    print(f)
EOP
}

# Call the python function $1 with the arguments ($2, $3, …)
pyc()
{
cat <<EOP | python - "$@"
import sys
import $PYMODULE
_args = sys.argv[1:]
cmd = _args[0]
args = _args[1:]
func = $PYMODULE.__dict__[cmd]
r = func(*args)
if r is not None:
  print(r)
EOP
}


# Get all top-level callables and create wrapper for them:
for cmd in $(_pyc_cmds)
do
  eval "${WRAPPER_PREFIX}$cmd() { pyc $cmd \"\$@\" ; }"
done

[[ $0 == $BASH_SOURCE ]] && "$@"
