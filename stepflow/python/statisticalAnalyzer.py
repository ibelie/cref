#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils
import os
import stat
# import numpy as np
# import pandas as pd
import shutil
import time
import re

GROUP = 'Statistical Analyzer'


#  .oooooo..o     .                 .    o8o                       .o.                             oooo
# d8P'    `Y8   .o8               .o8    `"'                      .888.                            `888
# Y88bo.      .o888oo  .oooo.   .o888oo oooo   .ooooo.           .8"888.     ooo. .oo.    .oooo.    888  oooo    ooo   oooooooo  .ooooo.
#  `"Y8888o.    888   `P  )88b    888   `888  d88' `"Y8         .8' `888.    `888P"Y88b  `P  )88b   888   `88.  .8'   d'""7d8P  d88' `88b
#      `"Y88b   888    .oP"888    888    888  888              .88ooo8888.    888   888   .oP"888   888    `88..8'      .d8P'   888ooo888
# oo     .d8P   888 . d8(  888    888 .  888  888   .o8       .8'     `888.   888   888  d8(  888   888     `888'     .d8P'  .P 888    .o
# 8""88888P'    "888" `Y888""8o   "888" o888o `Y8bod8P'      o88o     o8888o o888o o888o `Y888""8o o888o     .8'     d8888888P  `Y8bod8P'

# 运行java分析工具，获取静态分析数据
class funStaticAnalyze(Step):
	'Get all funs in pythonProject by java tool'

	REQUIRE = 'gitRepo', 'fileDiff',

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return False

	def generate(self):
		cls = self.__class__
		for ver in self.flow.fileDiff.versions:
			path = "data/%s/%s/%s.json" % (self.flow.project, cls.__name__, ver)
			if os.path.isfile(path): continue
			path = 'data/%s' % self.flow.project
			not os.path.isdir(path+"/%s/temp" % (cls.__name__)) and os.makedirs(path+"/%s/temp" % (cls.__name__))
			cmd = 'git --git-dir=%s/.git archive --format=tar %s . | gzip -9 > ../%s/temp/%s.tar.gz' % (self.flow.gitRepo.path, ver, cls.__name__, ver)
			not os.path.isdir(path) and os.makedirs(path)
			result = os.system(cmd)
			inputPath = "%s/%s/temp/%s" % (path, cls.__name__, ver)
			outputPath = "%s/%s"%(path, cls.__name__)
			not os.path.isdir(inputPath) and os.makedirs(inputPath)
			cmd = "tar -zxf %s/%s/temp/%s.tar.gz -C %s" % (path, cls.__name__, ver, inputPath)
			os.system(cmd)
			os.system("java -jar java/StaticAnalyzer.jar %s %s %s" % (inputPath, outputPath, ver))
			shutil.rmtree(inputPath)
			os.remove("%s/%s/temp/%s.tar.gz" % (path, cls.__name__, ver))

		data = {}
		for ver in self.flow.fileDiff.versions:
			path = "data/%s/%s/%s.json" % (self.flow.project, cls.__name__, ver)
			if os.path.exists(path):
				data[ver] = self._reorganize(utils.readData(path), "data/%s/%s/temp/%s/"%(self.flow.project, cls.__name__, ver))

		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, data)
		self.data = data

		return True

	def _reorganize(self, rawData, path):
		newData = {}
		for f in rawData['files']:
			fName = f['node'].split(path)[1].replace(')',"")
			funs = []
			for fun in f['Funs']:
				funs.append((fun['node'], fun['lineno']))
			newData[fName] = funs
		return newData


# ooooooooo.                       .o88o.        .oooooo.
# `888   `Y88.                     888 `"       d8P'  `Y8b
#  888   .d88' oooo d8b  .ooooo.  o888oo       888           .ooooo.  oooo    ooo  .ooooo.  oooo d8b
#  888ooo88P'  `888""8P d88' `88b  888         888          d88' `88b  `88.  .8'  d88' `88b `888""8P
#  888          888     888   888  888         888          888   888   `88..8'   888ooo888  888
#  888          888     888   888  888         `88b    ooo  888   888    `888'    888    .o  888
# o888o        d888b    `Y8bod8P' o888o         `Y8bood8P'  `Y8bod8P'     `8'     `Y8bod8P' d888b

