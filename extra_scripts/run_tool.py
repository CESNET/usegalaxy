## python3 -m pip install bioblend
import argparse
from bioblend import galaxy
from bioblend import TimeoutException

OK = 0
WARN = 1
CRIT = 2
UNK = 3

# Initialize parser
parser = argparse.ArgumentParser()

# Adding optional argument
parser.add_argument("-g", "--galaxy", help = "Galaxy instance URI")
parser.add_argument("-a", "--api_key", help = "Galaxy user API-key")
parser.add_argument("-t", "--tool_id", help = "Tool to run by its ID")

# Read arguments from command line
args = parser.parse_args()

if args.galaxy:
  galaxy_url = args.galaxy
else:
  print("Galaxy instance URI is missing!")
  exit(CRIT)

if args.api_key:
  api_key = args.api_key
else:
  print("Galaxy user API-key is missing!")
  exit(CRIT)

if args.tool_id:
  tool_name = args.tool_id
else:
  print("Tool to run is missing!")
  exit(CRIT)

hist_name = 'test_'+tool_name
wait_for = 300 # seconds
check_freq = 5 # every X seconds
max_jobs = 500 # Maximum allowed jobs per history cause we experienced some performance troubles and delay when trying to use history with a few hundreds of tousands of jobs

gi = galaxy.GalaxyInstance(galaxy_url, api_key)

hobj = [i  for i in  gi.histories.get_histories() if i['name']==hist_name]
if not hobj:
  print("Creating new history: "+hist_name)
  hobj = gi.histories.create_history(hist_name)
else:
  print("History "+hist_name+" found.")
  hobj = hobj[0]
  if hobj['count'] > max_jobs:
    print("Too many jobs in history. Re-creating it!")
    gi.histories.delete_history(hobj['id'], True)
    hobj = gi.histories.create_history(hist_name)

hid = hobj['id']
try:
  print("Running tool "+tool_name)
  jid = gi.tools.run_tool(hid, tool_name, {})['jobs'][0]['id']
  print("Waiting for job "+str(jid)+" to finish in "+str(wait_for)+" seconds.")
  gi.jobs.wait_for_job(jid, wait_for, check_freq)
except TimeoutException:
  print("Job "+str(jid)+" didn't finish correctly on time.")
  exit(WARN)
print("Job finished correctly on time")
exit(OK)
