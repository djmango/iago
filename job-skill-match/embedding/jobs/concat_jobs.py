import csv
import os
import re
from pathlib import Path

HERE = Path(__file__).parent

filenames = [filename for filename in os.listdir(HERE/'csv'/'jobs') if filename.endswith('.csv')]

jobs = set()
acronyms = ['SEO', 'SAP', 'AWS', '3D', 'HR', 'VP', 'CAD', 'CEO', 'CFO', 'CG', 'CTO', 'CNC', 'CMM', 'ASP', 'NET', 'PHP', 'ASIC', 'DJ', 'GCP', 'DevOps', 'GED', 'FX', 'GIS', 'HRD', 'HSE', 'IT', 'ICU', 'MRI', 'QA', 'RN', 'RF', 'SRE', 'SAS', 'SAT', 'SQL', 'UI', 'UX', 'AI']
acronyms_lower = [x.lower() for x in acronyms]

for filename in filenames:
    with open(HERE/'csv'/'jobs'/filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            title = str(row[0])

            # no all caps
            if title.isupper():
                title = title.capitalize()

            # check for acronyms and capitalize
            r = re.findall(r'\W(\w{1,10})\W', title) # for some reason we miss Asp.Net and only get the Net, i thought it was cuz of overlapping but at this point not sure, not really worth fixing atm
            if len(r) > 0:
                for orig_acronym in r:
                    if orig_acronym not in acronyms and orig_acronym.lower() in acronyms_lower: # compare in lowercase to match complex acronyms like DevOps  
                        title = title.replace(orig_acronym, acronyms[acronyms_lower.index(orig_acronym.lower())]) # basically find the index of the correct acronym using the lowercase compare and replace the occurance with said correct acronym
            # check if not already in set
            if title.lower() not in [job.lower() for job in jobs]:
                jobs.add(title.strip())
                print(title)

with open(HERE/'jobtitles.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Job Titles'])

    for row in sorted(jobs):
        writer.writerow([row])