class funProfileCoverage(Step):
	'get the coverage of ProfileData'

	REQUIRE = 'profileData', 'profileDiff', 'astDiff', 'fileDiff', 'funStaticAnalyze', 'buildCommits'

	def load(self):
		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		self.data = utils.readData(path)
		return False

	def generate(self):
		data = {}
		for diff, fs in self.flow.profileData.data.iteritems():
			prev = diff[:10]
			post = diff[-10:]
			prevSet = data.setdefault(prev, set())
			postSet = data.setdefault(post, set())
			for f_n, d in fs.iteritems():
				if d['mark'] == 'update':
					prevSet.add(f_n)
					postSet.add(f_n)
				# elif d['mark'] == 'add':
				# 	postSet.add(f_n)
				# elif d['mark'] == 'remove':
				# 	prevSet.add(f_n)

		data = {k: len(v) for k, v in data.iteritems()}
		for ver, f_funs in self.flow.funStaticAnalyze.data.iteritems():
			funNums = 0
			for funs in f_funs.itervalues():
				funNums += len(funs)
			data[ver] = (data[ver], funNums)
		for k, v in data.iteritems():
			if not isinstance(v, tuple):
				data[k] = (v, None)

		for diff in self.flow.fileDiff.diffs:
			astDiff = self.flow.astDiff.data[diff]
			profileDiff = self.flow.profileDiff.data[diff]
			ver = diff[:10]
			astDiff = filter(lambda fs: filter(lambda f: f['action'] != 'INS', fs), astDiff.itervalues())
			profileDiff = filter(lambda p: p['mark'] != 'add', profileDiff.itervalues())
			inc = 0
			reg = 0
			for f in profileDiff:
				if f['totTime'][2]<0:
					inc+=1
				else:
					reg+=1

			data[ver] = (len(astDiff), len(profileDiff), data[ver][0], data[ver][1], inc, reg)

		# TIME_FORMAT = '%Y-%m-%d'
		# print time.mktime(time.strptime('2011-10-12', TIME_FORMAT))
		# print time.time()
		for k, v in data.iteritems():
			if len(v) == 2:
				data[k] = (None, None, v[0], v[1], 0, 0)

		from datetime import datetime
		for v, c in self.flow.buildCommits.commits.iteritems():
			v = v[:10]
			if v in data:
				ct = time.ctime(c['timestamp'])
				gmt = time.strptime(ct)
				data[v] += (str(datetime(gmt.tm_year, gmt.tm_mon, gmt.tm_mday)), )


		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		utils.saveData(path, [(k,data[k]) for k in self.flow.fileDiff.versions])
		#astdiff个数,profileDiff,profileCoverage,StaticAnalyzer
		self.data = data

		return True


# ooooooooo.                       .o88o.            .o.        .oooooo..o ooooooooooooo
# `888   `Y88.                     888 `"           .888.      d8P'    `Y8 8'   888   `8
#  888   .d88' oooo d8b  .ooooo.  o888oo           .8"888.     Y88bo.           888
#  888ooo88P'  `888""8P d88' `88b  888            .8' `888.     `"Y8888o.       888
#  888          888     888   888  888           .88ooo8888.        `"Y88b      888
#  888          888     888   888  888          .8'     `888.  oo     .d8P      888
# o888o        d888b    `Y8bod8P' o888o        o88o     o8888o 8""88888P'      o888o

class funProfileAST(Step):
	'get the AST of profile diff'

	REQUIRE = 'profileTraceDiff', 'profileDiff'

	def load(self):
		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		self.data = utils.readData(path)
		return False

	def generate(self):
		data = {}
		a_CallerAST = .0
		a_CalleeAST = .0
		a_SelfAST = .0
		a_OtherAST = .0
		a_totalCount = .0
		for diff, fs in self.flow.profileDiff.data.iteritems():
			callerAST = .0
			calleeAST = .0
			selfAST = .0
			OtherAST = .0
			totalCount = .0
			#遍历有性能变化的函数
			for f in fs:
				totalCount += 1
				_, _, tv, er, ee = self.flow.profileTraceDiff.data[diff][f]
				if tv:
					selfAST += 1
				if ee:
					calleeAST += 1
				if er:
					callerAST += 1
				if not tv and not er and not ee:
					OtherAST += 1

			a_CallerAST += callerAST
			a_CalleeAST += calleeAST
			a_SelfAST += selfAST
			a_OtherAST += OtherAST
			a_totalCount += totalCount
			data[diff] = (callerAST, calleeAST, selfAST, OtherAST, totalCount)

		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		utils.saveData(path, [(k,data[k]) for k in self.flow.fileDiff.diffs])
		self.data = data
		print 'profile no ast diff: %4d %4d %4d %4d %4d %6.3f%% %6.3f%% %6.3f%% %6.3f%%' % (a_CallerAST, a_CalleeAST, a_SelfAST, a_OtherAST, a_totalCount, a_CallerAST / a_totalCount * 100, a_CalleeAST / a_totalCount * 100, a_SelfAST / a_totalCount * 100, a_OtherAST / a_totalCount * 100)

		return True


