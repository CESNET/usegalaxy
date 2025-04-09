# MetaCentrum Galaxy Ansible Playbook

This playbook installs and configures Galaxy server on Metacentrum CZ infrastructure.

## requirements

- You need to have `ansible`. Python virtualenv is a recommended way to its installation.

- These ports enabled on host machine:
```
80(HTTP)
443(HTTPS)
4369(TCP)
5671(TCP)
15672(TCP)
25672(TCP)
```

- Metacentrum service account (in the following examples `galaxy-qa1` is used)
- OIDC secrets set up for federated login

## auth with the playbook

Use your existing ssh key or generate new with `$ ssh-keygen -t ed25519`

- If you want to run the playbook through github action you need to add your key to your github profile.
- For executing this from a local machine you can forward your sshkey to the host.

## add a host

For the purposes below the `<YOUR_HOST>` can be e.g. `galaxy-qa2.galaxy.cloud.e-infra.cz`

Add an entry to the `hosts.yml` file which will look like this:

```
galaxyservers:
  hosts:
    <YOUR_HOST>:
      ansible_user: debian
```

## create vars file for your host

Create `host_vars/<YOUR_HOST>/vars.yml`. It should contain the following vars:

```
galaxy_mutable_data_dir: /data/galaxy

pulsar:
  user_name: galaxy-qa1
  nfs_home: brno11-elixir
  nfs_prefix: pulsar-qa2
  pbs_queue: galaxyqa
  pbs_gpu_queue: galaxy_gpu

pulsar_data_dir: "/storage/{{ pulsar.nfs_home }}/home/{{ pulsar.user_name }}/{{ pulsar.nfs_prefix }}"

# displayed in Galaxy's masthead
csnt_brand: <YOUR_HOST>
```

note: the same service user (`galaxy-qa1`) is used for both `pulsar-qa1` and `pulsar-qa2`

## create and fill ansible vault

generate password with `$ openssl rand -base64 24 > .vault-password.txt`

create vault for your host `ansible-vault create host_vars/<YOUR_HOST>/secret.yml`

The vault should contain the following vars:

```yml
vault_id_secret: choose_something_unique_per_instance
rabbitmq_users_password:
  mqadmin: a-really-long-password-here
  pulsar: a-really-long-DIFFERENT-password-here
vault_rabbitmq_password_galaxy: good-password-here
oidc_client_id: string-with-client-id
oidc_client_secret: string-with-client-secret

# Galaxy admin API key for tool installation
api_key: dont-be-lazy-a-really-long-password-here

# see https://github.com/galaxyproject/galaxy/blob/dev/doc/source/admin/special_topics/vault.md
vault_encryption_keys:
- generated_key_NUDIABSUmny78sad8a7sby87av8dv=

pulsar_ssh_key: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  asdasdasdad
  -----END OPENSSH PRIVATE KEY-----

tiaas_password: a-really-long-password-here
vault_rabbitmq_password_flower: a-really-long-password-here
vault_flower_user_password: a-really-long-password-here
vault_sentry_password: a-really-long-password-here
vault_reports_admin_password: a-really-long-password-here
```
note: you should avoid having a `/` or `\` in your password as galaxy will interpret this as a path.

## running playbook
`$ ansible-playbook --limit <YOUR_HOST> galaxy.yml`

## tools

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

## deployment troubleshooting

Following are troubleshooting notes gathered through the learning process.

### glibc

On ubuntu < 22.04 and Debian < 12 the GLIBC version is incompatible with the ```galaxyproject.tusd``` GLIBC, therefore playbook ends in error.
- in `roles/galaxyproject.tusd/defaults/main.yml` you have to set the `tusd_version:` to 'v1.8.0' (tested, possibly higher)

### debian 11

On Debian 11 the default version of `ansible` is 2.10.08 which fails to extract binaries for TUSd.
- workaround:
  - `sudo vim /etc/apt/sources.list` add this line : `deb http://ppa.launchpad.net/ansible/ansible/ubuntu focal main`
  - then `sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 93C4A3FD7BB9C367`
  - followed by `sudo apt-get update` and `sudo apt-get install ansible -y`
- Note that you might need to `sudo apt remove ansible` `sudo apt autoremove` before you try to install ansible.

### rabbitmq python

Use `sudo apt install python3-docker` before running the `usegalaxy.rabbitmqserver` role.

### influxdb

For influxdb apt key error: https://www.influxdata.com/blog/linux-package-signing-key-rotation/
