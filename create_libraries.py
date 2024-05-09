#import psycopg2
from bioblend import galaxy
import sys, os

server_name = sys.argv[1]
server = 'https://' + server_name
api_key = sys.argv[2]
gi = galaxy.GalaxyInstance(url=server, key=api_key)

# Define library properties
library_name = sys.argv[3] if sys.argv and len(sys.argv)>3 else "RCX-data"
library_description = sys.argv[4] if sys.argv and len(sys.argv)>4 else "Recetox data from Sally"

# Create library
if not library_name in [l['name'] for l in gi.libraries.get_libraries()]:
  new_library = gi.libraries.create_library(name=library_name, description=library_description)
  print("New library ID:", new_library['id'])
else:
  print("Library "+library_name+" already exists!")
  for new_library in gi.libraries.get_libraries():
    if library_name == new_library['name']:
      break
# populate library
data_dir = sys.argv[5] if sys.argv and len(sys.argv) > 5 else '/mnt/sally/000020-Shares/rcx-da/umsa_test'
root_folder_id = None
for root, dirs, files in os.walk(data_dir):
#  for item in dirs:
#    if not any([dir.startswith('.') for dir in os.path.join(root,item).split(os.path.sep)]) and files:
#      print('..importing folder '+os.path.join(root,item))
#      new_ldda = gi.libraries.upload_file_from_server(library_id=new_library['id'], server_dir=os.path.join(os.path.relpath(root, '/mnt/sally/'),item), link_data_only='link_to_files', preserve_dirs=True)

  if not any([dir.startswith('.') for dir in root.split(os.path.sep)]):
    if not os.path.basename(root) in [d['name'] for d in gi.libraries.get_folders(library_id=new_library['id'])]:
      print('..creating folder '+root)
      new_folder = gi.libraries.create_folder(library_id=new_library['id'], folder_name=os.path.basename(root), base_folder_id = root_folder_id)
      root_folder_id = new_folder[0]['id']
    else:
      print('..skipping folder '+root+' because it already exists!')
      for d in gi.libraries.get_folders(library_id=new_library['id']):
        if os.path.basename(root) == d['name']:
          root_folder_id = d['id']
          break
    for filename in files:
      if not filename.startswith('.'):
        print('..creating file '+filename)
#        new_ldda = gi.libraries.upload_file_from_local_path(library_id=new_library['id'], file_local_path=os.path.join(root,filename), folder_id=root_folder_id)
        new_ldda = gi.libraries.upload_from_galaxy_filesystem(library_id=new_library['id'], filesystem_paths=os.path.join(root,filename), folder_id=root_folder_id, link_data_only='link_to_files')
  else:
    print('..skipping folder '+root+' because it starts with a dot (i.e., most probably a hidden folder)!')

#new_ldda = gi.libraries.upload_file_from_server(library_id=new_library['id'], server_dir=data_dir, link_data_only='link_to_files', preserve_dirs=True)
print("Populating library "+new_library['id']+" with data from "+data_dir+" has finished!")