# oooooooooo.    o8o   .o88o.  .o88o.        .oooooo.                                         .
# `888'   `Y8b   `"'   888 `"  888 `"       d8P'  `Y8b                                      .o8
#  888      888 oooo  o888oo  o888oo       888           .ooooo.  oooo  oooo  ooo. .oo.   .o888oo
#  888      888 `888   888     888         888          d88' `88b `888  `888  `888P"Y88b    888
#  888      888  888   888     888         888          888   888  888   888   888   888    888
#  888     d88'  888   888     888         `88b    ooo  888   888  888   888   888   888    888 .
# o888bood8P'   o888o o888o   o888o         `Y8bood8P'  `Y8bod8P'  `V88V"V8P' o888o o888o   "888"

class funDiffCount(Step):
	'get the diff count of functions'

	REQUIRE = 'profileDiff', 'astDiff'

	def load(self):
		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		self.data = utils.readData(path)
		return False

	def generate(self):
		data = {}
		for diff, astDiff in self.flow.astDiff.data.iteritems():
			for func in astDiff:
				data.setdefault(func, [0, 0, 0, 0, 0])
				data[func][0] += 1
		for diff, profileDiff in self.flow.profileDiff.data.iteritems():
			for func in profileDiff:
				data.setdefault(func, [0, 0, 0, 0, 0])
				data[func][1] += 1
				if profileDiff[func]['totTime'][2] < 0:
					data[func][3] += 1
				else:
					data[func][4] += 1
		for func in data:
			data[func][2] = len(self.flow.fileDiff.versions)

		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		utils.saveData(path, data)
		self.data = data

		return True


