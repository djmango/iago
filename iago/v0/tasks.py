from v0.utils import RepeatedTimer
import requests


def keepLambdasHot(interval: float = 60.0):
    RepeatedTimer(interval, requests.get, 'https://api.dev.jeeny.ai/status')
    RepeatedTimer(interval, requests.get, 'https://api.staging.jeeny.ai/status')
    RepeatedTimer(interval, requests.get, 'https://api.qa.jeeny.ai/status')
