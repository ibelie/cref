#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils
import hashlib

GROUP = 'Modeling'


#           oooo  oooo       oooooooooo.    o8o   .o88o.  .o88o.
#           `888  `888       `888'   `Y8b   `"'   888 `"  888 `"
#  .oooo.    888   888        888      888 oooo  o888oo  o888oo   .oooo.o
# `P  )88b   888   888        888      888 `888   888     888    d88(  "8
#  .oP"888   888   888        888      888  888   888     888    `"Y88b.
# d8(  888   888   888        888     d88'  888   888     888    o.  )88b
# `Y888""8o o888o o888o      o888bood8P'   o888o o888o   o888o   8""888P'

# 整理和汇总各种diff
class allDiffs(Step):
	'Combine all diffs'

	REQUIRE = 'fileDiff', 'gitDiff', 'astDiff', 'profileDiff'

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return False

	def generate(self):
		data = {}
		for diff in self.flow.fileDiff.index:
			astDiff = self.flow.astDiff.data[diff]
			profileDiff = self.flow.profileDiff.data[diff]
			if not set(astDiff) & set(profileDiff): continue

			data[diff] = {}
			for f_n in profileDiff:
				data[diff][f_n] = {}

		print data.keys(), len(data)

		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, data)
		self.data = data

		return False


# oooo                                            o8o
# `888                                            `"'
#  888   .ooooo.   .oooo.   oooo d8b ooo. .oo.   oooo  ooo. .oo.    .oooooooo
#  888  d88' `88b `P  )88b  `888""8P `888P"Y88b  `888  `888P"Y88b  888' `88b
#  888  888ooo888  .oP"888   888      888   888   888   888   888  888   888
#  888  888    .o d8(  888   888      888   888   888   888   888  `88bod8P'
# o888o `Y8bod8P' `Y888""8o d888b    o888o o888o o888o o888o o888o `8oooooo.
#                                                                  d"     YD
#                                                                  "Y88888P'

class learning(Step):
	'not implemented'

	REQUIRE = 'allDiffs',

	def load(self):
		return False

	def generate(self):
		return False


#          oooo                                          .o   .ooooo.     .oooo.       .ooo
#          `888                                        o888  d88'   `8.  d8P'`Y8b    .88'
#  .oooo.o  888 .oo.    .ooooo.  oooo oooo    ooo       888  Y88..  .8' 888    888  d88'
# d88(  "8  888P"Y88b  d88' `88b  `88. `88.  .8'        888   `88888b.  888    888 d888P"Ybo.
# `"Y88b.   888   888  888   888   `88..]88..8'         888  .8'  ``88b 888    888 Y88[   ]88
# o.  )88b  888   888  888   888    `888'`888'          888  `8.   .88P `88b  d88' `Y88   88P
# 8""888P' o888o o888o `Y8bod8P'     `8'  `8'          o888o  `boood8'   `Y8bd8P'   `88bod8'

# 输出展示数据
class show1806(Step):
	'Output show json data 2018-06'

	REQUIRE = 'buildCommits', 'fileDiff', 'astDiff', 'profileData', 'profileDiff'

	def load(self):
		return False

	def generate(self):
		PVALUE = self.flow.profileDiff.PVALUE
		cls = self.__class__
		statistics = []
		transition = {}
		commits = {c[:10]: v for c, v in self.flow.buildCommits.commits.iteritems()}
		for diff in self.flow.fileDiff.diffs:
			astDiff = self.flow.astDiff.data[diff]
			profileDiff = self.flow.profileDiff.data[diff]
			for n, d in astDiff.iteritems():
				transition.setdefault(hashlib.md5(n).hexdigest(), {}).setdefault(diff, {}).setdefault('astDiff', len(d))
			for n, d in profileDiff.iteritems():
				transition.setdefault(hashlib.md5(n).hexdigest(), {}).setdefault(diff, {}).setdefault('profileDiff', -d['totTime'][2])
			if max(len(astDiff), len(profileDiff)) > 500:
				continue

			statistics.append({
				'diff': diff,
				'timestamp': int(commits[diff[-10:]]['timestamp']) * 1000,
				'AST Diff': len(astDiff),
				'Profile Diff': len(profileDiff),
			})

			nodes = {}
			profileData = self.flow.profileData.data[diff]
			for n, p in profileData.iteritems():
				if (p['totTime'][1] < PVALUE and p['totTime'][2] != 0):
					nodes[n] = p['totTime'][2] < 0
				elif n in astDiff:
					nodes[n] = None

			graph = {
				'edges': [],
			}

			edgeNodes = set()
			for n, p in profileData.iteritems():
				for ce in p['callee']:
					if n in nodes and ce in nodes:
						edgeNodes.add(n)
						edgeNodes.add(ce)
						graph['edges'].append({
							'source': n,
							'target': ce,
							'weight': (len(astDiff.get(n, ())) + 1) * (1 if nodes[n] is None else 2) + (len(astDiff.get(ce, ())) + 1) * (1 if nodes[ce] is None else 2),
						})

			if len(edgeNodes) < 100:
				for edge in graph['edges']:
					if edge['weight'] > 4 or len(graph['edges']) < 10:
						edge['shape'] = 'flowingEdge'

			graph['nodes'] = [{
				'id': n,
				'md5': hashlib.md5(n).hexdigest(),
				'AST Diff': len(astDiff.get(n, ())),
				'Profile Diff': nodes[n],
				'weight': (len(astDiff.get(n, ())) + 1) * (1 if nodes[n] is None else 2),
			} for n in edgeNodes]

			path = 'data/%s/%s/diff/%s.json' % (cls.__name__, self.flow.project, diff)
			utils.saveData(path, graph)

		path = 'data/%s/%s/statistics.json' % (cls.__name__, self.flow.project)
		utils.saveData(path, statistics)

		for n, fs in transition.iteritems():
			funcdata = []
			for diff in self.flow.fileDiff.diffs:
				funcdata.append({
					'timestamp': int(commits[diff[-10:]]['timestamp']) * 1000,
					'astDiff': fs[diff].get('astDiff', 0) if diff in fs else 0,
					'profileDiff': fs[diff].get('profileDiff', 0) if diff in fs else 0,
				})
			path = 'data/%s/%s/func/%s.json' % (cls.__name__, self.flow.project, n)
			utils.saveData(path, funcdata)

		return False
