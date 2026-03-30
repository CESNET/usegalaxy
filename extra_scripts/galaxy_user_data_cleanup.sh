#!/bin/bash
source {{ galaxy_venv_dir }}/bin/activate
GALAXY_LOG_DIR={{ galaxy_mutable_data_dir }}/log/gxadmin/ GALAXY_ROOT={{ galaxy_root }}/server GALAXY_CONFIG_FILE={{ galaxy_config_file }} /usr/local/bin/gxadmin galaxy cleanup $1
