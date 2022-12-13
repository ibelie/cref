# #-*- coding: utf-8 -*-
# # Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# # Use of this source code is governed by The MIT License
# # that can be found in the LICENSE file.

# from stepflow.step import Step
# from stepflow import utils
# import matplotlib.pyplot as plt
# import os
# import stat
# import numpy as np
# import pandas as pd
# from fp_growth import find_frequent_itemsets

# GROUP = 'Result Outputer'


# # projectList = ['abydos']
# projectList = [
# "anaconda",
# "DataProcessor",
# "i8c",
# "abydos",
# "pyFDA",
# "gofer",
# "petl",
# "custodian",
# "WALinuxAgent",
# "TriFusion"]
# M = 6
# N = 2

# # 导出批量分析shell脚本

# #  .o8                     .             oooo              .oooooo..o     .                 .    o8o               .    o8o                      oooo       ooooooooo.
# # "888                   .o8             `888             d8P'    `Y8   .o8               .o8    `"'             .o8    `"'                      `888       `888   `Y88.
# #  888oooo.   .oooo.   .o888oo  .ooooo.   888 .oo.        Y88bo.      .o888oo  .oooo.   .o888oo oooo   .oooo.o .o888oo oooo   .ooooo.   .oooo.    888        888   .d88' oooo  oooo  ooo. .oo.   ooo. .oo.    .ooooo.  oooo d8b
# #  d88' `88b `P  )88b    888   d88' `"Y8  888P"Y88b        `"Y8888o.    888   `P  )88b    888   `888  d88(  "8   888   `888  d88' `"Y8 `P  )88b   888        888ooo88P'  `888  `888  `888P"Y88b  `888P"Y88b  d88' `88b `888""8P
# #  888   888  .oP"888    888   888        888   888            `"Y88b   888    .oP"888    888    888  `"Y88b.    888    888  888        .oP"888   888        888`88b.     888   888   888   888   888   888  888ooo888  888
# #  888   888 d8(  888    888 . 888   .o8  888   888       oo     .d8P   888 . d8(  888    888 .  888  o.  )88b   888 .  888  888   .o8 d8(  888   888        888  `88b.   888   888   888   888   888   888  888    .o  888
# #  `Y8bod8P' `Y888""8o   "888" `Y8bod8P' o888o o888o      8""88888P'    "888" `Y888""8o   "888" o888o 8""888P'   "888" o888o `Y8bod8P' `Y888""8o o888o      o888o  o888o  `V88V"V8P' o888o o888o o888o o888o `Y8bod8P' d888b


# class batchStatisticalRunner(Step):
# 	'generate a shell script of a batch of Statistical runners'

# 	REQUIRE = 'projectInfo',

# 	def load(self):
# 		return False

# 	def generate(self):
# 		with open('batch_runner.sh', 'w') as f:
# 			f.write('export PYTHONPATH=$(cd `dirname $0`; pwd)\n\n')
# 			for p in projectList:
# 				f.write('echo "Statistical run %s ..."\n' % p)
# 				f.write('python -B -m stepflow -s funProfileAST -p %s\n\n' % (p))
# 		os.chmod("batch_runner.sh", stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

# 		return False


# # oooooooooooo                                .oooooo.
# # `888'     `8                               d8P'  `Y8b
# #  888         oooo  oooo  ooo. .oo.        888           .ooooo.  oooo    ooo  .ooooo.  oooo d8b  .oooo.    .oooooooo  .ooooo.
# #  888oooo8    `888  `888  `888P"Y88b       888          d88' `88b  `88.  .8'  d88' `88b `888""8P `P  )88b  888' `88b  d88' `88b
# #  888    "     888   888   888   888       888          888   888   `88..8'   888ooo888  888      .oP"888  888   888  888ooo888
# #  888          888   888   888   888       `88b    ooo  888   888    `888'    888    .o  888     d8(  888  `88bod8P'  888    .o
# # o888o         `V88V"V8P' o888o o888o       `Y8bood8P'  `Y8bod8P'     `8'     `Y8bod8P' d888b    `Y888""8o `8oooooo.  `Y8bod8P'
# #                                                                                                           d"     YD
# #                                                                                                           "Y88888P'

# #每个版本中有多少函数发生了变化
# class funCoverageDrawer(Step):
# 	'get the coverage of funs for astDiff, profileDiff, profile'
# 	REQUIRE = ()

# 	def load(self):
# 		return False

# 	def generate(self):
# 		resultPath = 'data/result/%s/'%self.__class__.__name__
# 		not os.path.isdir(resultPath) and os.mkdir(resultPath)

