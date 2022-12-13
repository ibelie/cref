# import csv
# project_author = {}
# with open ("./data/projects.csv",'r') as f:
#     f_csv = csv.reader(f)
#     next(f_csv)
#     for row in f_csv:
#         project_author[row[0]] =row[1]

# # print(project_author)

# import os
# import json

# def saveData(path, data):
# 	folder = path.rpartition('/')[0]
# 	not os.path.isdir(folder) and os.makedirs(folder)
# 	with open(path, 'w') as f:
# 		json.dump(data, f, indent = 4, sort_keys = True)


# def readData(path):
# 	with open(path, 'r') as f:
# 		return json.load(f)

# allprojects = readData('./data/preparation copy/MemLeakProjects.json')
# new_project = {}
# for k,v in allprojects.items():
#     if k in project_author:
#         new_project[k]=v
# saveData('./data/preparation/MemLeakProjects.json',new_project)

import os
from os import path

fs = os.listdir('./data/memleak')
for f in fs:
    print(f)
    