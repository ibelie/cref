#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow import utils
from stepflow.step import Step
from scipy.stats import ttest_ind
import pstats
import math
import copy

GROUP = 'Profile Analyzer'


#                                .o88o.  o8o  oooo                 oooooooooo.                 .
#                                888 `"  `"'  `888                 `888'   `Y8b              .o8
# oo.ooooo.  oooo d8b  .ooooo.  o888oo  oooo   888   .ooooo.        888      888  .oooo.   .o888oo  .oooo.
#  888' `88b `888""8P d88' `88b  888    `888   888  d88' `88b       888      888 `P  )88b    888   `P  )88b
#  888   888  888     888   888  888     888   888  888ooo888       888      888  .oP"888    888    .oP"888
#  888   888  888     888   888  888     888   888  888    .o       888     d88' d8(  888    888 . d8(  888
#  888bod8P' d888b    `Y8bod8P' o888o   o888o o888o `Y8bod8P'      o888bood8P'   `Y888""8o   "888" `Y888""8o
#  888
# o888o

class profileData(Step):
	'extract profile data'

	REQUIRE = 'buildHistory', 'fileDiff', 'transition'

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return True

	def _getFuncInfo(self, d, v, f, l, n):
		if n in ('<genexpr>', '<module>'):
			# AST中的GeneratorExp需要特殊处理，忽略掉了
			return None, None, None

		if not f.startswith('/home/travis/build/'):
			return f, n, None
		f = '/'.join(f.split('/')[6:])

		if f not in self.flow.transition.data:
			n = '%s:%d' % (n, l)
		else:
			defs = self.flow.transition.data[f]
			for name, vs in defs.iteritems():
				if v in vs and vs[v] == l:
					if n.strip('<>_') not in name and (n, name) not in self.renamed:
						self.renamed[(n, name)] = (v, f, l)
						print 'Rename:', repr((n, name, v, f, l)), len(self.renamed)
					n = name
					break
			else:
				f_n = utils.getStringKeys(f, n)
				if f_n not in self.notFound:
					self.notFound[f_n] = (v, f, l, n)
					print 'Profile diff cannot find funciton line number %s' % repr((v, f, l, n)), len(self.notFound)

		f_n = utils.getStringKeys(f, n)
		if f_n not in d:
			d[f_n] = {"totTime": [], "cumTime": [], "callee": {}}

		return f, n, d[f_n]

	def _extractProfile(self, version):
		data = {}
		path = "data/%s/profile/%s_%s_%%d.prof" % (self.flow.project, self.flow.project, version)
		for index in xrange(self.flow.REPEAT_TEST):
			if utils.getFileSize(path % index) < 10:
				continue
			stats = pstats.Stats(path % index).stats
			if len(stats) <= 0:
				continue

			for func, (totNum, cumNum, totTime, cumTime, callers) in stats.iteritems():
				f, n, funcInfo = self._getFuncInfo(data, version, *func)
				if f is None or n is None:
					continue

				for caller, (totNum, cumNum, totTime, cumTime) in callers.items():
					_, _, callerFunc = self._getFuncInfo(data, version, *caller)
					if callerFunc is None: continue
					f_n = utils.getStringKeys(f, n)
					if f_n not in callerFunc['callee']:
						callerFunc['callee'][f_n] = {"totTime": [], "cumTime": []}
					callerFunc['callee'][f_n]['totTime'].append(float(totTime) / totNum)
					callerFunc['callee'][f_n]['cumTime'].append(float(cumTime) / cumNum)

				if funcInfo is not None:
					funcInfo['totTime'].append(float(totTime) / totNum)
					funcInfo['cumTime'].append(float(cumTime) / cumNum)

		return data

	def _getTimeDiff(self, prev, post):
		t, p = ttest_ind(prev, post)
		if math.isinf(t):
			t = "i"
		elif math.isnan(t):
			t = "n"
		if math.isnan(p):
			p = "n"

		average_prev = float(sum(prev)) / len(prev)
		average_post = float(sum(post)) / len(post)

		if average_post + average_prev == 0:
			return t, p, 0
		return t, p, (average_post - average_prev) / (average_post + average_prev)

	def _profileDiff(self, prev, post):
		data = {}

		#前后版本都有的函数
		for f_n in set(prev) & set(post):
			pr = prev[f_n]
			po = post[f_n]
			calleeDiff = {}

			#都调用的
			for c_f_n in set(pr['callee']) & set(po['callee']):
				c_pr = pr['callee'][c_f_n]
				c_po = po['callee'][c_f_n]
				totTime = self._getTimeDiff(c_pr['totTime'], c_po['totTime'])
				cumTime = self._getTimeDiff(c_pr['cumTime'], c_po['cumTime'])
				calleeDiff[c_f_n] = {
					"totTime": totTime,
					"cumTime": cumTime,
					"mark": "update",
				}

			#删除的调用
			for c_f_n in set(pr['callee']) - set(po['callee']):
				calleeDiff[c_f_n] = {"totTime": (0, 0, -1), "cumTime": (0, 0, -1), "mark": "remove"}

			#新增的调用
			for c_f_n in set(po['callee']) - set(pr['callee']):
				calleeDiff[c_f_n] = {"totTime": (0, 0, 1), "cumTime": (0, 0, 1), "mark": "add"}

			totTime = self._getTimeDiff(pr['totTime'], po['totTime'])
			cumTime = self._getTimeDiff(pr['cumTime'], po['cumTime'])
			data[f_n] = {
				"totTime": totTime,
				"cumTime": cumTime,
				"callee": calleeDiff,
				"mark": "update",
			}

		#删除的函数
		for f_n in set(prev) - set(post):
			calleeDiff = {c: {"totTime": (0, 0, -1), "cumTime": (0, 0, -1), "mark": "remove"} for c in prev[f_n]['callee']}
			data[f_n] = {"totTime": (0, 0, -1), "cumTime": (0, 0, -1), "callee": calleeDiff, "mark": "remove"}

		#新增的函数
		for f_n in set(post) - set(prev):
			calleeDiff = {c: {"totTime": (0, 0, 1), "cumTime": (0, 0, 1), "mark": "add"} for c in post[f_n]['callee']}
			data[f_n] = {"totTime": (0, 0, 1), "cumTime": (0, 0, 1), "callee": calleeDiff, "mark": "add"}

		return data

	def generate(self):
		data = {}
		profiles = {}
		self.renamed = {}
		self.notFound = {}
		for diff in self.flow.fileDiff.index:
			prev = diff[:10]
			post = diff[-10:]
			if prev not in profiles:
				profiles[prev] = self._extractProfile(prev)
			if post not in profiles:
				profiles[post] = self._extractProfile(post)
			data[diff] = self._profileDiff(profiles[prev], profiles[post])

		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, data)
		self.data = data
		del self.renamed
		del self.notFound

		return True


