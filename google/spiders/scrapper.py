import scrapy
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.request import urlopen
import json
from datetime import datetime
import tldextract
import socket
from bs4 import BeautifulSoup
import re
from urllib.request import Request
import trafilatura

API_KEY = '9d96544d6380b375233763276cd810ca'

def get_url(url):
    payload = {'api_key': API_KEY, 'url': url, 'autoparse': 'true', 'country_code': 'in'}
    proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    return proxy_url

def create_google_url(query, site=''):
    google_dict = {'q': query, 'num': 2}
    return 'http://www.google.com/search?' + urlencode(google_dict)

def bs4text(link):
    try:
        soup = BeautifulSoup(urlopen(link).read(), features="lxml")
        txt = soup.getText()
    except:
        return None
    return txt

def tfttext(link):
    try:
        downloaded = trafilatura.fetch_url(link)
        txt = trafilatura.extract(downloaded)
    except:
        return None
    return txt
        

class GoogleSpider(scrapy.Spider):
    name = 'google'
    allowed_domains = ['api.scraperapi.com']
    custom_settings = {'ROBOTSTXT_OBEY': 'False',
                       'LOG_LEVEL': 'INFO',
                       'CONCURRENT_REQUESTS_PER_DOMAIN': 1, 
                       'RETRY_TIMES': 3}

    def start_requests(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive'
        }
        with open(self.inp) as f:
            queries = [line.rstrip() for line in f]
        for query in queries:
            url = create_google_url(query)
            yield scrapy.Request(get_url(url), callback=self.parse, meta={'pos': 0}, headers = headers)
            
            

    def parse(self, response):
        if response.status >= 500:
            print('#########################################################STOP############################################################################')
            return
        di = json.loads(response.text)
        query = di['search_information']['query_displayed']
        pos = response.meta['pos']
        # ioclist = response.meta['ioclist']
        for result in di['organic_results']:
            link = result['link']
            txt = bs4text(link)
            if txt is None:
                txt = tfttext(link)
                if txt is None:
                    return
                
            ioc = re.findall(r"([a-fA-F\d]{32})", txt)
            ioc = list(set(ioc))
            ioc = [i.lower() for i in ioc]
            ip = re.findall(r"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", txt)
            # url = re.findall(r"(?!http|https|https:\/\/|http:\/\/)([?a-zA-Z0-9-.\+]{2,256}\.[a-z]{2,4}\b)", txt)
            # ip = ip + url
            maxlen = max(len(ioc), len(ip))
            ioc += [''] * (maxlen - len(ioc))
            ip += [''] * (maxlen - len(ip))
            
            domain = []
            for addr in ip:
                if addr != '':
                    try:
                        domain.append(socket.gethostbyaddr(addr)[0])
                    except:
                        domain.append('')
                else:
                    domain.append('')
            for i in range(maxlen):
                # if ioc[i] not in ioclist or ioc[i] == '':
                item = {'position': pos, 'query': query, 'link': link, 'ioc': ioc[i], 'ip': ip[i], 'domain': domain[i]}
                    # if ioc[i] != '':
                    #     ioclist.append(ioc[i])
                pos = pos + 1
                yield item
