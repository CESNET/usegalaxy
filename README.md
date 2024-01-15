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
ansible-galaxy install -p roles -r requirements.yml
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

## Debian 11

### TUS

On ubuntu < 22.04 and Debian < 12 the GLIBC version is incompatible with the ```galaxyproject.tusd``` GLIBC, therfore playbook ends in error.
- in `roles/galaxyproject.tusd/defaults/main.yml` you have to set the `tusd_version:` to 'v1.8.0' (tested, possibly higher)

### Ansible

On Debian 11 the default version of `ansible` is 2.10.08 which fails to extract binaries for TUSd.
- workaround:
  - because of Puppet, we need to create dedicated sources.list file for ansible
  - `sudo vim /etc/apt/sources.list.d/ansible_ubuntu_focal_main.list` add this line : `deb http://ppa.launchpad.net/ansible/ansible/ubuntu focal main`
  - then `sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 93C4A3FD7BB9C367`
  - followed by `sudo apt-get update` and `sudo apt-get install ansible -y`
- Note that you might need to `sudo apt remove ansible` `sudo apt autoremove` before you try to install ansible.

### Nginx Upload Module

Our playbook makes use of `nginx-upload-module`, which is not included by default in any nginx-* distribution from `apt`.
This is a simple recipe for installing nginx with the upload-module.

```
sudo apt remove *nginx* -y &&
sudo apt autoremove -y &&

wget http://nginx.org/download/nginx-1.24.0.tar.gz &&
tar -xzf nginx-1.24.0.tar.gz &&
cd nginx-1.24.0/ &&
git clone https://github.com/hongzhidao/nginx-upload-module.git &&
sudo apt-get install -y libpcre3 libpcre3-dev libssl-dev zlib1g-dev &&
./configure --user=nginx --group=nginx --prefix=/etc/nginx --conf-path=/etc/nginx/nginx.conf --sbin-path=/usr/sbin/nginx --http-log-path=/var/log/nginx/access.log --error-log-path=/var/log/nginx/error.log --lock-path=/var/lock/nginx.lock --pid-path=/run/nginx.pid --modules-path=/usr/lib/nginx/modules --http-client-body-temp-path=/var/lib/nginx/body --http-fastcgi-temp-path=/var/lib/nginx/fastcgi --http-proxy-temp-path=/var/lib/nginx/proxy --http-scgi-temp-path=/var/lib/nginx/scgi --http-uwsgi-temp-path=/var/lib/nginx/uwsgi --with-compat --with-debug --with-pcre-jit --with-http_ssl_module --with-http_stub_status_module --with-http_realip_module --with-http_auth_request_module --with-http_v2_module --with-http_dav_module --with-http_slice_module --with-threads --with-http_addition_module --with-http_gunzip_module --with-http_gzip_static_module --with-http_sub_module --add-module=nginx-upload-module &&
make && make install
```

Note that you might need to `sudo systemctl unmask nginx.service` and remove the `galaxy` and `redirect-ssl` from `/etc/nginx/sites-available and `/etc/nginx/sites-enabled` before running the playbook again.

### Other issues


Use `sudo apt install python3-docker` before running the `usegalaxy.rabbitmqserver` role.

For influxdb apt key error: https://www.influxdata.com/blog/linux-package-signing-key-rotation/

For proftpd add "LoadModule mod_tls.c" to roles/galaxyproject.proftpd/templates/tls.conf.j2 just before the TLSEngine 