# ooooooooooooo                                             oooooooooo.    o8o   .o88o.  .o88o.
# 8'   888   `8                                             `888'   `Y8b   `"'   888 `"  888 `"
#      888      oooo d8b  .oooo.    .ooooo.   .ooooo.        888      888 oooo  o888oo  o888oo
#      888      `888""8P `P  )88b  d88' `"Y8 d88' `88b       888      888 `888   888     888
#      888       888      .oP"888  888       888ooo888       888      888  888   888     888
#      888       888     d8(  888  888   .o8 888    .o       888     d88'  888   888     888
#     o888o     d888b    `Y888""8o `Y8bod8P' `Y8bod8P'      o888bood8P'   o888o o888o   o888o

class profileTraceDiff(Step):
	'trace back AST diff of profile data'

	REQUIRE = 'profileData', 'fileDiff', 'astDiff'

	PVALUE = 0.05

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return True

	def generate(self):
		def _trace(t, n, d, s):
			tb = {}
			for k in d[n][t]:
				if k in s:
					continue
				s.add(k)
				tb[k] = _trace(t, k, d, s) if k in d else {}
			return tb

		def _hasASTDiff(t, d):
			for k in d:
				if k in t:
					return True
			for v in d.itervalues():
				if _hasASTDiff(t, v):
					return True
			return False

		data = {}
		for diff, kvs in self.flow.profileData.data.iteritems():
			inverse = {}
			traceAST = {}
			for k, vs in kvs.iteritems():
				inverse.setdefault(k, {'caller': set()})
				for v in vs['callee']:
					inv = inverse.setdefault(v, {'caller': set()})
					inv['caller'].add(k)

				for df in self.flow.fileDiff.diffs:
					if k in self.flow.astDiff.data[df]:
						traceAST[k] = df
					if df == diff:
						break

			d = {}
			for k in kvs:
				caller = _trace('caller', k, inverse, set())
				callee = _trace('callee', k, kvs, set())
				d[k] = [0, 0, traceAST.get(k),
					_hasASTDiff(traceAST, caller), _hasASTDiff(traceAST, callee)]
			data[diff] = d

		self.data = data
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, self.data)

		return True


#                                .o88o.  o8o  oooo                 oooooooooo.    o8o   .o88o.  .o88o.
#                                888 `"  `"'  `888                 `888'   `Y8b   `"'   888 `"  888 `"
# oo.ooooo.  oooo d8b  .ooooo.  o888oo  oooo   888   .ooooo.        888      888 oooo  o888oo  o888oo
#  888' `88b `888""8P d88' `88b  888    `888   888  d88' `88b       888      888 `888   888     888
#  888   888  888     888   888  888     888   888  888ooo888       888      888  888   888     888
#  888   888  888     888   888  888     888   888  888    .o       888     d88'  888   888     888
#  888bod8P' d888b    `Y8bod8P' o888o   o888o o888o `Y8bod8P'      o888bood8P'   o888o o888o   o888o
#  888
# o888o

class profileDiff(Step):
	'get profile diff'

	REQUIRE = 'profileData',

	PVALUE = 0.05

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return True

	def generate(self):
		def _totTime(data):
			changed = {k: copy.deepcopy(v) for k, v in data.iteritems() if v['totTime'][1] < self.PVALUE and v['mark'] == 'update'}
			for d in changed.itervalues():
				if d.get('callee'): d['callee'] = _totTime(d['callee'])
			return changed

		self.data = {k: _totTime(v) for k, v in self.flow.profileData.data.iteritems()}
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, self.data)

		return True
