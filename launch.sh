#!/usr/bin/env bash
set -euo pipefail

directory=$(dirname -- "$0")
dms=$1
shift

# A package update can change the QML API without changing the version string.
if [[ -r "$directory/ui/shell.qml" && -r "$directory/dms.sha256" ]] &&
    checksum=$(sha256sum < "$dms") &&
    [[ ${checksum%% *} == "$(<"$directory/dms.sha256")" ]]; then
    exec "$dms" --config "$directory/ui" "$@"
fi
exec "$dms" "$@"