# 		frames = []
# 		for project in projectList:
# 			path = 'data/result/funProfileCoverage/%s.json'%(project)
# 			rawList = utils.readData(path)
# 			# print rawDict
# 			df0 = pd.DataFrame()
# 			diffs = []
# 			astDiffCoverage = []
# 			astDiffNums = []
# 			coverages = []
# 			profileDiffCoverage = []
# 			profileDiffNums = []
# 			allFunsNums = []
# 			incFunsNums = []
# 			regFunsNums = []
# 			profileFunNums = []
# 			incFunsPercent = []
# 			regFunsPercent = []
# 			dateTime = []
# 			from datetime import datetime
# 			for i in rawList:
# 				# print i,project
# 				diffs.append(i[0])
# 				#astdiff个数,profileDiff,profileCoverage,StaticAnalyzer
# 				astDiffNums.append(i[1][0])
# 				profileDiffNums.append(i[1][1])
# 				profileFunNums.append(i[1][2])
# 				allFunsNums.append(i[1][3])

# 				if i[1][0] == None:astDiffCoverage.append(0)
# 				else:astDiffCoverage.append(i[1][0]/float(i[1][3]))
# 				if i[1][1] == None:profileDiffCoverage.append(0)
# 				else:profileDiffCoverage.append(i[1][1]/float(i[1][3]))
# 				coverages.append(i[1][2]/float(i[1][3]))

# 				incFunsNums.append(i[1][4])
# 				regFunsNums.append(i[1][5])

# 				if i[1][2]==0:
# 					incFunsPercent.append(0)
# 					regFunsPercent.append(0)
# 				else:
# 					incFunsPercent.append(i[1][4]/float(i[1][2]))
# 					regFunsPercent.append(i[1][5]/float(i[1][2]))

# 				dateTime.append(datetime.strptime(i[1][6],'%Y-%m-%d %H:%M:%S'))


# 			df0['diff'] = diffs
# 			df0['astDiffNums'] = astDiffNums
# 			df0['profileDiffNums'] = profileDiffNums
# 			df0['profileFunNums'] = profileFunNums
# 			df0['allFunsNums'] = allFunsNums

# 			df0['astDiffCoverage'] = astDiffCoverage
# 			df0['profileDiffCoverage'] = profileDiffCoverage
# 			df0['profileCoverage'] = coverages

# 			df0['incFunsNums'] = incFunsNums
# 			df0['regFunsNums'] = regFunsNums

# 			df0['incFunsPercent'] = incFunsPercent
# 			df0['regFunsPercent'] = regFunsPercent
# 			df0['dateTime'] = dateTime
# 			df0['project'] = project
# 			frames.append(df0)
# 		df = pd.concat(frames)
# 		df.to_csv(resultPath + "%s.csv"%(self.__class__.__name__))
# 		self._saveResult(0, df, "ast diff coverage ", 'build history', 'percent', lambda df: df[['astDiffCoverage']], resultPath)
# 		self._saveResult(1, df, "profile diff coverage ", 'build history', 'percent', lambda df: df[['profileDiffCoverage']], resultPath)
# 		self._saveResult(2, df, "profile coverage ", 'build history', 'percent', lambda df: df[['profileCoverage']], resultPath)
# 		self._saveResultProfileTime(3, df, "inc profile coverage ", 'build history', 'percent', lambda df: df['incFunsPercent'], lambda df: df['regFunsPercent'], resultPath)
# 		# self._saveResult(4, df, "reg profile coverage ", 'build history', 'percent', lambda df: df[['regFunsPercent']], resultPath)
# 		# self._saveInReProfile(3, df, "profile coverage ", 'build history', 'percent', lambda df: df[['incFunsPercent', 'regFunsPercent']], resultPath)

# 	def _saveResultProfileTime(self, j, df, title, xlabel, ylabel, dfContext1, dfContext2, resultPath):
# 		f = open(resultPath + "%s.txt"%(self.__class__.__name__),'w')
# 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# 		for i,project in enumerate(projectList):
# 			tempDf = df[df['project'] == project]
# 			f.write(project + "\n")
# 			f.write(str(tempDf.describe()) + "\n")
# 			f.write("\n********************************\n")
# 			resultDF1 = dfContext1(tempDf)
# 			resultDF1.index = pd.Index(tempDf['dateTime'])
# 			resultDF2 = dfContext2(tempDf)
# 			resultDF2.index = pd.Index(tempDf['dateTime'])
# 			utils.drawDF(axes[i/N][i-N*(i/N)], title+project, xlabel, ylabel, pd.rolling_mean(resultDF1,30))
# 			utils.drawDF(axes[i/N][i-N*(i/N)], title+project, xlabel, ylabel, pd.rolling_mean(resultDF2,30))
# 		plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))

# 	def _saveInReProfile(self, j, df, title, xlabel, ylabel, dfContext, resultPath):
# 		# fig, axes = plt.subplots(M,N,figsize=(50,50))
# 		resultDf = pd.DataFrame()
# 		for i,project in enumerate(projectList):
# 			tempDf = dfContext(df[df['project'] == project])
# 			lst = []
# 			for i in range(0,9):
# 				lst +=[i]*(len(tempDf)/10)
# 			lst+= [9]*(len(tempDf)-len(lst))
# 			tempDf['percent'] = lst
# 			resultDf = resultDf.append(tempDf.groupby('percent').agg('mean'))

