# usegalaxy

Simple galaxy installation steps.

On fresh install of ubuntu:
```
sudo apt-get update
sudo apt-get upgrade -y
sudo apt update
sudo apt upgrade -y
sudo apt install -y software-properties-common
sudo apt-add-repository --yes --update ppa:ansible/ansible
sudo apt install -y ansible
```

Clone the repo and instal required galaxy roles.
```
git clone https://github.com/CESNET/usegalaxy.git
cd usegalaxy
ansible-galaxy install -p roles -r requirements.yml --force
```
Note that the roles are already present in this repo.

After the instalation, you should configure your [inventory file](https://training.galaxyproject.org/training-material/topics/admin/tutorials/ansible/tutorial.html#inventory-file) ([hosts](https://github.com/CESNET/usegalaxy/blob/main/hosts)) and set up a vault:
```
openssl rand -base64 24 > .vault-password.txt
ansible-vault create group_vars/secret.yml
```
The second command opens an editor wherein you should define variables eg.:
```
vault_id_secret: "a-long-random-value"
rabbitmq_users_password:
  mqadmin: "a-long-random-value"
  galaxy: "a-long-random-value"
  galaxy_gpu: "a-long-random-value"
```
The value should be a long random value, which can be obtained by command `openssl rand -base64 24`, though you should avoid having a `/` or `\` in your password as galaxy will interpret this as a path.

Make sure you have these ports enabled on your machine:
```
80(HTTP)
443(HTTPS)
4369(TCP)
5671(TCP)
15672(TCP)
25672(TCP)
```

Once everything have been installed and configured, the ansible playbook can be run as follows:
```
ansible-playbook galaxy.yml
```

## Usegalaxy tools

Install ephemeris for tool management:
```
virtualenv -p python3 ~/ephemeris_venv
. ~/ephemeris_venv/bin/activate
pip install ephemeris
```
To obtain the list of tools from the [usegalaxy.eu](https://usegalaxy.eu) use:
```
get-tool-list -g "https://usegalaxy.eu" -o "eu_tool_list.yaml"
```
and then to install them:
```
shed-tools install -g https://your-galaxy -a <api-key> -t eu_tool_list.yaml
```
The api key can be found in the User -> Preferences -> Manage API Key in Galaxy menu.

...

Later we should use this [role](https://github.com/galaxyproject/ansible-galaxy-tools) to automate this, but there are too many tools to be installed and it is very inpractical for testing purposes. 

## Notes

On ubuntu < 22.04 and Debian < 12 the GLIBC version is incompatible with the ```galaxyproject.tusd``` GLIBC, therfore playbook ends in error.
- in `roles/galaxyproject.tusd/defaults/main.yml` you have to set the `tusd_version:` to 'v1.6.0' (tested, possibly higher)

# Debian 11

On Debian 11 the default version of `ansible` is 2.10.08 which fails to extract binaries for TUSd.
- workaround: 
  - `sudo vim /etc/apt/sources.list` add this line : `deb http://ppa.launchpad.net/ansible/ansible/ubuntu focal main`
  - then `sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 93C4A3FD7BB9C367`
  - followed by `sudo apt-get update` and `sudo apt-get install ansible -y`
- Note that you might need to `sudo apt remove ansible` `sudo apt autoremove` before you try to install ansible.

Use `sudo apt install python3-docker` before running the `usegalaxy.rabbitmqserver` role.

