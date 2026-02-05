# TPV Auto Lint
Ansible role to create a script that automatically lints all YAML files in the `tpv_mutable_dir` and checks for their existence in Galaxy's `job_conf.yml`. If both applies, it copies the file to the TPV rules directory, updating existing files.
This leads to a automatic reload, if Galaxy watches this directory.
With this script, TPV in Galaxy's job handlers can't break anymore. Which would otherwise lead to mostly undetected destination mapping failures.

## Requirements
 - Ansible >= 2.11  
 - [galaxyproject.galaxy](https://galaxy.ansible.com/galaxyproject/galaxy) for TPV and the `galaxy_*` vars

## Role Variables
See [defaults/main](./default/main.yml) or galaxy's [default/main](https://github.com/galaxyproject/ansible-galaxy/blob/main/defaults/main.yml)
## Playbook Example
Include role in your Galaxyserver Playbook **after** the galaxyproject.galaxy role (the dirs have to exist already)
## License
GPLv3
## Author Information
[Galaxy Europe](https://galaxyproject.org/eu/)