# 		resultDf1 = pd.DataFrame({i:resultDf.ix[i]['incFunsPercent'].tolist() for i in range(0,10)})
# 		resultDf2 = pd.DataFrame({i:resultDf.ix[i]['regFunsPercent'].tolist() for i in range(0,10)})

# 		fig, axes = plt.subplots(1,2,figsize=(30,10))
# 		# axes.set_autoscaley_on(False)
# 		# plt.ylim([0,1])
# 		axes[0].set(ylim=[0, 0.15])
# 		axes[1].set(ylim=[0, 0.15])
# 		utils.drawDF(axes[0], title, xlabel, ylabel, resultDf1, 'boxplot')
# 		utils.drawDF(axes[1], title, xlabel, ylabel, resultDf2, 'boxplot')
# 		plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))
# 		resultDf1.to_csv(resultPath + "_inc%s.csv"%(self.__class__.__name__))
# 		resultDf2.to_csv(resultPath + "_reg%s.csv"%(self.__class__.__name__))
# 		print resultDf1.describe()
# 		print resultDf2.describe()
# 		# 	utils.drawDF(axes[i/N][i-N*(i/N)], title+project, xlabel, ylabel, dfContext(tempDf))
# 		# 	plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))

# 	def _saveResult(self, j, df, title, xlabel, ylabel, dfContext, resultPath):
# 		f = open(resultPath + "%s.txt"%(self.__class__.__name__),'w')
# 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# 		for i,project in enumerate(projectList):
# 			tempDf = df[df['project'] == project]
# 			f.write(project + "\n")
# 			f.write(str(tempDf.describe()) + "\n")
# 			f.write("\n********************************\n")
# 			utils.drawDF(axes[i/N][i-N*(i/N)], title+project, xlabel, ylabel, dfContext(tempDf))
# 		plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))

# #获取ast变化占profilediff的比例

# #                                .o88o.  o8o  oooo                       .o.                    .              .o8
# #                                888 `"  `"'  `888                      .888.                 .o8             "888
# # oo.ooooo.  oooo d8b  .ooooo.  o888oo  oooo   888   .ooooo.           .8"888.      .oooo.o .o888oo       .oooo888  oooo d8b  .oooo.   oooo oooo    ooo  .ooooo.  oooo d8b
# #  888' `88b `888""8P d88' `88b  888    `888   888  d88' `88b         .8' `888.    d88(  "8   888        d88' `888  `888""8P `P  )88b   `88. `88.  .8'  d88' `88b `888""8P
# #  888   888  888     888   888  888     888   888  888ooo888        .88ooo8888.   `"Y88b.    888        888   888   888      .oP"888    `88..]88..8'   888ooo888  888
# #  888   888  888     888   888  888     888   888  888    .o       .8'     `888.  o.  )88b   888 .      888   888   888     d8(  888     `888'`888'    888    .o  888
# #  888bod8P' d888b    `Y8bod8P' o888o   o888o o888o `Y8bod8P'      o88o     o8888o 8""888P'   "888"      `Y8bod88P" d888b    `Y888""8o     `8'  `8'     `Y8bod8P' d888b
# #  888
# # o888o
# class funProfileASTDrawer(Step):
# 	'get the AST of profile diff'
# 	REQUIRE = ()

# 	def load(self):
# 		return False

# 	def generate(self):
# 		resultPath = 'data/result/%s/'%self.__class__.__name__
# 		not os.path.isdir(resultPath) and os.mkdir(resultPath)

# 		frames = []
# 		for project in projectList:
# 			path = 'data/result/funProfileAST/%s.json'%(project)
# 			rawList = utils.readData(path)
# 			df0 = pd.DataFrame()
# 			diffs = []
# 			callerAST = []
# 			calleeAST = []
# 			selfAST = []
# 			otherAST = []
# 			profileDiffCoverage = []
# 			allProfileDiffFuns = []
# 			for i in rawList:
# 				if i[1][2]!=0:
# 					callerAST.append(i[1][0]/float(i[1][4]))
# 					calleeAST.append(i[1][1]/float(i[1][4]))
# 					selfAST.append(i[1][2]/float(i[1][4]))
# 					otherAST.append(i[1][3]/float(i[1][4]))
# 					allProfileDiffFuns.append(i[1][4])
# 					diffs.append(i[0])

