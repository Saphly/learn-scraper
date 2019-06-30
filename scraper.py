import requests
import config
with requests.Session() as s:
    res = s.get('https://www.ease.ed.ac.uk/cosign.cgi')
    cookies = dict(res.cookies)
    loginfo = {'login': config.login, 
               'password': config.password,
               'ref': 'https://www.learn.ed.ac.uk/cgi-bin/login.cgi',
               'service': 'cosign-eucsCosign-www.learn.ed.ac.uk'}
    r = requests.post('https://www.ease.ed.ac.uk/cosign.cgi', data=loginfo, cookies=cookies)
    print(r.status_code)
    print(r.text)
