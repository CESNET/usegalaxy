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
- OIDC client id and secret set up for federated login with proper scopes

## auth with the playbook

Use your existing ssh key or generate a new one with `$ ssh-keygen -t ed25519`

- If you want to run the playbook through github action you need to add your key to your github profile.
- For executing this from a local machine you can forward your sshkey to the host.

## add a host

For the purposes below the `<YOUR_HOST>` can be e.g. `galaxy-qa2.galaxy.cloud.e-infra.cz`

Add an entry to the `hosts.yml` file which could look like this:

```
galaxyservers:
  hosts:
    <YOUR_HOST>:
      ansible_user: debian
```

## create vars file for your host

Create `host_vars/<YOUR_HOST>/vars.yml`.
Check out the `vars.yml` files of other hosts in this repo to get an idea of what are the options.

note: The same service user (`galaxy-qa1`) is used for both `pulsar-qa1` and `pulsar-qa2` instances.

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
einfracz_client_id: string-with-client-id
einfracz_client_secret: string-with-client-secret

# Galaxy admin API key for tool installation
api_key: dont-be-lazy-a-really-long-password-here
# see https://github.com/galaxyproject/galaxy/blob/dev/doc/source/admin/special_topics/vault.md
vault_encryption_keys:
- generated_key_NUDIABSUmny78sad8a7sby87av8dv=
pulsar_ssh_key: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  asdasdasdad
  -----END OPENSSH PRIVATE KEY-----
```

## RBD storage
On production instances, the Galaxy datasets and other mutable data are stored on RBD (RADOS Block Device) using Ceph. Its installation and configuration is covered by this playbook and the following variables help to maintain the process:
```
rbd_mount_point: /data
rbd_data_dir: "{{ rbd_mount_point }}/galaxy"
rbd_cluster_code: CL4
```

## running playbook
`$ ansible-playbook --limit <YOUR_HOST> galaxy.yml`

## creating service users

At the moment our playbooks assume there is an admin's API key, so after a first run the vault needs to be updated with such a key.

You also need to create a non-admin service user called `galaxy@cesnet.cz` for running tool tests and other non-admin automated tasks.

## tools

Instances' tools are managed by a combination of a cron script that installs them (deployed from this playbook) -- check out [the script](templates/galaxy/cron/install_tools.sh.j2)
and external repository that contains the lists of tools for every instance: https://github.com/CESNET/galaxy_tools.

## deployment troubleshooting

Following are troubleshooting notes gathered through the learning process.


### client build OOM

- stop app before building
- do not build maps (`make client-production` only)
- set reasonable heap (e.g. `NODE_OPTIONS: --max_old_space_size=4096`)
- disable webpack parallel minimizer

```diff
diff --git a/client/webpack.config.js b/client/webpack.config.js
index 8202237857..99f86ec25d 100644
--- a/client/webpack.config.js
+++ b/client/webpack.config.js
@@ -43,7 +43,7 @@ module.exports = (env = {}, argv = {}) => {
     if (targetEnv == "production") {
         minimizations = {
             minimize: true,
-            minimizer: [new TerserPlugin(), new CssMinimizerPlugin()],
+            minimizer: [new TerserPlugin({parallel: false,}), new CssMinimizerPlugin()],
         };
     } else {
         minimizations = {
```


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

### influxdb

For influxdb apt key error: https://www.influxdata.com/blog/linux-package-signing-key-rotation/

### flower

Flower role 2.0 tries to install python `virtualenv` globally, which debian12 does not allow. You have to modify the role to prevent this.
