import collections
import csv
import os
import re
import string
import time
from pathlib import Path

HERE = Path(__file__).parent

def has_only_latin_letters(name):
    char_set = string.ascii_letters
    return all((True if x in char_set else False for x in name))

filenames = [filename for filename in os.listdir(HERE/'csv'/'skills') if filename.endswith('.txt')]

skills = []

for filename in filenames:
    with open(HERE/'csv'/'skills'/filename, 'r') as f:
        for skill in f.readlines():
            # start = time.perf_counter()
            skill = skill.strip()

            if not bool(re.search(r'[a-zA-Z]', skill)): # skip skills that have less than 3 chars
                continue

            if not skill.isascii(): # skip non-english skills
                continue
            
            # check if not already in set - Disabled as this bought execution time waay up obv
            # if skill.lower() not in [x.lower() for x in skills]:
                # skills.add(skill)
                # print(skill)
            # print(f'Execution took {round(time.perf_counter() - start, 5)}s')

            skills.append(skill)

# remove duplicates
wordset = collections.OrderedDict()
wordset = collections.OrderedDict.fromkeys(skills)
print(len(skills))
skills = [item for item in wordset if item.istitle() or item.title() not in wordset]
print(len(skills))

with open(HERE/'skills.csv', 'w') as f:
    writer = csv.writer(f)

    for row in sorted(skills):
        writer.writerow([row])
