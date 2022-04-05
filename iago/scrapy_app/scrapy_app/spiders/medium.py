import json
import logging
import requests
import os

import scrapy
from bs4 import BeautifulSoup
from v0.models import ScrapedArticle, Skill
from v0.utils import clean_str

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MediumSpider(scrapy.spiders.CrawlSpider):
    name = 'medium'

    def __init__(self, tags, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tags = tags.split(',')

        self.seen_urls = set(ScrapedArticle.objects.all().values_list('url', flat=True))
        self.start_urls = [f'https://medium.com/tag/{tag}/archive/' for tag in tags]
        self.IAGO_API_USER = os.getenv('IAGO_API_SCRAPY_USER')
        self.IAGO_API_PASS = os.getenv('IAGO_API_SCRAPY_PASS')

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_tagpage)

    def parse_tagpage(self, response):
        """ medium tag page parse, find all years of publication and send to parse_days to get articles """

        # use the last page button to grab the number of pages
        soup = BeautifulSoup(str(response.text), features='lxml')
        timebuckets = soup.findAll('div', attrs={'class': 'timebucket'})

        years = [int(x.text) for x in timebuckets]

        for y in years:  # generate urls for all months in the years we have articles
            yearUrl = response.url + "/" + str(y)
            for m in range(1, 12):
                monUrl = yearUrl + "/" + str(m)
                yield scrapy.Request(url=monUrl, callback=self.parse_month)

    def parse_month(self, response):
        """ get article links from days or months """

        monSoup = BeautifulSoup(str(response.text), features='lxml')
        allDays = monSoup.findAll("div", attrs={'class': 'timebucket'})
        if len(allDays) != 0:  # if we do have days lets check the day pages
            for a in allDays:
                dayUrl = a.find("a")
                if dayUrl is not None:  # it could be not linked
                    dayUrl = str(dayUrl['href'])
                    yield scrapy.Request(url=dayUrl, callback=self.parse_day)

        else:  # get articles directly from month/year whatever we got directed to
            links = list(monSoup.findAll("div", attrs={"class": "postArticle-readMore"}))
            for l in links:
                # pull article link
                articleLink = str(l.find("a")['href']).partition('?')[0]
                if articleLink not in self.seen_urls:
                    self.seen_urls.add(articleLink)
                    postID = articleLink.split('/')[-1].split('-')[-1]
                    yield scrapy.Request(url=f'https://medium.com/_/api/posts/{postID}', callback=self.parse_article, meta={'articleLink': articleLink})

    def parse_day(self, response):
        """ get article links from days """

        daySoup = BeautifulSoup(str(response.text), features='lxml')
        links = list(daySoup.findAll("div", attrs={"class": "postArticle-readMore"}))
        for l in links:
            # pull article link
            articleLink = str(l.find("a")['href']).partition('?')[0]
            if articleLink not in self.seen_urls:
                self.seen_urls.add(articleLink)
                postID = articleLink.split('/')[-1].split('-')[-1]
                yield scrapy.Request(url=f'https://medium.com/_/api/posts/{postID}', callback=self.parse_article, meta={'articleLink': articleLink})

    def parse_article(self, response):
        code = response.status

        if code == 200:
            yield self._post_200(response)

        elif code == 302:
            yield self._post_302(response)

        elif code == 410:
            yield self._post_410(response)

        # add here other requests code if necessary

    # https://github.com/S1M0N38/medium-scraper/blob/master/medium/spiders/post_spider.py
    def _post_200(self, response):
        data = json.loads(response.text[16:])
        # https://pastebin.com/VRs24XmV
        post = data['payload']['value']

        # filter non eng
        if post['detectedLanguage'] != 'en':
            logger.info(f'BOUNCED {post["title"]} for majority non-english content')
            return

        article = ScrapedArticle()
        article.url = response.meta.get('articleLink')
        article.title = post['title']
        # author is annoying
        if 'references' in data['payload'] and 'User' in data['payload']['references']:
            article.author = data['payload']['references']['User'].popitem()[1]['name']
        elif '@' in article.url:
            article.author = article.url.split('@')[1].split('/')[0]

        article.subtitle = post['virtuals']['subtitle']
        article.thumbnail = f"https://miro.medium.com/{post['virtuals']['previewImage']['imageId']}"  # https://miro.medium.com/0*5avpGviF6Pf1EyUL.jpg
        article.content_read_seconds = int(float(post['virtuals']['readingTime'])*60)
        article.provider = 'medium'

        # concat paragraphs
        paragraphs = []
        for par in post['content']['bodyModel']['paragraphs']:
            paragraphs.append(clean_str(par['text']))

        article.content = '\n\n'.join(paragraphs)

        for t in post['virtuals']['tags']:
            if t['type'] == 'Tag':
                article.tags.append(t['slug'])

        # do article AI processing, use Iago api

        # use serverless to get the embedding
        r = requests.get('https://serverless.iago.jeeny.ai/transform', json={'texts': [article.content]}, verify=False) # didnt fix the ssl issue on serverless yet
        if r.status_code == 200:
            logger.info(f'IAGO serverless embed complete for {article.title}')
            article.embedding_all_mpnet_base_v2 = r.json()['vectors'][0]
        else:
            logger.error(f'Iago Serverless API {r.status_code} {r.text}')
            return

        # then use django iago to get the skills
        r = requests.get('https://api.iago.jeeny.ai/v0/skillspace/match_embeds', json={'embeds': [article.embedding_all_mpnet_base_v2]}, auth=(self.IAGO_API_USER, self.IAGO_API_PASS))
        # r = requests.get('http://localhost:80/v0/skillspace/match_embeds', json={'embeds': [article.embedding_all_mpnet_base_v2]}, auth=(self.IAGO_API_USER, self.IAGO_API_PASS))
        if r.status_code == 200:
            logger.info(f'IAGO processing complete for {article.title}')
            article_ai_data = r.json()['results'][0]
            article.save()
            for skill in article_ai_data['skills']:
                article.skills.add(Skill.objects.get(name=skill))
        else:
            logger.error(f'Iago API {r.status_code} {r.text}')
            
        return {'article': article}

    def _post_302(self, response):
        post_id = response.url.split('/')[-1]
        logger.info('The post {post_id} removed (user is blacklisted)')

    def _post_410(self, response):
        post_id = response.url.split('/')[-1]
        logger.info('The post {post_id} removed (user removed it)')
