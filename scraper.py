import requests
import config
import re

from bs4 import BeautifulSoup
from pprint import pprint as pp

FOLDER_REGEX = re.compile('\/webapps\/blackboard\/content\/listContent\.jsp\?course_id=([^&]*)&content_id=([^&]*)')
COURSE_NAME = 'Linear Programming, Modelling and Solution'
LEARN_URL = 'https://www.learn.ed.ac.uk'

ALL_FOLDERS = set()

def get_folders_from_page(page_link, s):
    s.header = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    result = s.get(page_link)
    result.close()
    ALL_FOLDERS.add(result.url)
    soup = BeautifulSoup(result.text, 'lxml')
    folders_links = soup.find_all('a', href=FOLDER_REGEX)
    for folder in folders_links:
        folder = LEARN_URL + FOLDER_REGEX.match(folder.get('href').strip()).group(0)
        if folder in ALL_FOLDERS:
            continue
        else:
            get_folders_from_page(folder, s)



# Logging in to Learn
with requests.Session() as s:
    res = s.get('https://www.ease.ed.ac.uk/cosign.cgi')
    cookies = dict(res.cookies)
    loginfo = {'login': config.login, 
               'password': config.password,
               'ref': LEARN_URL + '/cgi-bin/login.cgi',
               'service': 'cosign-eucsCosign-www.learn.ed.ac.uk'}
    r = s.post('https://www.ease.ed.ac.uk/cosign.cgi', data=loginfo, cookies=cookies)

    # To get to the course module tabs as it loads after the page
    data = {'action': 'refreshAjaxModule', 
            'modId': '_4_1',
            'tabId': '_1_1',
            'tab_tab_group_id': '_171_1'}
    r = s.post(LEARN_URL + '/webapps/portal/execute/tabs/tabAction', data=data)
    soup = BeautifulSoup(r.text, 'lxml')

    # Finding the course that we want 
    course_link = soup.find('a', string=re.compile(COURSE_NAME + '.*')).get('href').strip()

    get_folders_from_page(LEARN_URL + course_link, s)

    pp(list(ALL_FOLDERS))
    print(len(list(ALL_FOLDERS)))
    # ##############
    # r = s.get(LEARN_URL + course_link)
    # course_url = r.url
    # soup = BeautifulSoup(r.text, 'lxml')
    # # Check if there's pdf on the front page and download it
    # content_links = soup.find_all('a', href=re.compile('\/bbcswebdav\/.*'))
    # for content_link in content_links:
    #     r = s.get(LEARN_URL + content_link.get('href'))
    #     content_name = r.url.split('/')[-1]
    #     with open(content_name, 'wb') as f:
    #         f.write(r.content)

    # # Access folder and download pdf
    # dir_links = soup.find_all('a', href=re.compile('\/webapps\/blackboard\/content\/listContent\.jsp\?course_id={}&content_id=.*'.format(course_id)))
    # for dir_link in dir_links:  
    #     # To avoid getting into a loop of reloading the page
    #     if course_url not in LEARN_URL + dir_link.get('href'):
    #         #print(dir_link.get('href'))
    #         #while 
    #         r = s.get(LEARN_URL + dir_link.get('href'))
    #         soup = BeautifulSoup(r.text, 'lxml')
    #         #while 
    #         content_links = soup.find_all('a', href=re.compile('\/bbcswebdav\/.*'))
    #         #print('{}: \n {} \n\n'.format(dir_link, content_links))
    #         # for content_link in content_links:
    #         #     r = s.get(LEARN_URL + content_link.get('href'))
    #         #     content_name = r.url.split('/')[-1]
    #         #     with open(content_name, 'wb') as f:
    #         #         f.write(r.content)


