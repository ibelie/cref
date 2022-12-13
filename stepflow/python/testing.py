#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils

GROUP = 'Testing'

# transition trifusion/process/sequence.py
class transition_sequence(Step):
	'transition_sequence'

	REQUIRE = 'fileDiff', 'transition'

	def load(self):
		return False

	def generate(self):
		cls = self.__class__
		data = {}
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		for n, d in self.flow.transition.data['trifusion/process/sequence.py'].iteritems():
			if 'remove:' in n or '_write_gphocs' in n:
				data[n] = d
		with open(path, 'w') as f:
			f.write('{\n')
			for n, d in data.iteritems():
				f.write('"%s": {\n' % n)
				i = 0
				for v in self.flow.fileDiff.versions:
					l = d[v]
					if i % 4 == 0:
						f.write('\t')
					f.write('"%s": %d, ' % (v, l))
					if i % 4 == 3:
						f.write('\n')
					i += 1
				if i % 4 != 0:
					f.write('\n')
				f.write('\t},\n')
			f.write('}\n')
		return False


# rawASTDiff trifusion/process/sequence.py
class rawASTDiff_sequence(Step):
	'rawASTDiff_sequence'

	REQUIRE = 'rawASTDiff'

	def load(self):
		return False

	def generate(self):
		diff = '9a3cae4d00-c1678877c5'
		f = 'trifusion/process/sequence.py'
		data = {'diff': [], 'match': []}

		path = self.flow.rawASTDiff.data[(f, diff)][1]
		diffs = utils.readData(path)['astDiff']
		for d in diffs:
			if (d['type'] == 'FUNCTIONDEF' or \
				d['type'] == 'CLASSDEF') and '_write_gphocs' in d['node']:
				d.pop('action')
				data['diff'].append(d)

		path = self.flow.rawASTDiff.data[(f, diff)][0]
		matches = utils.readData(path)['astMatch']
		for m in matches:
			if (m['dst']['type'] == 'FUNCTIONDEF' or \
				m['src']['type'] == 'FUNCTIONDEF' or \
				m['dst']['type'] == 'CLASSDEF' or \
				m['src']['type'] == 'CLASSDEF') and \
				('_write_gphocs' in m['src']['node'] or \
				'_write_gphocs' in m['dst']['node']):
				data['match'].append(m)

		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, data)

		return False