# 			df0['diff'] = diffs
# 			df0['callerAST'] = callerAST
# 			df0['calleeAST'] = calleeAST
# 			df0['selfAST'] = selfAST
# 			df0['otherAST'] = otherAST
# 			df0['allProfileDiffFuns'] = allProfileDiffFuns
# 			df0['project'] = project
# 			frames.append(df0)
# 		df = pd.concat(frames)
# 		df.to_csv(resultPath + "%s.csv"%(self.__class__.__name__))
# 		self._saveResult(0, df, "caller percent ", 'build history', 'percent', lambda df: df[['callerAST']], resultPath)
# 		self._saveResult(1, df, "callee percent ", 'build history', 'percent', lambda df: df[['calleeAST']], resultPath)
# 		self._saveResult(2, df, "self percent ", 'build history', 'percent', lambda df: df[['selfAST']], resultPath)
# 		self._saveResult(3, df, "other percent ", 'build history', 'percent', lambda df: df[['otherAST']], resultPath)

# 	def _saveResult(self, j, df, title, xlabel, ylabel, dfContext, resultPath):
# 		f = open(resultPath + "%s.txt"%(self.__class__.__name__),'w')
# 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# 		for i,project in enumerate(projectList):
# 			tempDf = df[df['project'] == project]
# 			f.write(project + "\n")
# 			f.write(str(tempDf.describe()) + "\n")
# 			f.write("\n********************************\n")
# 			utils.drawDF(axes[i/N][i-N*(i/N)], title+project, xlabel, ylabel, dfContext(tempDf))
# 			plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))


# #  .o88o.                                    .o8   o8o   .o88o.  .o88o.                                                      .
# #  888 `"                                   "888   `"'   888 `"  888 `"                                                    .o8
# # o888oo  oooo  oooo  ooo. .oo.         .oooo888  oooo  o888oo  o888oo        .ooooo.   .ooooo.  oooo  oooo  ooo. .oo.   .o888oo
# #  888    `888  `888  `888P"Y88b       d88' `888  `888   888     888         d88' `"Y8 d88' `88b `888  `888  `888P"Y88b    888
# #  888     888   888   888   888       888   888   888   888     888         888       888   888  888   888   888   888    888
# #  888     888   888   888   888       888   888   888   888     888         888   .o8 888   888  888   888   888   888    888 .
# # o888o    `V88V"V8P' o888o o888o      `Y8bod88P" o888o o888o   o888o        `Y8bod8P' `Y8bod8P'  `V88V"V8P' o888o o888o   "888"
# # 函数发生了多少次变化
# class funDiffCountDrawer(Step):
# 	'get the AST of profile diff'
# 	REQUIRE = ()

# 	def load(self):
# 		return False

# 	def generate(self):
# 		resultPath = 'data/result/%s/'%self.__class__.__name__
# 		not os.path.isdir(resultPath) and os.mkdir(resultPath)

# 		frames = []
# 		for project in projectList:
# 			path = 'data/result/funDiffCount/%s.json'%(project)
# 			rawDict = utils.readData(path)
# 			df0 = pd.DataFrame()
# 			df0['astDiff'] = [i[0] for i in rawDict.itervalues()]
# 			df0['astDiffPercent'] = [float(i[0])/i[2] for i in rawDict.itervalues()]
# 			df0['profileDiff'] = [i[1] for i in rawDict.itervalues()]
# 			df0['profileDiffPercent'] = [float(i[1])/i[2] for i in rawDict.itervalues()]
# 			df0['profileIncPercent'] = [float(i[3])/i[2] for i in rawDict.itervalues()]
# 			df0['profileRegPercent'] = [float(i[4])/i[2] for i in rawDict.itervalues()]
# 			df0['project'] = project
# 			frames.append(df0)
# 		df = pd.concat(frames)
# 		df.to_csv(resultPath + "%s.csv"%(self.__class__.__name__))
# 		self._saveTextResult(df, resultPath)
# 		self._saveResult(0, df, "profileChange ", 'build history', 'percent', lambda df: df[['profileIncPercent']], resultPath)
# 		self._saveResult(1, df, "profileChange ", 'build history', 'percent', lambda df: df[['profileRegPercent']], resultPath)
# 		# self._saveResult(1, df, "profileChangeCount ", 'build history', 'percent', lambda df: df[['profileDiff']], resultPath)

# 	def _saveResult(self, j, df, title, xlabel, ylabel, dfContext, resultPath):
# 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# 		for i,project in enumerate(projectList):
# 			tempDf = df[df['project'] == project]
# 			utils.drawDF(axes[i/N][i-N*(i/N)], title+project, xlabel, ylabel, dfContext(tempDf))
# 			plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))

# 	def _saveTextResult(self, df, resultPath):
# 		f = open(resultPath + "%s.txt"%(self.__class__.__name__),'w')
# 		for i,project in enumerate(projectList):
# 			tempDf = df[df['project'] == project]
# 			tempDf1 = pd.DataFrame()
# 			tempDf1['astDiff'] = tempDf.groupby('astDiff').size()[1:]
# 			a = tempDf1['astDiff'].sum()
# 			tempDf1['percent'] = tempDf1['astDiff'].apply(lambda x: float(x)/a)
# 			tempDf2 = pd.DataFrame()
# 			tempDf2['profileDiff'] = tempDf.groupby('profileDiff').size()[1:]
# 			b = tempDf2['profileDiff'].sum()
# 			tempDf2['percent'] = tempDf2['profileDiff'].apply(lambda x: float(x)/b)
# 			f.write(project + "\n")
# 			f.write(str(tempDf.describe()) + "\n")
# 			f.write(str(tempDf1) + "\n%d, %d, %.2f\n"%(a,tempDf1['percent'].sum(), tempDf1['percent'][3:].sum()))
# 			f.write(str(tempDf2) + "\n%d, %d, %.2f\n"%(b,tempDf2['percent'].sum(), tempDf2['percent'][3:].sum()))
# 			f.write("\n********************************\n")
# 		f.close()

