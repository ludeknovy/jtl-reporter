import os
import glob
import requests
import json
import sys
from argparse import ArgumentParser

# if you use different folder for saving your output files change this path accordingly
directory = './logs'

parser = ArgumentParser()
parser.add_argument("-s", "--scenario", dest="scenario",
                    help="scenario name", required=True)
parser.add_argument("-p", "--project",
                    dest="project", required=True,
                    help="project name")
parser.add_argument("-e", "--environment",
                    dest="environment", required=True,
                    help="environment")
parser.add_argument("-host", "--hostname",
                    dest="hostname", required=False,
                    help="hostname")
parser.add_argument("-ec", "--exit-code",
                    dest="exit_code", required=False,
                    help="exit code")
parser.add_argument("-er", "--exit-reason",
                    dest="exit_reason", required=False,
                    help="exit reason")

args = parser.parse_args()

latest_folder = max([os.path.join(directory, d) for d in os.listdir(directory) if os.path.isdir(
    os.path.join(os.path.abspath(directory), d))], key=os.path.getmtime)


def get_note(note):
    return '' if note == 'None' else str(note)

note = get_note(args.exit_reason)

files = dict(
    kpi=open(latest_folder + '/kpi.jtl', 'rb'),
    environment=(None, args.environment),
    status=(None, args.exit_code),
    note=(None, get_note(args.exit_reason))
)

if (os.path.exists(latest_folder + '/monitoring_logs.csv')):
    logs = open(latest_folder + '/monitoring_logs.csv', 'rb')
    files['monitoring'] = logs

url = '<jtl-reporter-base-url:port>/api/projects/%s/scenarios/%s/items' % (
    args.project, args.scenario)

r = requests.post(url, files=files, headers={'x-access-token': 'yourApiToken'})