# oooooooooooo                                                                     .        oooooooooo.    o8o   .o88o.  .o88o.
# `888'     `8                                                                   .o8        `888'   `Y8b   `"'   888 `"  888 `"
#  888         oooo d8b  .ooooo.   .ooooo oo oooo  oooo   .ooooo.  ooo. .oo.   .o888oo       888      888 oooo  o888oo  o888oo
#  888oooo8    `888""8P d88' `88b d88' `888  `888  `888  d88' `88b `888P"Y88b    888         888      888 `888   888     888
#  888    "     888     888ooo888 888   888   888   888  888ooo888  888   888    888         888      888  888   888     888
#  888          888     888    .o 888   888   888   888  888    .o  888   888    888 .       888     d88'  888   888     888
# o888o        d888b    `Y8bod8P' `V8bod888   `V88V"V8P' `Y8bod8P' o888o o888o   "888"      o888bood8P'   o888o o888o   o888o
#                                       888.
#                                       8P'
#                                       "
class funFrequentDiff(Step):
	'get the frequente diff of functions'

	REQUIRE = ('profileDiff',  'astDiff')

	def load(self):
		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		self.data = utils.readData(path)
		return False

	def generate(self):
		# transactions = {'inc':[], 'reg':[]}

		# transactionsInc = [
		# 	['milk', 'egg', 'bread', 'chips'],
		# 	['egg', 'popcorn', 'chips', 'bear'],
		# 	['egg', 'bread', 'chips'],
		# 	['milk', 'egg', 'bread', 'popcorn', 'chips', 'bear'],
		# 	['milk', 'bread', 'bear'],
		# 	['egg', 'bread', 'bear'],
		# 	['milk', 'bread', 'chips'],
		# 	['milk', 'egg', 'bread', 'butter', 'chips'],
		# 	['milk', 'egg', 'butter', 'chips'],
		# ]
		allTransactions = []
		for diff, fs in self.flow.profileDiff.data.iteritems():
			astDiff = self.flow.astDiff.data[diff]

			for f, p in fs.iteritems():
				if 'trifusion/tests/test_' in f:
					continue
				if f in astDiff:
					context = set()
					for d in astDiff[f]:
						if 'node' in d:
							nodeContext = re.sub('[0-9]+', '', d['node'])
							context.add(utils.getStringKeys(nodeContext , d['type'] , d['action']))
					allTransactions.append((diff, f, tuple(context), p['totTime'][2], self.flow.project))
					# if p['totTime'][2]<0:
					# 	transactionsInc.append(context)
					# else:
					# 	transactionsReg.append(context)
		# print len(transactionsReg),len(transactionsInc)
		# dataInc = tuple(find_frequent_itemsets(transactionsInc, 6, True))
		# dataReg = tuple(find_frequent_itemsets(transactionsReg, 6, True))
		#
		# resultData = {'inc':[], 'reg':[]}
		# for d, c in dataInc:
		# 	context = set()
		# 	for i in d:
		# 		context.add(i)
		# 	fileList = []
		# 	for diff, f, t in allTransactions:
		# 		if not (set(d) - t):
		# 			fileList.append( (diff, f))
		# 	resultData['inc'].append((context, c, fileList))
		#
		# for d, c in dataReg:
		# 	context = set()
		# 	for i in d:
		# 		context.add(i)
		# 	fileList = []
		# 	for diff, f, t in allTransactions:
		# 		if not (set(d) - t):
		# 			fileList.append( (diff, f))
		# 	resultData['reg'].append((context, c, fileList))
		#
		# print len(resultData['inc']), len(resultData['reg'])
		#
		# resultList = {'inc':[], 'reg':[]}
		# for i, (context_i, c_i, fileList_i) in enumerate(resultData['inc']):
		# 	isSub = False
		# 	for j, (context_j, c_j, fileList_j) in enumerate(resultData['inc']):
		# 		if not (context_i - context_j) and c_i == c_j and fileList_i == fileList_j and i != j:
		# 			isSub = True
		# 			break
		# 	not isSub and resultList['inc'].append((tuple(context_i), c_i, fileList_i))
		# for i, (context_i, c_i, fileList_i) in enumerate(resultData['reg']):
		# 	isSub = False
		# 	for j, (context_j, c_j, fileList_j) in enumerate(resultData['reg']):
		# 		if not (context_i - context_j) and c_i == c_j and fileList_i == fileList_j and i != j:
		# 			isSub = True
		# 			break
		# 	not isSub and resultList['reg'].append((tuple(context_i), c_i, fileList_i))

		# print len(resultList['inc']), len(resultList['reg'])
		cls = self.__class__
		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
		utils.saveData(path, allTransactions)
		# path2 = 'data/result/%s/%sReg.json'%(cls.__name__, self.flow.project)
		# utils.saveData(path2, data2)
		self.data = allTransactions

		return True