# #平凡模式

# #  .o88o.                              oooooooooooo                                                                     .        oooooooooo.    o8o   .o88o.  .o88o.
# #  888 `"                              `888'     `8                                                                   .o8        `888'   `Y8b   `"'   888 `"  888 `"
# # o888oo  oooo  oooo  ooo. .oo.         888         oooo d8b  .ooooo.   .ooooo oo oooo  oooo   .ooooo.  ooo. .oo.   .o888oo       888      888 oooo  o888oo  o888oo
# #  888    `888  `888  `888P"Y88b        888oooo8    `888""8P d88' `88b d88' `888  `888  `888  d88' `88b `888P"Y88b    888         888      888 `888   888     888
# #  888     888   888   888   888        888    "     888     888ooo888 888   888   888   888  888ooo888  888   888    888         888      888  888   888     888
# #  888     888   888   888   888        888          888     888    .o 888   888   888   888  888    .o  888   888    888 .       888     d88'  888   888     888
# # o888o    `V88V"V8P' o888o o888o      o888o        d888b    `Y8bod8P' `V8bod888   `V88V"V8P' `Y8bod8P' o888o o888o   "888"      o888bood8P'   o888o o888o   o888o
# #                                                                            888.
# #                                                                            8P'
# #                                                                            "
# class funFrequentDiffDrawer(Step):
# 	'get the AST of profile diff'
# 	REQUIRE = ()

# 	def load(self):
# 		return False

# 	def generate(self):
# 		allTransactions = []
# 		transactions = {'inc':[], 'reg':[]}
# 		for i,project in enumerate(projectList):
# 			path = 'data/result/funFrequentDiff/%s.json'%(project)
# 			projectTractions = utils.readData(path)
# 			allTransactions.extend(projectTractions)
# 			for diff, f, context, p, pj in projectTractions:
# 				if p < 0:
# 					transactions['inc'].append(set(context))
# 				else:
# 					transactions['reg'].append(set(context))
# 			print len(transactions['reg']),len(transactions['inc'])
# 		dataInc = tuple(find_frequent_itemsets(transactions['inc'], 6, True))
# 		dataReg = tuple(find_frequent_itemsets(transactions['reg'], 6, True))

# 		resultData = {'inc':[], 'reg':[]}
# 		for d, c in dataInc:
# 			context = set()
# 			for i in d:
# 				context.add(i)
# 			fileList = []
# 			for diff, f, t, p, pj in allTransactions:
# 				if not (set(d) - set(t)):
# 					fileList.append( (diff, f))
# 			resultData['inc'].append((context, c, fileList, pj))

# 		for d, c in dataReg:
# 			context = set()
# 			for i in d:
# 				context.add(i)
# 			fileList = []
# 			for diff, f, t, p, pj in allTransactions:
# 				if not (set(d) - set(t)):
# 					fileList.append( (diff, f))
# 			resultData['reg'].append((context, c, fileList, pj))

# 		print len(resultData['inc']), len(resultData['reg'])

# 		# cls = self.__class__
# 		# path = 'data/result/%s/%s.json'%(cls.__name__, cls.__name__)
# 		# utils.saveData(path, resultData)
# 		# # path2 = 'data/result/%s/%sReg.json'%(cls.__name__, self.flow.project)
# 		# # utils.saveData(path2, data2)
# 		# self.data = resultData

# 		resultList = {'inc':[], 'reg':[]}
# 		for i, (context_i, c_i, fileList_i, pj_i) in enumerate(resultData['inc']):
# 			isSub = False
# 			for j, (context_j, c_j, fileList_j, pj_j) in enumerate(resultData['inc']):
# 				if not (context_i - context_j) and c_i == c_j and fileList_i == fileList_j and i != j:
# 					isSub = True
# 					break
# 			not isSub and resultList['inc'].append((tuple(context_i), c_i, fileList_i, pj_i))
# 		for i, (context_i, c_i, fileList_i, pj_i) in enumerate(resultData['reg']):
# 			isSub = False
# 			for j, (context_j, c_j, fileList_j, pj_j) in enumerate(resultData['reg']):
# 				if not (context_i - context_j) and c_i == c_j and fileList_i == fileList_j and i != j:
# 					isSub = True
# 					break
# 			not isSub and resultList['reg'].append((tuple(context_i), c_i, fileList_i, pj_i))

