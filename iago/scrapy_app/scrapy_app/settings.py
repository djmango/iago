# Scrapy settings for scrapy_app project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import logging
import os
import sys
from pathlib import Path

import django
from django.core.cache import cache
from hide_my_name import HideMyName

# logging
# https://doc.scrapy.org/en/latest/topics/logging.html#logging-settings
LOG_FORMAT = '%(asctime)s %(levelname)s %(threadName)s [%(module)s:%(funcName)s:%(lineno)d] | %(message)s'
LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)

# DJANGO INTEGRATION
# https://alioguzhan.medium.com/how-to-use-scrapy-with-django-application-c16fabd0e62e
sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))  # this is to add the django project path to sys envs
os.environ['DJANGO_SETTINGS_MODULE'] = 'iago.settings'


django.setup()

# get proxies
hmn = HideMyName()
print('Getting proxies..')
proxies = cache.get('scrapy_hmn_proxies')
if not proxies or False:
    proxies = hmn.get_proxies(10)
    cache.set('scrapy_hmn_proxies', proxies, timeout=60 * 60 * 1)  # 1 hour
print(f'Got {len(proxies)} proxies!')

ROTATING_PROXY_LIST = [f'{x[0]}:{x[1]}' for x in proxies]

BOT_NAME = 'scrapy_app'

SPIDER_MODULES = ['scrapy_app.spiders']
NEWSPIDER_MODULE = 'scrapy_app.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'scrapy_app (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 16

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'scrapy_app.middlewares.ScrapyAppSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    'scrapy_app.middlewares.ScrapyAppDownloaderMiddleware': 543,
# }
DOWNLOADER_MIDDLEWARES = {
   'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
   'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
#    'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
#    'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'scrapy_app.pipelines.ScrapyAppPipeline': 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 60 * 60 * 1
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
