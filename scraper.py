import config
import os
import re
import requests

from bs4 import BeautifulSoup
from pprint import pprint as pp

FOLDER_INFOS = set()
CONTENT_REGEX = re.compile('\/bbcswebdav\/.*')
COURSE_NAME = 'Linear Programming, Modelling and Solution'
EASE_URL = 'https://www.ease.ed.ac.uk/cosign.cgi'
FOLDER_REGEX = re.compile(
    '\/webapps\/blackboard\/content\/listContent\.jsp\?course_id=' +
    '([^&]*)&content_id=([^&]*)'
)
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
    response = s.get(
        LEARN_URL + '/auth-saml/saml/login', params={'apId': '_175_1'})
    soup = BeautifulSoup(response.text, 'lxml')
    form_url = soup.find('form').get('action')
    saml_request = soup.find('input').get('value')

    response = s.post(form_url, data={'SAMLRequest': saml_request})
    soup = BeautifulSoup(response.text, 'lxml')
    login_form = soup.find('form', attrs={'method': 'post'})
    loginfo = {'login': config.login,
               'password': config.password}
    for key in ['submit', 'ref', 'service']:
        loginfo[key] = login_form.findChild(
            'input', attrs={'name': key}).get('value')
    form_url = login_form.get('action')

    response = s.post(EASE_URL + form_url, data=loginfo)
    soup = BeautifulSoup(response.text, 'lxml')
    form_url = soup.find('form').get('action')
    saml_response = soup.find('input').get('value')

    response = s.post(form_url, data={'SAMLResponse': saml_response})

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

    for folder_path, folder_link in FOLDER_INFOS:
        dir_path = '/'.join(folder_path)
        os.makedirs(dir_path, exist_ok=True)
        r = s.get(folder_link)
        soup = BeautifulSoup(r.text, 'lxml')
        content_links = soup.find_all('a', href=re.compile('\/bbcswebdav\/.*'))
        for content_link in content_links:
            r = s.get(LEARN_URL + content_link.get('href'))
            content_name = r.url.split('/')[-1]
            with open(dir_path + '/' + content_name, 'wb') as f:
                f.write(r.content)
