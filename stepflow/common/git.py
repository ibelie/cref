#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils
import time
import os
import re

GROUP = 'Git'


#             o8o      .        ooooooooo.
#             `"'    .o8        `888   `Y88.
#  .oooooooo oooo  .o888oo       888   .d88'  .ooooo.  oo.ooooo.   .ooooo.
# 888' `88b  `888    888         888ooo88P'  d88' `88b  888' `88b d88' `88b
# 888   888   888    888         888`88b.    888ooo888  888   888 888   888
# `88bod8P'   888    888 .       888  `88b.  888    .o  888   888 888   888
# `8oooooo.  o888o   "888"      o888o  o888o `Y8bod8P'  888bod8P' `Y8bod8P'
# d"     YD                                             888
# "Y88888P'                                            o888o

# 获取git版本库
class gitRepo(Step):
	'git clone repository'

	REQUIRE = 'projectInfo',

	def load(self):
		if not self.flow.project: return True
		cls = self.__class__
		self.path = os.path.abspath('data/%s/%s' % (cls.__name__, self.flow.project))
		return os.path.isdir(self.path)

	def generate(self):
		if not self.flow.project: return True
		self.path = self.prepare(self.flow.project)
		return self.path is not None

	def prepare(self, project):
		cls = self.__class__
		path = os.path.abspath('data/%s/%s' % (cls.__name__, project))
		if os.path.isdir(path): return path
		cmd = 'git clone %s %s' % (self.flow.projectInfo.get_repo(project), path)
		if os.path.isfile(path):
			os.remove(path)
		dirname = os.path.dirname(path)
		not os.path.isdir(dirname) and os.mkdir(dirname)
		if os.system(cmd) == 0:
			return path
		return None

	def clone(self, name):
		path = os.path.abspath('data/gitClone/%s/%s' % (self.flow.project, name))
		if os.path.isfile(path):
			os.remove(path)
		if not os.path.isdir(path):
			dirname = os.path.dirname(path)
			not os.path.isdir(dirname) and os.mkdir(dirname)
			cmd = 'git clone %s %s' % (self.path, path)
			if os.system(cmd) != 0: return None
		return path


#  .o8                    o8o  oooo        .o8         .oooooo.                                                  o8o      .
# "888                    `"'  `888       "888        d8P'  `Y8b                                                 `"'    .o8
#  888oooo.  oooo  oooo  oooo   888   .oooo888       888           .ooooo.  ooo. .oo.  .oo.   ooo. .oo.  .oo.   oooo  .o888oo  .oooo.o
#  d88' `88b `888  `888  `888   888  d88' `888       888          d88' `88b `888P"Y88bP"Y88b  `888P"Y88bP"Y88b  `888    888   d88(  "8
#  888   888  888   888   888   888  888   888       888          888   888  888   888   888   888   888   888   888    888   `"Y88b.
#  888   888  888   888   888   888  888   888       `88b    ooo  888   888  888   888   888   888   888   888   888    888 . o.  )88b
#  `Y8bod8P'  `V88V"V8P' o888o o888o `Y8bod88P"       `Y8bood8P'  `Y8bod8P' o888o o888o o888o o888o o888o o888o o888o   "888" 8""888P'

