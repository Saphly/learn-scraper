import requests
import config
import re

from bs4 import BeautifulSoup

COURSE_NAME = 'Linear Programming, Modelling and Solution'

with requests.Session() as s:
    res = s.get('https://www.ease.ed.ac.uk/cosign.cgi')
    cookies = dict(res.cookies)
    loginfo = {'login': config.login, 
               'password': config.password,
               'ref': 'https://www.learn.ed.ac.uk/cgi-bin/login.cgi',
               'service': 'cosign-eucsCosign-www.learn.ed.ac.uk'}
    r = s.post('https://www.ease.ed.ac.uk/cosign.cgi', data=loginfo, cookies=cookies)
    
    data = {'action': 'refreshAjaxModule', 
               'modId': '_4_1',
               'tabId': '_1_1',
               'tab_tab_group_id': '_171_1'}
    r = s.post('https://www.learn.ed.ac.uk/webapps/portal/execute/tabs/tabAction', data=data)
    html = r.text
    soup = BeautifulSoup(html, 'html.parser')

    print(html)

    # for link in soup.find_all('a'):
    #     print(link)#print(soup.find('a', href='/webapps/blackboard/execute/launcher?type=Course&id=_65022_1&url='))