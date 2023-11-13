#!/bin/bash
# Script that copies files to TPV config dir, only if linting is successful

PYTHONPATH="/opt/galaxy/server/lib"
VENV="/opt/galaxy/venv"
TPV_DIR="/opt/galaxy/config/total_perspective_vortex"
GALAXY_CONF_DIR="/opt/galaxy/config"

. $VENV/bin/activate

for f in *.yml; do
        if PYTHONPATH=$PYTHONPATH tpv lint "$f"; then
                echo "lint successful, checking job_conf..."
                if grep -q "/total_perspective_vortex/$f" "$GALAXY_CONF_DIR/job_conf.yml"; then
                        echo "$f is present in job_conf, copying..."
                        [[ $(type -t cp) == "alias" ]] && unalias cp
                        cp -bu "$f" "$TPV_DIR/$f"
                else
                        echo "$f is not present in job_conf, exiting..."
                        exit 3 && true
                fi
        else
                echo "lint failed, '$f' was not copied"
                exit 3 && true
    fi
done