# 获取每个版本的提交时间，按照先后顺序对buildHistory中的各个版本进行排序
class buildCommits(Step):
	'sort build history by commit log'

	REQUIRE = 'buildHistory', 'gitRepo'

	TIME_FORMAT = '%a %b %d %H:%M:%S %Y'
	GIT_LOG_CMD = 'git --git-dir=%s/.git log --date=local --pretty=format:"%%H %%cd %%P"'

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.commits = utils.readData(path)
		self.data = sorted(self.flow.buildHistory.data.itervalues(),
			key = lambda build: self.commits[build['commit']]['timestamp'])
		return True

	def generate(self):
		commits = {}
		with os.popen(self.GIT_LOG_CMD % self.flow.gitRepo.path) as proc:
			a = 0
			b = 0
			c = 0
			line = proc.readline()
			while line:
				a=a+1
				commit, _, date_parent = line.partition(' ')
				date_parent = date_parent.split(' ')

				if len(date_parent[5:]) > 1:
					print 'ignore commit with parents:', date_parent[5:]
					line = proc.readline()
					b=b+1
					continue
				date = ' '.join(date_parent[:5])
				if commit not in self.flow.buildHistory.data:
					line = proc.readline()
					continue
				date = date.strip()
				timestamp = time.mktime(time.strptime(date, self.TIME_FORMAT))
				# assert time.strftime(self.TIME_FORMAT, time.localtime(timestamp)) == date, repr((timestamp, date, time.strftime(self.TIME_FORMAT, time.localtime(timestamp))))
				commits[commit] = {
					'date': date,
					'timestamp': timestamp,
				}
				c=c+1
				if 'parentID' in self.flow.buildHistory.data[commit]:
					commits[commit]['parentID'] = self.flow.buildHistory.data[commit]['parentID']
				if 'authorName' in self.flow.buildHistory.data[commit]:
					commits[commit]['authorName'] = self.flow.buildHistory.data[commit]['authorName']
				line = proc.readline()
		print len(commits),len(self.flow.buildHistory.data)
		print a, b, c
		self.data = sorted((b for b in self.flow.buildHistory.data.itervalues() if b['commit'] in commits),
			key = lambda build: commits[build['commit']]['timestamp'])

		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, commits)
		self.commits = commits

		return True


#           oooo                                                         .o8         .oooooo.                   .o8
#           `888                                                        "888        d8P'  `Y8b                 "888
#  .ooooo.   888 .oo.    .oooo.   ooo. .oo.    .oooooooo  .ooooo.   .oooo888       888           .ooooo.   .oooo888   .ooooo.   .oooo.o
# d88' `"Y8  888P"Y88b  `P  )88b  `888P"Y88b  888' `88b  d88' `88b d88' `888       888          d88' `88b d88' `888  d88' `88b d88(  "8
# 888        888   888   .oP"888   888   888  888   888  888ooo888 888   888       888          888   888 888   888  888ooo888 `"Y88b.
# 888   .o8  888   888  d8(  888   888   888  `88bod8P'  888    .o 888   888       `88b    ooo  888   888 888   888  888    .o o.  )88b
# `Y8bod8P' o888o o888o `Y888""8o o888o o888o `8oooooo.  `Y8bod8P' `Y8bod88P"       `Y8bood8P'  `Y8bod8P' `Y8bod88P" `Y8bod8P' 8""888P'
#                                             d"     YD
#                                             "Y88888P'

# 版本间有变化的文件，每两个相邻版本一个文件夹，里面prev和post分别是前后版本的文件夹
# 另外保存一个json文件，里面是版本和文件的索引，方便做遍历
class changedCodes(Step):
	'fetch changed python source codes for sorted builds'

	REQUIRE = 'buildCommits', 'gitRepo'

	fileRe = re.compile(r'\s*(?P<tag>[AMD])\s+(?P<path>\S+)\s*', re.I)

	def load(self):
		cls = self.__class__
		self.index = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		index = utils.readData(self.index)
		data = {}
		for diff, files in index.iteritems():
			for t, f in files:
				path = 'data/%s/%s/%s/%%s/%s' % (self.flow.project, cls.__name__, diff, f)
				prev = os.path.abspath(path % 'prev')
				post = os.path.abspath(path % 'post')
				noPrev = not os.path.isfile(prev)
				noPost = not os.path.isfile(post)
				if True:
					pass
				elif noPrev and noPost:
					return False
				elif noPrev:
					if t != 'A': return False
				elif noPost:
					if t != 'D': return False
				elif t != 'M': return False
				data[(f, diff)] = (prev, post)
		self.data = data

		return True

	def generate(self):
		cls = self.__class__
		index = {}
		data = {}
		commitsSet = set()
		for build in self.flow.buildCommits.data:
			commitsSet.add(build['commit'])
		for i, build in enumerate(self.flow.buildCommits.data):
			post = build['commit']
			if 'parentID' not in build:
				if i == 0:
					prev = post
					continue
			else:
				prev = build['parentID']
				if prev not in commitsSet:
					# print prev,post,'note....',len(commitsSet)
					continue

			files = []
			cmd = 'git --git-dir=%s/.git diff --name-status %s %s' % (self.flow.gitRepo.path, prev, post)
			# print cmd
			# raw_input()
			with os.popen(cmd) as proc:
				line = proc.readline()
				while line:
					m = self.fileRe.match(line)
					if m:
						fileName = m.group('path')
						if fileName.endswith(self.flow.EXT):
							files.append((m.group('tag'), fileName))
					elif line.strip():
						print line.strip()
					line = proc.readline()

			if files:
				diff = '%s-%s' % (prev[:10], post[:10])
				index[diff] = files
				for t, f in files:
					path = '../%s/%s/%%s/%s' % (cls.__name__, diff, f)
					prevPath = os.path.abspath(path % 'prev')
					postPath = os.path.abspath(path % 'post')
					folder = path.rpartition('/')[0]
					False and t in ('D', 'M') and not os.path.isdir(folder % 'prev') and os.makedirs(folder % 'prev')
					False and t in ('A', 'M') and not os.path.isdir(folder % 'post') and os.makedirs(folder % 'post')
					False and t in ('D', 'M') and os.system('git --git-dir=%s/.git show %s:%s > %s' % (self.flow.gitRepo.path, prev, f, prevPath))
					False and t in ('A', 'M') and os.system('git --git-dir=%s/.git show %s:%s > %s' % (self.flow.gitRepo.path, post, f, postPath))
					data[(f, diff)] = (prevPath, postPath)

			if 'parentID' not in build:
				prev = post

		self.data = data
		self.index = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(self.index, index)

		return True


