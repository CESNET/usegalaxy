import psycopg2
from bioblend import galaxy
import sys

server_name = sys.argv[1]
server = 'https://' + server_name
api_key = sys.argv[2]
gi = galaxy.GalaxyInstance(url=server, key=api_key)

# Define library properties
library_name = 'Test'
library_description = 'Library for testing purpose'

# Create library
new_library = gi.libraries.create_library(name=library_name, description=library_description)

print("New library ID:", new_library['id'])
