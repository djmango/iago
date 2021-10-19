import logging

import scrapy
from action_engine.models import Article
from bs4 import BeautifulSoup
from iago.utils import clean_str

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

API_BASE_URL = 'http://api.scraperapi.com/'

class MediumSpider(scrapy.spiders.CrawlSpider):
    name = 'medium'
    # allowed_domains = ['*']

    def __init__(self, tags, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tags = tags.split(',')
        
        self.seen_urls = set(Article.objects.all().values_list('url', flat=True))
        self.start_urls = [f'https://medium.com/tag/{tag}/archive/' for tag in tags]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_tagpage)

    def parse_tagpage(self, response):
        """ medium tag page parse, find all years of publication and send to parse_days to get articles """

        # use the last page button to grab the number of pages
        soup = BeautifulSoup(str(response.text), features='lxml')
        timebuckets = soup.findAll('div', attrs={'class': 'timebucket'})

        years = [int(x.text) for x in timebuckets]

        for y in years: # generate urls for all months in the years we have articles
            yearUrl = response.url + "/" + str(y)
            for m in range(1, 12):
                monUrl = yearUrl + "/" + str(m)
                yield scrapy.Request(url=monUrl, callback=self.parse_month)

    def parse_month(self, response):
        """ get article links from days or months """

        monSoup = BeautifulSoup(str(response.text), features='lxml')
        allDays = monSoup.findAll("div", attrs={'class': 'timebucket'})
        if len(allDays) != 0: # if we do have days lets check the day pages
            for a in allDays:
                dayUrl = a.find("a")
                if dayUrl is not None: # it could be not linked
                    dayUrl = str(dayUrl['href'])
                    yield scrapy.Request(url=dayUrl, callback=self.parse_day)

        else: # get articles directly from month/year whatever we got directed to
            links = list(monSoup.findAll("div", attrs={"class": "postArticle-readMore"}))
            for l in links:
                articleLink = str(l.find("a")['href']).partition('?')[0]

                # params = {
                #     'api_key': os.getenv('SCRAPERAPI_KEY'),
                #     'url': articleLink.replace('https://', 'http://'),
                #     'render': 'true'
                # }
                # articleLink = API_BASE_URL + '?' + urllib.parse.urlencode(params)
                if articleLink not in self.seen_urls:
                    self.seen_urls.add(articleLink)
                    yield scrapy.Request(url=articleLink, callback=self.parse_article)

    def parse_day(self, response):
        """ get article links from days """

        daySoup = BeautifulSoup(str(response.text), features='lxml')
        links = list(daySoup.findAll("div", attrs={"class": "postArticle-readMore"}))
        for l in links:
            articleLink = str(l.find("a")['href']).partition('?')[0]

            # params = {
            #         'api_key': os.getenv('SCRAPERAPI_KEY'),
            #         'url': articleLink.replace('https://', 'http://'),
            #         'render': 'true'
            #     }
            # articleLink = API_BASE_URL + '?' + urllib.parse.urlencode(params)
            if articleLink not in self.seen_urls:
                self.seen_urls.add(articleLink)
                yield scrapy.Request(url=articleLink, callback=self.parse_article)

    def parse_article(self, response):
        """ bandcamp artist page parse """

        articleSoup = BeautifulSoup(str(response.text), features='lxml')

        # f = articleSoup.find_all("section", attrs={"class": "meteredContent"})

        item = {}
        item['url'] = response.url

        if len(item['url']) <= 200: # long urls are usually chinese or cryl encoded
            sections = articleSoup.find_all('section')
            story_paragraphs = []
            section_titles = []

            for section in sections:
                paragraphs = section.find_all('p')
                for paragraph in paragraphs:
                    story_paragraphs.append(paragraph.text)

                subs = section.find_all('h1')
                for sub in subs:
                    section_titles.append(sub.text)


            item['title'] = section_titles[0] if len(section_titles) != 0 else story_paragraphs[0]
            item['content'] = ''
            for p in story_paragraphs:
                item['content'] += p + '\n'
                
            item['content'] = clean_str(item['content'])

            yield item
