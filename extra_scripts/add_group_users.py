import psycopg2
import bioblend.galaxy
import sys

conn = psycopg2.connect(database="galaxy", user="postgres")
cursor = conn.cursor()
cursor.execute("SELECT * FROM galaxy_user")
users = cursor.fetchall()
user_dict = dict()

for user in users:
    user_dict[user[0]] = user[3] # id is key, email is value

cursor.execute("SELECT * FROM oidc_user_authnz_tokens WHERE provider='e-infra_cz'")
einfra_users = cursor.fetchall()

einfra_emails = []
for einfra_user in einfra_users:
    einfra_emails.append(user_dict[einfra_user[1]])

server = 'https://' + sys.argv[1]
api_key = sys.argv[2]
gi = bioblend.galaxy.GalaxyInstance(url=server, key=api_key)

api_users = gi.users.get_users()
id_dict = dict()
for user in api_users:
    id_dict[user['email']] = user['id']

groups = gi.groups.get_groups()
for group in groups:
    if group['name'] == 'E-infra':
        group_id = group['id']

for mail in einfra_emails:
    gi.groups.add_group_user(group_id=group_id, user_id=id_dict[mail])
