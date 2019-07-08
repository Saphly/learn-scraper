import config
import re
import requests

from bs4 import BeautifulSoup
from pprint import pprint as pp

FOLDER_INFOS = set()
CONTENT_REGEX = re.compile('\/bbcswebdav\/.*')
COURSE_NAME = 'Linear Programming, Modelling and Solution'
EASE_URL = 'https://www.ease.ed.ac.uk/cosign.cgi'
FOLDER_REGEX = re.compile(
    '\/webapps\/blackboard\/content\/listContent\.jsp\?course_id=([^&]*)&content_id=([^&]*)')
LEARN_URL = 'https://www.learn.ed.ac.uk'


def get_folder_infos_from_page(page_link, s, breadcrumb):
    response = s.get(page_link)
    soup = BeautifulSoup(response.text, 'lxml')

    # Scrape the page title and add it to the given breadcrumb
    folder_name = soup.find('span', id='pageTitleText').find('span').string
    breadcrumb += (folder_name,)

    # Keep track of links + path that we have visited
    folder_info = (breadcrumb, response.url)
    FOLDER_INFOS.add(folder_info)

    folder_htmls = soup.find_all('a', href=FOLDER_REGEX)
    for folder_html in folder_htmls:
        folder_suffix = FOLDER_REGEX.match(folder_html.get('href')).group(0)
        folder_link = LEARN_URL + folder_suffix
        # Do not visit links that we have already visited
        if any(folder_link in folder_info for folder_info in FOLDER_INFOS):
            continue
        else:
            get_folder_infos_from_page(folder_link, s, breadcrumb)


with requests.Session() as s:
    # Logging in to Learn via EASE.
    response = s.get(EASE_URL)
    cookies = dict(response.cookies)
    loginfo = {'login': config.login,
               'password': config.password,
               'ref': LEARN_URL + '/cgi-bin/login.cgi',
               'service': 'cosign-eucsCosign-www.learn.ed.ac.uk'}
    response = s.post(EASE_URL, data=loginfo, cookies=cookies)
    # Load course module tabs, which is populated dynamically.
    data = {'action': 'refreshAjaxModule',
            'modId': '_4_1',
            'tabId': '_1_1',
            'tab_tab_group_id': '_171_1'}
    response = s.post(
        LEARN_URL + '/webapps/portal/execute/tabs/tabAction', data=data)
    soup = BeautifulSoup(response.text, 'lxml')

    # Find the course that we want, and populate FOLDER_INFOS
    # recursively using the get_folder_infos_from_page function.
    course_html = soup.find('a', string=re.compile(COURSE_NAME + '.*'))
    course_title = course_html.string
    course_link = LEARN_URL + course_html.get('href').strip()
    get_folder_infos_from_page(course_link, s, (course_title,))

    pp(list(FOLDER_INFOS))
    pp(len(list(FOLDER_INFOS)))

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