#  .o88o.  o8o  oooo                 oooooooooo.    o8o   .o88o.  .o88o.
#  888 `"  `"'  `888                 `888'   `Y8b   `"'   888 `"  888 `"
# o888oo  oooo   888   .ooooo.        888      888 oooo  o888oo  o888oo
#  888    `888   888  d88' `88b       888      888 `888   888     888
#  888     888   888  888ooo888       888      888  888   888     888
#  888     888   888  888    .o       888     d88'  888   888     888
# o888o   o888o o888o `Y8bod8P'      o888bood8P'   o888o o888o   o888o

# 从直接使用changedCodes中的index数据，在后续Step中可以省略changedCodes中的代码文件
class fileDiff(Step):
	'load changedCodes index'

	REQUIRE = 'buildCommits', 'changedCodes',

	def load(self):
		index = utils.readData(self.flow.changedCodes.index)
		versions = sorted(self.flow.buildCommits.commits,
			key = lambda c: self.flow.buildCommits.commits[c]['timestamp'])
		versionIdx = {c[:10]: i for i, c in enumerate(versions)}
		assert len(versionIdx) == len(self.flow.buildCommits.commits)
		for diff, files in index.iteritems():
			print diff,versionIdx[diff[:10]], versionIdx[diff[-10:]]
			# assert versionIdx[diff[:10]] < versionIdx[diff[-10:]]
		self.versions = sorted(set([k[:10] for k in index] + [k[-10:] for k in index]), key = lambda k: versionIdx[k])
		self.diffs = sorted(index, key = lambda k: versionIdx[k[:10]])
		self.index = index
		return True

	def generate(self):
		return self.load()


#             o8o      .        ooooo
#             `"'    .o8        `888'
#  .oooooooo oooo  .o888oo       888          .ooooo.   .oooooooo
# 888' `88b  `888    888         888         d88' `88b 888' `88b
# 888   888   888    888         888         888   888 888   888
# `88bod8P'   888    888 .       888       o 888   888 `88bod8P'
# `8oooooo.  o888o   "888"      o888ooooood8 `Y8bod8P' `8oooooo.
# d"     YD                                            d"     YD
# "Y88888P'                                            "Y88888P'

# 从git获取的版本间的diff日志，每两个相邻版本保存一个txt文件
class gitLog(Step):
	'fetch git log for sorted builds'

	REQUIRE = 'gitRepo', 'fileDiff'

	def load(self):
		cls = self.__class__
		data = {}
		for diff in self.flow.fileDiff.index:
			path = os.path.abspath('data/%s/%s/%s.txt' % (self.flow.project, cls.__name__, diff))
			if not os.path.isfile(path):
				return False
			data[diff] = path
		self.data = data
		return True

	def generate(self):
		cls = self.__class__
		root = os.path.abspath('data/%s/%s' % (self.flow.project, cls.__name__))
		not os.path.isdir(root) and os.makedirs(root)
		data = {}
		for diff in self.flow.fileDiff.index:
			path = '%s/%s.txt' % (root, diff)
			os.system('git --git-dir=%s/.git diff %s > %s' % (self.flow.gitRepo.path, diff.replace('-', ' '), path))
			data[diff] = path
		self.data = data
		return True


