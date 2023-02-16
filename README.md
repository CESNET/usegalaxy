# usegalaxy

Simple galaxy installation steps.

On fresh install of ubuntu:
```
sudo apt-get update
sudo apt-get upgrade -y
sudo apt update
sudo apt upgrade
sudo apt install software-properties-common
sudo apt-add-repository --yes --update ppa:ansible/ansible
sudo apt install ansible
```

Clone the repo and instal requireded galaxy roles.
```
git clone https://github.com/CESNET/usegalaxy.git
cd usegalaxy
ansible-galaxy install -p roles -r requirements.yml
```

After the instalation, you should configure your [inventory file](https://training.galaxyproject.org/training-material/topics/admin/tutorials/ansible/tutorial.html#inventory-file).

```NGINX``` is configured to run without SSL, see [guide](https://training.galaxyproject.org/training-material/topics/admin/tutorials/ansible-galaxy/tutorial.html#nginx) on how to configure it to use SSL.

Once everything have been installed, and hosts configured, the ansible playbook can be run as follows:
```
ansible-playbook galaxy.yml
```

## Found bugs

On ubuntu 20.04 the GLIBC version is incompatible with the ```galaxyproject.tusd``` GLIBC, therfore playbook ends in error.

