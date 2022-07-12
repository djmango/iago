import json
import logging
import requests
import os
# from oauthlib.oauth2 import BackendApplicationClient
# from requests_oauthlib import OAuth2Session
import pandas as pd

import scrapy
from bs4 import BeautifulSoup
from v0.models import Content, Skill
from v0.utils import mediumReadtime, clean_str

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HbrSpider(scrapy.spiders.CrawlSpider):
    name = 'hbr'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.seen_urls = set(Content.objects.filter(provider='hbr').values_list('url', flat=True))
        df = pd.read_csv('https://gist.githubusercontent.com/djmango/b580fc6eaef2fb625553ab418f68d1a1/raw/eaec2495d742d286a513b36a49ac2aa991909346/hbr.csv')
        self.start_urls = [str(x).replace('https://', 'https://') for x in df['article-href'].to_list() if x not in self.seen_urls]

        # oauth for iago
        # self._iago_oauth()

        logger.info(f'-- {str(self.name).upper()} SPIDER STARTED WITH {len(self.start_urls)} URLS')

    def _save_token(self, token):
        self.iago_token = token

    # def _iago_oauth(self):
    #     client_id = os.getenv('IAGO_EXPRESSAPI_CLIENT_ID')
    #     client_secret = os.getenv('IAGO_EXPRESSAPI_CLIENT_SECRET')
    #     self.client = BackendApplicationClient(client_id=client_id, client_secret=client_secret)
    #     oauth = OAuth2Session(client=self.client)
    #     self.token = oauth.fetch_token(token_url='https://auth.iago.jeeny.ai/oauth2/token')
    #     # self.client = OAuth2Session(client_id, token=token, auto_refresh_url='https://auth.iago.jeeny.ai/oauth2/token', token_updater=self._save_token)
    #     # r = self.client.get(protected_url)
    #     print('e')

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_article)

    def parse_article(self, response):
        code = response.status

        if code == 200:
            yield self._post_200(response)

        else:
            logger.warning(f'{response.url} returned {code}')

        # add here other requests code if necessary

    def _post_200(self, response):
        soup = BeautifulSoup(str(response.text), features='lxml').find('div', {'class': 'content-area--left-aligned'})
   
        article = Content()
        article.url = response.url
        article.last_response = soup.prettify()
        article.title = soup.find('h1', {'class': 'article-hed'}).text
        # as usual author is annoying
        authors = soup.find('ul', {'class': 'article-byline-list'})
        authors_str = ''
        for author in authors.find_all('a'):
            authors_str += author.text + ' '
        article.author = authors_str
        article.thumbnail = 'https://hbr.org' + str(soup.find('div', {'class': 'hero-image-content '}).find('img')['src'])
        article.content = clean_str(soup.find('div', {'class': 'article-body standard-content'}).text)
        article.content_read_seconds = mediumReadtime(article.content)
        article.provider = Content.providers.hbr

        # # use django iago to get the skills and embed
        # r = requests.get('https://api.iago.jeeny.ai/v0/skillspace/match', json={'texts': [article.content]})
        # if r.status_code == 200:
        #     logger.info(f'IAGO processing complete for {article.title}')
        #     article_ai_data = r.json()['results'][0]
        #     article.embedding_all_mpnet_base_v2 = article_ai_data['embed']
        #     article.save()
        #     for skill in article_ai_data['skills']:
        #         article.skills.add(Skill.objects.get(name=skill))
        # else:
        #     logger.error(f'Iago API {r.status_code} {r.text}')
        return {'article': article}
