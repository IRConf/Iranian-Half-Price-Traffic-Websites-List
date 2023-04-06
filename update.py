import requests
import sys
import re
import json
import pandas as pd
import socket
from netaddr import IPNetwork, IPAddress
from multiprocessing import Manager, Pool
import functools

# Create a multiprocessing manager and pool for parallel processing
manager = Manager()
pool = Pool()

# set default timeout for socket requests to 1 second
socket.setdefaulttimeout(1)

# Define a function to check if a domain is valid based on its IP address on list
def is_domain_valid(domain, ipnets):
  try:
    ip = IPAddress(socket.gethostbyname(domain))  # get IP address of the domain
    for ipnet in ipnets:
      if ip in IPNetwork(ipnet):
        return True  # Return True if domain IP matches the IP range in the list
  except:
    return False  # return False if domain does not exist


# Define a function to check if a domain is valid and add it to the domain list if it is
def check_domain_worker(item, old_domain_list, domain_list):
  domain, ipnets = item
  # Check if the domain is not in the old domain list, not already in the domain list, and is valid
  if domain not in old_domain_list and domain not in domain_list and is_domain_valid(domain, ipnets):
    # Add the domain to the domain list
    domain_list.append(domain)


# create a requests session and set the proxy for HTTPS requests
session = requests.Session()
session.proxies = {'https': 'http://5.161.55.129:8080'}

# send a GET request to a URL and store the HTML response
html = session.get('https://eservices.ito.gov.ir/page/iplist').text

# extract a token from the HTML response using start and end strings
start_string = '<form action="/Page/GetIPList" method="post"><input name="__RequestVerificationToken" type="hidden" value="'
end_string = '" />            <div class="row">'
start_index = html.find(start_string) + len(start_string)
end_index = html.find(end_string)
token = html[start_index:end_index]

# check if token and cookie exist, exit if not
if not token or not session.cookies.get_dict()['__RequestVerificationToken']:
  sys.exit('Cannot access')

# Send a POST request with data and headers to GetIPList endpoint to download eligible websites list
html = session.post('https://eservices.ito.gov.ir/Page/GetIPList', 
                      headers = {
                          "Referer": "https://eservices.ito.gov.ir/page/iplist",
                          "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
                          "Referrer-Policy": "strict-origin-when-cross-origin"
                          },
                      data = {
                          "__RequestVerificationToken": token,
                          "ExportExcel":'true',
                          "CustomSearch": ""
                          }
                      )

# Write the response content to a file named list.xls
open('list.xls', 'wb').write(html.content)

# Use pandas to extract data from HTML table 
data = pd.read_html(html.content)

# Write the table to a JSON file named list.json
open('list.json', 'w').write(data[0].to_json())

# Extract domains from website URLs
new_domain_list = {}
for website in data[0].iloc:
  # Use regular expression to extract domain from URL
  filter = re.search(r"(.*://)?([^/:]+\.)?([^/:]+\.[a-z][a-z0-9]+)(/)?", website[0].lower())
  if filter and filter.group(3):
    domain = filter.group(3)
    # append ipnet to domain key
    if domain not in new_domain_list:
      new_domain_list[domain] = []
    new_domain_list[domain].append(website[2]) 

# Load previous not filtered domain list
old_domain_list = json.load(open("old_domains", "r"))

# Write the list of new domains before filtering to a file named old_domains
json.dump(new_domain_list, open("old_domains", "w"))

# Load previous domain list
domain_list = open("domains", "r").read().split('\n')

# Convert domain_list to a shared list so it can be safely accessed by multiple processes
# Also convert old_domain_list to a shared list for consistency
domain_list = manager.list(domain_list)
old_domain_list = manager.list(old_domain_list)

# Map the check_domain_worker function to each item in the new_domain_list dictionary, passing in the shared old_domain_list
# and domain_list as arguments to the function
pool.map(functools.partial(check_domain_worker, old_domain_list=old_domain_list, domain_list=domain_list), new_domain_list.items())

# Sort the domain list alphabetically
domain_list.sort()

# Write the filtered list of domains to a file named domains
open("domains", "w").write('\n'.join(domain_list))