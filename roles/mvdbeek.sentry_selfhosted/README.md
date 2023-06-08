Ansible Role: peaceman.sentry_selfhosted
========================================

Installs sentry selfhosted via docker-compose project from

https://github.com/getsentry/onpremise

Requirements
------------

* Installed docker and docker-compose

Role Variables
--------------

```yaml
sentry_docker_compose_project_folder: /opt/docker/sentry
sentry_version: 21.1.0
sentry_bind: 9000
sentry_env: {}

sentry_mail:
  host: mail.example.com
  from: sentry@example.com
  port: 587
  username: redacted
  password: redacted

sentry_config:
  slack.client-id: "redacted"
  slack.client-secret: "redacted"
  slack.signing-secret: "redacted"
  slack.legacy-app: false

sentry_url: https://sentry.example.com
sentry_superusers:
  - email: admin@example.com
    password: redacted
```