# 		print len(resultList['inc']), len(resultList['reg'])
# 		cls = self.__class__
# 		path = 'data/result/%s.json'%(cls.__name__)
# 		utils.saveData(path, resultList)
# 		# path2 = 'data/result/%s/%sReg.json'%(cls.__name__, self.flow.project)
# 		# utils.saveData(path2, data2)
# 		self.data = resultList

# class funFrequentDiffDrawer_UniqueGit(Step):
# 	'Git diff with frequent diff'
# 	REQUIRE = ()

# 	ProjectList = [
# 		# ["anaconda", 2],
# 		# ["DataProcessor", 3],
# 		# ["i8c", 3],
# 		# ["abydos", 3],
# 		# ["pyFDA", 2],
# 		# ["gofer", 2],
# 		# ["petl", 3],
# 		# ["custodian", 4],
# 		# ["WALinuxAgent", 3],
# 		["TriFusion", 6],
# 	]

# 	GitDiff = {}

# 	def load(self):
# 		return False

# 	def _gitDiff(self, fq):
# 		data = {}
# 		for t, c, fs, ps in fq:
# 			if len(t) <= 1:
# 				continue
# 			for i, (d, f) in enumerate(fs):
# 				p = ps[i]
# 				if p not in self.GitDiff:
# 					path = 'data/%s/gitDiff.json' % p
# 					self.GitDiff[p] = utils.readData(path)
# 				gitDiff = self.GitDiff[p]
# 				if d not in gitDiff: continue
# 				gitDiff = gitDiff[d]
# 				if f not in gitDiff: continue
# 				gitDiff = gitDiff[f]
# 				if 'prev' not in gitDiff or 'post' not in gitDiff:
# 					continue
# 				if len(gitDiff['prev']) > 15 or len(gitDiff['post']) > 15:
# 					continue
# 				if (p, d, f) not in data:
# 					data[(p, d, f)] = set(t)
# 				else:
# 					data[(p, d, f)] |= set(t)
# 		for (p, d, f), t in data.iteritems():
# 			yield list(t), p, d, f, self.GitDiff[p][d][f]['prev'], self.GitDiff[p][d][f]['post']

# 	def generate(self):
# 		allData = set()
# 		# for operate in ('inc', ):
# 		# 	for frequentSize in (0.5, ) :
# 		# 		path = 'data/result/funFrequentDiffDrawer/all/%s/%s/funFrequentDiffDrawer_Unique.json'%(operate, frequentSize)
# 		# 		data = utils.readData(path)
# 		# 		data = list(self._gitDiff(data))
# 		# 		for _, p, d, f, _, _ in data:
# 		# 			allData.add((p, d, f))
# 		# 		path = 'data/result/funFrequentDiffDrawer/all/%s/%s/funFrequentDiffDrawer_UniqueGit.json'%(operate, frequentSize)
# 		# 		utils.saveData(path, data)

# 		for operate in ('inc', ):
# 			for project, frequentSize in self.ProjectList:
# 				path = 'data/result/funFrequentDiffDrawer/seperate/%s/%s/%s_Unique.json' % (operate, frequentSize, project)
# 				data = utils.readData(path)
# 				data = list(self._gitDiff(data))
# 				data = filter(lambda (_, p, d, f, __, ___): (p, d, f) not in allData, data)
# 				if len(data) <= 0:
# 					continue
# 				path = 'data/result/funFrequentDiffDrawer/seperate/%s/%s/%s_UniqueGit.json' % (operate, frequentSize, project)
# 				utils.saveData(path, data)

