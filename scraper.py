import requests
import config
import re

from bs4 import BeautifulSoup

COURSE_NAME = 'Linear Programming, Modelling and Solution'
LEARN_URL = 'https://www.learn.ed.ac.uk'

with requests.Session() as s:
    res = s.get('https://www.ease.ed.ac.uk/cosign.cgi')
    cookies = dict(res.cookies)
    loginfo = {'login': config.login, 
               'password': config.password,
               'ref': LEARN_URL + '/cgi-bin/login.cgi',
               'service': 'cosign-eucsCosign-www.learn.ed.ac.uk'}
    r = s.post('https://www.ease.ed.ac.uk/cosign.cgi', data=loginfo, cookies=cookies)

    data = {'action': 'refreshAjaxModule', 
               'modId': '_4_1',
               'tabId': '_1_1',
               'tab_tab_group_id': '_171_1'}
    r = s.post(LEARN_URL + '/webapps/portal/execute/tabs/tabAction', data=data)
    soup = BeautifulSoup(r.text, 'lxml')

    course_link = soup.find('a', string=re.compile(COURSE_NAME + '.*')).get('href').strip()
    course_id = re.compile('(?:\/webapps\/blackboard\/execute\/launcher\?type=Course&id=)(.*)&(?:.*)').search(course_link).group(1)
    r = s.get(LEARN_URL + course_link)
    course_url = r.url
    soup = BeautifulSoup(r.text, 'lxml')

    
    content_links = soup.find_all('a', href=re.compile('\/bbcswebdav\/.*'))
    for content_link in content_links:
        r = s.get(LEARN_URL + content_link.get('href'))
        content_name = r.url.split('/')[-1]
        with open(content_name, 'wb') as f:
            f.write(r.content)

    # folders
    dir_links = soup.find_all('a', href=re.compile('\/webapps\/blackboard\/content\/listContent\.jsp\?course_id={}&content_id=.*'.format(course_id)))
    for dir_link in dir_links:  
        if course_url not in LEARN_URL + dir_link.get('href'):
            print(dir_link.get('href'))
            r = s.get(LEARN_URL + dir_link.get('href'))
            soup = BeautifulSoup(r.text, 'lxml')
            content_links = soup.find_all('a', href=re.compile('\/bbcswebdav\/.*'))
            print('{}: \n {} \n\n'.format(dir_link, content_links))
            for content_link in content_links:
                r = s.get(LEARN_URL + content_link.get('href'))
                content_name = r.url.split('/')[-1]
                with open(content_name, 'wb') as f:
                    f.write(r.content)

