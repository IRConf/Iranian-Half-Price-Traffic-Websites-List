# import necessary modules
import requests
import sys
import re
import numpy as np
import pandas as pd
import socket

# set default timeout for socket requests to 1 second
socket.setdefaulttimeout(1)

# define a function to check if a domain exists
def is_domain_exists(domain):
  try:
    ips = socket.gethostbyname(domain)  # get IP address of the domain
    return True  # return True if domain exists
  except:
    return False  # return False if domain does not exist

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

# Select the first column of the first table that contains website urls
website_list = data[0].iloc[:,0]

# Extract domains from website URLs
new_domain_list = []
for website in website_list:
  # Use regular expression to extract domain from URL
  filter = re.search(r"(.*://)?([^/:]+\.)?([^/:]+\.[a-z][a-z0-9]+)(/)?", website.lower())
  if filter and filter.group(3):
    domain = filter.group(3)
    new_domain_list.append(domain)

# Remove duplicate domains using numpy
new_domain_list = np.unique(np.array(new_domain_list)).tolist()

# Load previouse not filtered domain list
old_domain_list = open("raw_domains", "r").read().split('\n')

# Write the list of new domains before filtering to a file named raw_domains
open("raw_domains", "w").write('\n'.join(new_domain_list))

# load previouse domain list
domain_list = open("domains", "r").read().split('\n')

# Filter new domains to only include those that exist
for domain in new_domain_list:
    if domain not in old_domain_list and is_domain_exists(domain):
      domain_list.append(domain)

# Sort list
domain_list.sort()

# Write the filtered list of domains to a file named domains
open("domains", "w").write('\n'.join(domain_list))