# #
# # # 计算各个builds中存在astDiff和profileDiff的函数个数
# #
# # #  .o88o.                         ooooo      ooo                                        oooooooooo.
# # #  888 `"                         `888b.     `8'                                        `888'   `Y8b
# # # o888oo  oooo  oooo  ooo. .oo.    8 `88b.    8  oooo  oooo  ooo. .oo.  .oo.    .oooo.o  888      888 oooo d8b  .oooo.   oooo oooo    ooo  .ooooo.  oooo d8b
# # #  888    `888  `888  `888P"Y88b   8   `88b.  8  `888  `888  `888P"Y88bP"Y88b  d88(  "8  888      888 `888""8P `P  )88b   `88. `88.  .8'  d88' `88b `888""8P
# # #  888     888   888   888   888   8     `88b.8   888   888   888   888   888  `"Y88b.   888      888  888      .oP"888    `88..]88..8'   888ooo888  888
# # #  888     888   888   888   888   8       `888   888   888   888   888   888  o.  )88b  888     d88'  888     d8(  888     `888'`888'    888    .o  888
# # # o888o    `V88V"V8P' o888o o888o o8o        `8   `V88V"V8P' o888o o888o o888o 8""888P' o888bood8P'   d888b    `Y888""8o     `8'  `8'     `Y8bod8P' d888b
# #
# #
# # class funNumsDrawer(Step):
# # 	'get the number of funs with astDiff and profileDiff'
# #
# # 	REQUIRE = ()
# #
# # 	def load(self):
# # 		return False
# #
# # 	def generate(self):
# # 		resultPath = 'data/result/%s/'%self.__class__.__name__
# # 		not os.path.isdir(resultPath) and os.mkdir(resultPath)
# #
# # 		frames = []
# # 		for project in projectList:
# # 			path = 'data/result/funNumsStatistic/%s.json'%(project)
# # 			df0 = pd.DataFrame(utils.readData(path))
# # 			df0['project'] = project
# # 			frames.append(df0)
# # 		df = pd.concat(frames)
# # 		df.to_csv(resultPath + "%s.csv"%(self.__class__.__name__))
# #
# # 		self._saveResult(0, df, "num of tracked, astDiff, profileDiff", 'build history', 'Num', lambda df: df[['astDiffNum', 'trackedNum', 'profileDiffNum']], resultPath)
# # 		self._saveResult(1, df, "percent of astDiff not tracked", 'build history', 'percent', lambda df: df[['astNotInTracked']], resultPath)
# # 		self._saveResult(2, df, "percent of profileDiff tracked", 'build history', 'percent', lambda df: df[['profileInTracked']], resultPath)
# # 		self._saveResult(3, df, "percent of astDiff with profileDiff", 'build history', 'percent', lambda df: df[['astInProfile']], resultPath)
# # 		self._saveResult(4, df, "percent of profileDiff with astDiff", 'build history', 'percent', lambda df: df[['profileInAst']], resultPath)
# # 		self._saveResult(5, df, "num of astDiff", 'build history', 'Num', lambda df: df.groupby('astDiffNum').size().cumsum(), resultPath)
# # 		self._saveResult(6, df, "num of trackedNum", 'build history', 'Num', lambda df: df.groupby('trackedNum').size().cumsum(), resultPath)
# # 		self._saveResult(7, df, "num of profileDiffNum", 'build history', 'Num', lambda df: df.groupby('profileDiffNum').size().cumsum(), resultPath)
# # 		self._saveResult(8, df, "num of astNotInTracked", 'build history', 'Num', lambda df: df.groupby('astNotInTracked').size().cumsum(), resultPath)
# # 		self._saveResult(9, df, "num of profileInTracked", 'build history', 'Num', lambda df: df.groupby('profileInTracked').size().cumsum(), resultPath)
# # 		self._saveResult(10, df, "num of astInProfile", 'build history', 'Num', lambda df: df.groupby('astInProfile').size().cumsum(), resultPath)
# # 		self._saveResult(11, df, "num of profileInAst", 'build history', 'Num', lambda df: df.groupby('profileInAst').size().cumsum(), resultPath)
# #
# # 	def _saveResult(self, j, df, title, xlabel, ylabel, dfContext, resultPath):
# # 		f = open(resultPath + "%s_%s.txt"%(self.__class__.__name__, j),'w')
# # 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# # 		for i,project in enumerate(projectList):
# # 			tempDf = df[df['project'] == project]
# # 			f.write(project + "\n")
# # 			f.write(str(tempDf.describe()) + "\n")
# # 			f.write("\n********************************\n")
# # 			utils.drawDF(axes[i/N][i-N*(i/N)], title, xlabel, ylabel, dfContext(tempDf))
# # 		f.close()
# # 		plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))
# #
# #
# # # 计算各个builds中存在astDiff和profileDiff的函数个数
# # class funEvolutionDrawer(Step):
# # 	'get the number of funs with astDiff and profileDiff'
# #
# # 	REQUIRE = ()
# #
# # 	def load(self):
# #
# # 		return False
# #
# # 	def generate(self):
# # 		resultPath = 'data/result/%s/'%self.__class__.__name__
# # 		not os.path.isdir(resultPath) and os.mkdir(resultPath)
# #
# # 		frames = []
# # 		for project in projectList:
# # 			path = 'data/result/funEvolStatistic/%s.json'%(project)
# # 			df0 = pd.DataFrame(utils.readData(path))
# # 			df0['project'] = project
# # 			frames.append(df0)
# # 		df = pd.concat(frames)
# # 		df.to_csv(resultPath + "%s.csv"%(self.__class__.__name__))
# #
# # 		self._saveResult(0, df, "astDiffSum", 'build history', 'percent of methods', lambda df: df.groupby('astSum').size().apply(lambda x:x/float(len(df))), resultPath, 'ast')
# # 		self._saveResult(1, df, "profileDiffSum", 'build history', 'Num', lambda df: df.groupby('profileSum').size().apply(lambda x:x/float(len(df))), resultPath, 'profile')
# # 		self._saveResult(2, df, "trackedSum", 'build history', 'Num', lambda df: df.groupby('trackedSum').size().apply(lambda x:x/float(len(df))), resultPath, 'tracked')
# # 		self._saveResult1(3, df, "profile_astDiffEvolution", 'build history', 'Num', lambda df: df[['profileDiff'+str(i) for i in range((df.columns.size-1)//3-1)]].apply(lambda x:x.sum()/float(len(df))), lambda df: df[['astDiff'+str(i) for i in range((df.columns.size-1)//3-1)]].apply(lambda x:x.sum()/float(len(df))), resultPath)
# #
# # 	def _saveResult(self,j, df, title, xlabel, ylabel, dfContext, resultPath, dfType):
# # 		resultDf = pd.DataFrame(columns=(["pname", "count", 'nochange' , 'once', 'twice', 'less3']))
# # 		f = open(resultPath + "%s_%s.txt"%(self.__class__.__name__, j),'w')
# # 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# # 		for i,project in enumerate(projectList):
# # 			tempDf = df[df['project'] == project]
# # 			resultDf.loc[i] = [project, len(tempDf), len(tempDf[tempDf[dfType+'Sum'] == 0])/float(len(tempDf)),len(tempDf[tempDf[dfType+'Sum'] == 1])/float(len(tempDf)),  len(tempDf[tempDf[dfType+'Sum'] == 2])/float(len(tempDf)), len(tempDf[tempDf[dfType+'Sum'] > 3])/float(len(tempDf))]
# # 			f.write(project + "\t" + dfType + "\n")
# # 			f.write(str(tempDf.describe()) + "\n")
# # 			f.write("\n********************************\n")
# # 			utils.drawDF(axes[i/N][i-N*(i/N)], title, xlabel, ylabel, dfContext(tempDf),'bar')
# # 		f.write(str(resultDf) + '\n')
# # 		f.write(str(resultDf.describe()))
# # 		f.close()
# # 		plt.tight_layout()
# # 		plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))
# #
# # 	def _saveResult1(self,j, df, title, xlabel, ylabel, dfContext1, dfContext2, resultPath):
# # 		f = open(resultPath + "%s_%s.txt"%(self.__class__.__name__, j),'w')
# # 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# # 		for i,project in enumerate(projectList):
# # 			tempDf = df[df['project'] == project].dropna(axis = 1 , how = 'all')
# # 			resultDf = pd.DataFrame({'profileDiff':dfContext1(tempDf).values, 'astDiff':dfContext2(tempDf).values})
# # 			f.write(project + "\n")
# # 			f.write(str(tempDf.describe()) + "\n")
# # 			f.write("\n********************************\n")
# # 			utils.drawDF(axes[i/N][i-N*(i/N)], title, xlabel, ylabel, resultDf)
# # 		f.close()
# # 		plt.tight_layout()
# # 		plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))
# #
# #
# #
# # # 计算各个builds中存在astDiff和profileDiff的函数个数
# # class funProfileEvolutionDrawer(Step):
# # 	'get the number of funs with astDiff and profileDiff'
# #
# # 	REQUIRE = ()
# #
# # 	def load(self):
# #
# # 		return False
# #
# # 	def generate(self):
# # 		resultPath = 'data/result/%s/'%self.__class__.__name__
# # 		not os.path.isdir(resultPath) and os.mkdir(resultPath)
# #
# # 		# frames = []
# # 		# for project in projectList:
# # 		# 	path = 'data/result/funProfileEvolStatistic/%s.json'%(project)
# # 		# 	df0 = pd.DataFrame(utils.readData(path))
# # 		# 	df0['project'] = project
# # 		# 	frames.append(df0)
# # 		# df = pd.concat(frames)
# # 		# df.to_csv(resultPath + "%s.csv"%(self.__class__.__name__))
# #
# # 		self._saveResult(0, "profileDiffValueEvolution", 'build history', 'Num', lambda df: df[['profileDiffValue'+str(i) for i in range(df.columns.size)]].apply(lambda x:x.sum()/float(len(df))), resultPath)
# #
# # 	def _saveResult(self,j, title, xlabel, ylabel, dfContext, resultPath):
# # 		f = open(resultPath + "%s_%s.txt"%(self.__class__.__name__, j),'w')
# # 		fig, axes = plt.subplots(M,N,figsize=(50,50))
# # 		for i,project in enumerate(projectList):
# # 			path = 'data/result/funProfileEvolStatistic/%s.json'%(project)
# # 			tempDf = pd.DataFrame(utils.readData(path))
# # 			print tempDf
# # 			raw_input()
# # 			print dfContext(tempDf)
# # 			raw_input()
# # 			f.write(project + "\n")
# # 			f.write(str(tempDf.describe()) + "\n")
# # 			f.write("\n********************************\n")
# # 			utils.drawDF(axes[i/N][i-N*(i/N)], title, xlabel, ylabel, dfContext(tempDf),'boxplot')
# # 		f.close()
# # 		plt.tight_layout()
# # 		plt.savefig(resultPath + "%s_%s.png"%(self.__class__.__name__, j))
