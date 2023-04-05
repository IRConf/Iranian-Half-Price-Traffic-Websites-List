import requests
import sys
import re
import numpy as np
import pandas as pd

session = requests.Session()

session.proxies = {'https': 'http://5.161.55.129:8080'}

html = session.get('https://eservices.ito.gov.ir/page/iplist').text

start_string = '<form action="/Page/GetIPList" method="post"><input name="__RequestVerificationToken" type="hidden" value="'
end_string = '" />            <div class="row">'

start_index = html.find(start_string) + len(start_string)
end_index = html.find(end_string)

token = html[start_index:end_index]

if not token or not session.cookies.get_dict()['__RequestVerificationToken']:
  sys.exit('Cannot access')

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

data = pd.read_html(html.content)
domain_list = data[0].iloc[:,0]

filtered_list = []
for domain in domain_list:
  filter = re.search(r"(.*://)?([^/:]+\.)?([^/:]+\.[a-z][a-z0-9]+)(/)?", domain.lower())
  if filter and filter.group(3):
    filtered_list.append(filter.group(3))

filtered_list = np.unique(np.array(filtered_list))

open("domains", "w").write('\n'.join(filtered_list))

open('list.json', 'w').write(data[0].to_json())