#
# # 计算各个builds中存在astDiff变化的函数所占的比例
# class astPercent(Step):
# 	'get the percent of funs with ast change'
#
# 	REQUIRE = 'astDiff', 'funStaticAnalyze'
#
# 	def load(self):
# 		return False
#
# 	def generate(self):
# 		data = {'astDiffNum':[], 'trackedNum':[], 'profileDiffNum':[], \
# 		'astNotInTracked':[], 'astInProfile':[], 'profileInAst':[], 'profileInTracked':[]}
# 		for diff in self.flow.fileDiff.index:
# 			astDiff = set(self.flow.astDiff.data[diff].iterkeys())
# 			tracked = set(self.flow.profileData.data[diff].iterkeys())
# 			profileDiff = set(self.flow.profileDiff.data[diff].iterkeys())
# 			#分析astDiff中有多少函数没没有被tracked的
# 			if(len(astDiff) != 0):
# 				data['astNotInTracked'].append(len(astDiff - tracked)/float(len(astDiff)))
# 			else:
# 				data['astNotInTracked'].append(0)
# 			#分析profileDiff中有多少比例发生了astDiff
# 			if len(profileDiff) != 0:
# 				data['astInProfile'].append(len(profileDiff & astDiff)/float(len(profileDiff)))
# 			else:
# 				data['astInProfile'].append(1)
# 			#分析astDiff中共有多少比例发生了profileDiff
# 			if len(astDiff) != 0:
# 				data['profileInAst'].append(len(profileDiff & astDiff)/float(len(astDiff)))
# 			else:
# 				data['profileInAst'].append(1)
# 			#分析profileDiff在tracked中的比例
# 			if len(tracked)!=0:
# 				data['profileInTracked'].append(len(profileDiff)/float(len(tracked)))
# 			else:
# 				data['profileInTracked'].append(0)
# 			#分析总共有多少tracked,astDiff,profileDiff
# 			data['astDiffNum'].append(len(astDiff))
# 			data['trackedNum'].append(len(tracked))
# 			data['profileDiffNum'].append(len(profileDiff))
#
# 		cls = self.__class__
# 		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
# 		utils.saveData( path, data )
#
# 		return True
#
# # 从时间维度对单个函数的统计
# class funEvolStatistic(Step):
# 	'get the number of funs with astDiff and profileDiff'
#
# 	REQUIRE = 'astDiff', 'profileData','fileDiff', 'transition','profileDiff'
#
# 	def load(self):
# 		return False
#
# 	def generate(self):
# 		diffNums = len(self.flow.fileDiff.index)
# 		df = pd.DataFrame(columns=(\
# 		['astDiff' + str(i) for i in range(diffNums)] + \
# 		['profileDiff' + str(i) for i in range(diffNums)] + \
# 		['tracked' + str(i) for i in range(diffNums)]))
#
# 		funs = set()
# 		for diff in self.flow.fileDiff.index:
# 			astDiff = set(self.flow.astDiff.data[diff].iterkeys())
# 			tracked = set(self.flow.profileData.data[diff].iterkeys())
# 			profileDiff = set(self.flow.profileDiff.data[diff].iterkeys())
# 			funs = funs | astDiff | tracked | profileDiff
#
# 		for i, fun in enumerate(funs):
# 			df.loc[i] = [ fun in self.flow.astDiff.data[diff].iterkeys() for diff in self.flow.fileDiff.index] + \
# 			[fun in self.flow.profileDiff.data[diff].iterkeys() for diff in self.flow.fileDiff.index] + \
# 			[fun in self.flow.profileData.data[diff].iterkeys() for diff in self.flow.fileDiff.index]
#
# 		df['astSum'] = df[['astDiff'+str(i) for i in range(len(self.flow.fileDiff.index))]].apply(lambda x:x.sum(), axis=1)
# 		df['profileSum'] = df[['profileDiff'+str(i) for i in range(len(self.flow.fileDiff.index))]].apply(lambda x:x.sum(), axis=1)
# 		df['trackedSum'] = df[['tracked'+str(i) for i in range(len(self.flow.fileDiff.index))]].apply(lambda x:x.sum(), axis=1)
#
# 		cls = self.__class__
# 		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
# 		with open(path, 'w') as f:
# 			f.write(df.to_json())
#
# 		return True
#
#
# # 从时间维度对单个函数性能变化的统计
# class funProfileEvolStatistic(Step):
# 	'get the number of funs with astDiff and profileDiff'
#
# 	REQUIRE = 'astDiff', 'profileData','fileDiff', 'transition','profileDiff'
#
# 	def load(self):
# 		return False
#
# 	def generate(self):
# 		diffNums = len(self.flow.fileDiff.index)
# 		df = pd.DataFrame(columns=(['profileDiffValue' + str(i) for i in range(diffNums)]))
#
# 		for diff in self.flow.fileDiff.index:
# 			funs = set(self.flow.profileDiff.data[diff].iterkeys())
# 		for i, fun in enumerate(funs):
# 			funDiffList = []
# 			for diff in self.flow.fileDiff.diffs:
# 				if fun in self.flow.profileDiff.data[diff]:
# 					funDiffList.append(self.flow.profileDiff.data[diff][fun]['cumTime'][2])
# 				else:
# 					funDiffList.append(None)
# 			df.loc[i] = funDiffList
#
# 		cls = self.__class__
# 		path = 'data/result/%s/%s.json'%(cls.__name__, self.flow.project)
# 		with open(path, 'w') as f:
# 			f.write(df.to_json())
#
# 		return True
