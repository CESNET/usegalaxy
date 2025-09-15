#!/bin/env bash

set -e

FROM=$1
TO=$2
LIST=/tmp/dirs_to_move.$$

cd "${FROM}"
find shed_tools/ -mindepth 7 -maxdepth 7 -type d \( -name '.hg' -o -name 'test-data' \) > ${LIST}

cat ${LIST} | while read DIR; do
    if [ -n "$DIR" ]; then
        SRC="$FROM/$DIR";
        TARGET="$TO/$DIR";
        echo "moving $SRC -> $TARGET";
        rsync -av --mkpath "$SRC/" "$TARGET" && rm -rf "$SRC" && ln -s "$TARGET" "$SRC" || echo "rsync must failed, directory is missing!";
    else
        echo "line is empty!"
    fi
done
