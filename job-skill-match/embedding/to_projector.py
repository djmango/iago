import csv
import json
import pathlib
import time

start = time.perf_counter()

HERE = pathlib.Path(__file__).parent

# load thing
with open(HERE/'jobtitles_embedded.csv', 'r') as f:
    reader = csv.reader(f)
    names = []
    embeds = []
    for line in list(reader)[2:]:
        names.append(line[0])
        embed = line[1].replace('\'', '').replace('{', '[').replace('}', ']') # idk why dbeaver exports lists like this
        embeds.append(json.loads(embed))

# write names
with open(HERE/'jobtitles.tsv', 'w') as f:
    writer = csv.writer(f, delimiter='\t')
    for line in names:
        writer.writerow([line])

# write embed with each dimension as a column
with open(HERE/'embeds.tsv', 'w') as f:
    writer = csv.writer(f, delimiter='\t')
    for line in embeds:
        writer.writerow(line)
