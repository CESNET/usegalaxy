Example playbook 
=======
This playbook will deploy Nginx creating 2 virtualhosts:
* one http to be used by certbot to request the SSL certificate
* one https to serve the RabbitMQ administration website

Afterwards, it will deploy RabbitMQ creating two users:
* __mqadmin__ as administrator
* __galaxy__ as regular user
The user galaxy will be also associated to a galaxy virtualhost.

Password for both users are hosted on [secret_group_vars/rabbitmq.yml](secret_group_vars/rabbitmq.yml).
If you are planning to publish somewhere this playbook, this file should be encrypted (e.g. with ansible-vault).

Before to run this playbook, you have to update some variables in [group_vars/rabbitmq.yml](group_vars/rabbitmq.yml):
* __hostname__ - replace here your node's fqdn
* __certbot_admin_email__ -replace here your email
* __certbot_environment__: change to production when everything is ready to go

The RabbitMQ administration interface will be exposed at https://your_node_fqdn/rabbit