#             o8o      .        oooooooooo.    o8o   .o88o.  .o88o.
#             `"'    .o8        `888'   `Y8b   `"'   888 `"  888 `"
#  .oooooooo oooo  .o888oo       888      888 oooo  o888oo  o888oo
# 888' `88b  `888    888         888      888 `888   888     888
# 888   888   888    888         888      888  888   888     888
# `88bod8P'   888    888 .       888     d88'  888   888     888
# `8oooooo.  o888o   "888"      o888bood8P'   o888o o888o   o888o
# d"     YD
# "Y88888P'

# 根据git的版本间代码diff获取代码文本修改记录
class gitDiff(Step):
	'fetch text diff from git log'

	REQUIRE = 'fileDiff', 'gitLog', 'transition'

	fileRe = re.compile(r'^diff --git a/(?P<path>\S+)\s*.*', re.I)
	rangeRe = re.compile(r'^@@\s*\-(?P<oF>\d+),(?P<oR>\d+)\s*\+(?P<nF>\d+),(?P<nR>\d+)\s*@@.*', re.I)

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return True

	def _extractChanges(self, path):
		changes = {}
		with open(path, 'r') as diffFile:
			line = diffFile.readline()
			processedFlag = False
			currFile = None
			while line:
				m = self.fileRe.match(line) if not processedFlag else None
				if m:
					currFile = m.group('path')
					if currFile.endswith(self.flow.EXT):
						if currFile not in changes:
							changes[currFile] = {'prevLines': {}, 'postLines': {}}
							prevLines = {}
							postLines = {}
						processedFlag = True
					else:
						currFile = None

				m = self.rangeRe.match(line) if not processedFlag else None
				if m and currFile:
					oF = int(m.group("oF"))
					oR = int(m.group("oR"))
					nF = int(m.group("nF"))
					nR = int(m.group("nR"))
					processedFlag = True

					prevLineNum = 0
					postLineNum = 0
					line = diffFile.readline()
					while line:
						if line.startswith(' '):
							line = line[1:]
							prevLineNum += 1
							postLineNum += 1
						elif line.startswith('-'):
							line = line[1:]
							prevLines[oF + prevLineNum] = line
							prevLineNum += 1
						elif line.startswith('+'):
							line = line[1:]
							postLines[nF + postLineNum] = line
							postLineNum += 1

						if prevLineNum >= oR and postLineNum >= nR:
							break
						line = diffFile.readline()

					changes[currFile]['prevLines'] = prevLines
					changes[currFile]['postLines'] = postLines

				processedFlag = False
				line = diffFile.readline()

		return changes

	def _arrangeFunction(self, data, key, fileName, version, lines):
		if fileName not in self.flow.transition.data:
			print fileName, "not in transition"
			return

		defs = self.flow.transition.data[fileName]
		for lineNum, line in lines.iteritems():
			if not line.strip():
				continue

			func = None
			funcNum = -1
			for n, vs in defs.iteritems():
				num = vs[version]
				if funcNum < num <= lineNum:
					funcNum = num
					func = n

			if func is None:
				continue

			funcKey = utils.getStringKeys(fileName, func)
			if funcKey not in data:
				data[funcKey] = {key: {}}
			elif key not in data[funcKey]:
				data[funcKey][key] = {}
			data[funcKey][key][lineNum] = line

	def generate(self):
		data = {}
		for diff in self.flow.fileDiff.index:
			path = self.flow.gitLog.data[diff]
			changes = self._extractChanges(path)

			prev = diff[:10]
			post = diff[-10:]
			data[diff] = {}
			for f, cs in changes.iteritems():
				self._arrangeFunction(data[diff], 'prev', f, prev, cs['prevLines'])
				self._arrangeFunction(data[diff], 'post', f, post, cs['postLines'])

		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, data)
		self.data = data

		return True
