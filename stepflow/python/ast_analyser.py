#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils
import os

GROUP = 'AST Analyzer'


#                                                .o.        .oooooo..o ooooooooooooo      oooooooooo.    o8o   .o88o.  .o88o.
#                                               .888.      d8P'    `Y8 8'   888   `8      `888'   `Y8b   `"'   888 `"  888 `"
# oooo d8b  .oooo.   oooo oooo    ooo          .8"888.     Y88bo.           888            888      888 oooo  o888oo  o888oo
# `888""8P `P  )88b   `88. `88.  .8'          .8' `888.     `"Y8888o.       888            888      888 `888   888     888
#  888      .oP"888    `88..]88..8'          .88ooo8888.        `"Y88b      888            888      888  888   888     888
#  888     d8(  888     `888'`888'          .8'     `888.  oo     .d8P      888            888     d88'  888   888     888
# d888b    `Y888""8o     `8'  `8'          o88o     o8888o 8""88888P'      o888o          o888bood8P'   o888o o888o   o888o

# 运行java分析工具，获取AST的match和diff数据
class rawASTDiff(Step):
	'Get AST diff by java tool'

	REQUIRE = 'changedCodes', 'fileDiff',

	def load(self):
		cls = self.__class__
		data = {}
		for diff, files in self.flow.fileDiff.index.iteritems():
			for _, f in files:
				path = os.path.abspath('data/%s/%s/%s/%%s/%s' % (self.flow.project, cls.__name__, diff, f.replace(self.flow.EXT, '.json')))
				if not os.path.isfile(path % 'match'):
					print path % 'match'
					return False
				if not os.path.isfile(path % 'diff'):
					print path % 'diff'
					return False
				data[(f, diff)] = (path % 'match', path % 'diff')

		self.data = data
		return True

	def generate(self):
		cls = self.__class__
		data = {}
		for diff, files in self.flow.fileDiff.index.iteritems():
			for _, f in files:
				inputPath = self.flow.changedCodes.data[(f, diff)]
				outputPath = 'data/%s/%s/%s/%%s/%s' % (self.flow.project, cls.__name__, diff, f.replace(self.flow.EXT, '.json'))
				data[(f, diff)] = [os.path.abspath(outputPath % 'match'), os.path.abspath(outputPath % 'diff')]

				if os.path.isfile(outputPath % 'match') and os.path.isfile(outputPath % 'diff'):
					continue

				outputDir = outputPath.rpartition('/')[0]
				not os.path.isdir(outputDir % 'match') and os.makedirs(outputDir % 'match')
				not os.path.isdir(outputDir % 'diff') and os.makedirs(outputDir % 'diff')

				os.system("java -jar java/Diff.jar %s %s %s %s %s" % (inputPath[0], inputPath[1], outputPath % 'diff', outputPath % 'match', ".py"))
				#os.system("java -jar java/pyDiff.jar %s %s %s %s" % (inputPath[0], inputPath[1], outputPath % 'diff', outputPath % 'match'))

		self.data = data
		return True


#     .                                            o8o      .    o8o
#   .o8                                            `"'    .o8    `"'
# .o888oo oooo d8b  .oooo.   ooo. .oo.    .oooo.o oooo  .o888oo oooo   .ooooo.  ooo. .oo.
#   888   `888""8P `P  )88b  `888P"Y88b  d88(  "8 `888    888   `888  d88' `88b `888P"Y88b
#   888    888      .oP"888   888   888  `"Y88b.   888    888    888  888   888  888   888
#   888 .  888     d8(  888   888   888  o.  )88b  888    888 .  888  888   888  888   888
#   "888" d888b    `Y888""8o o888o o888o 8""888P' o888o   "888" o888o `Y8bod8P' o888o o888o

# 根据AST的match数据得到代码的演变记录，生成AST节点的一致性ID
class transition(Step):
	'Generate transition of AST nodes with unique ID'

	REQUIRE = 'fileDiff', 'rawASTDiff'

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return True

	# 根据prev:lineNum => post:lineNum尝试找到对应的def项并记录
	def _extendDef(self, defs, versions, node, prev, post, srcLineNum, dstLineNum):
		for n, d in defs.iteritems():
			if srcLineNum < 0:
				# 这种是INS的情况，原行号是-1，这里遍历的时候全部continue，最终走到最后的else分支
				continue
			elif prev in d and d[prev] == srcLineNum:
				assert post not in d or d[post] == dstLineNum
				# 当前def中记录的prev版本的lineNum刚好和srcLineNum相同，match成功
				# 记录post版本的lineNum
				d[post] = dstLineNum
				break
			elif len(versions) > 0:
				# 中间有一些版本没有修改任何代码，这会导致defs里面缺少某些版本的记录
				# 这时候直接用prev去查肯定是查不到的，但是可以用versions的最后一个版本去查
				# versions是按时间顺序记录的已经处理过的版本
				last = versions[-1]
				if last in d and d[last] == srcLineNum:
					assert post not in d or d[post] == dstLineNum
					# 当前def中记录的last版本的lineNum刚好和srcLineNum相同，match成功
					# 记录prev和post版本的lineNum
					d[prev] = srcLineNum
					d[post] = dstLineNum
					break
		else:
			# 包含INS和match不到的情况，记录prev和post版本的lineNum
			defs[node] = {prev: srcLineNum, post: dstLineNum}
			# 同时把前面的版本统统用srcLineNum补全
			for v in versions:
				defs[node][v] = srcLineNum

	def generate(self):
		data = {}
		versions = []
		for diff in self.flow.fileDiff.diffs:
			prev = diff[:10]
			post = diff[-10:]
			for _, f in self.flow.fileDiff.index[diff]:
				if f not in data:
					data[f] = {}
				defs = data[f]

				# 首先用diff中的记录更新defs信息
				path = self.flow.rawASTDiff.data[(f, diff)][1]
				diffs = utils.readData(path)['astDiff']
				for d in diffs:
					if d['type'] == 'FUNCTIONDEF' or \
						d['type'] == 'CLASSDEF':
						self._extendDef(defs, versions, d['node'], prev, post, d['src_lineNum'], d['dst_lineNum'])

				# 然后用match中的记录更新defs信息
				path = self.flow.rawASTDiff.data[(f, diff)][0]
				matches = utils.readData(path)['astMatch']
				for m in matches:
					if m['dst']['type'] == 'FUNCTIONDEF' or \
						m['src']['type'] == 'FUNCTIONDEF' or \
						m['dst']['type'] == 'CLASSDEF' or \
						m['src']['type'] == 'CLASSDEF':
						self._extendDef(defs, versions, m['src']['node'], prev, post, m['src']['lineNum'], m['dst']['lineNum'])

			# 有些文件并没有修改，这里统一遍历一遍defs
			# 按照上一个版本的行号补全，让每个处理过的版本都有对应的行号
			for defs in data.itervalues():
				for n, d in defs.iteritems():
					if post in d:
						continue
					elif prev in d:
						d[post] = d[prev]
					else:
						d[post] = d[prev] = d[versions[-1]]

			# 将处理过的版本号记录到versions里面
			# 因为有些版本间没有修改任何代码文件，所以prev不一定在versions中，需要检查一下加进去
			(not versions or versions[-1] != prev) and versions.append(prev)
			versions.append(post)

		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, data)
		self.data = data

		return True


#                        .        oooooooooo.    o8o   .o88o.  .o88o.
#                      .o8        `888'   `Y8b   `"'   888 `"  888 `"
#  .oooo.    .oooo.o .o888oo       888      888 oooo  o888oo  o888oo
# `P  )88b  d88(  "8   888         888      888 `888   888     888
#  .oP"888  `"Y88b.    888         888      888  888   888     888
# d8(  888  o.  )88b   888 .       888     d88'  888   888     888
# `Y888""8o 8""888P'   "888"      o888bood8P'   o888o o888o   o888o

# 根据AST节点的一致性ID对AST的diff数据进行整理
class astDiff(Step):
	'Convert AST diff data to python'

	REQUIRE = 'fileDiff', 'rawASTDiff', 'transition'

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		self.data = utils.readData(path)
		return True

	def generate(self):
		data = {}
		for diff, files in self.flow.fileDiff.index.iteritems():
			prev = diff[:10]
			post = diff[-10:]
			data[diff] = {}
			for _, f in files:
				defs = self.flow.transition.data[f]

				path = self.flow.rawASTDiff.data[(f, diff)][1]
				diffs = utils.readData(path)['astDiff']
				for d in diffs:
					funcParent = None
					classParent = None
					moduleParent = None

					for p in d['parents']:
						if p['type'] == 'FUNCTIONDEF' and (funcParent is None or p['lineNum'] > funcParent['lineNum']):
							funcParent = p
						elif p['type'] == 'CLASSDEF' and (classParent is None or p['lineNum'] > classParent['lineNum']):
							classParent = p
						elif p['type'] == 'MODULE' and (moduleParent is None or p['lineNum'] > moduleParent['lineNum']):
							moduleParent = p
					if 'label' not in d:
						d['label'] = ''
					actionInfo = {
						'action': d['actionName'],
						'node': d['node'],
						'label': d['label'],
						'lineNum': d['lineNum'],
						'type': d['type'],
						'funcParent': funcParent,
						'classParent': classParent,
						'moduleParent': moduleParent,
					}

					# INS的node和parents全都是post版本的
					version = post if d['actionName'] == 'INS' else prev
					lineNum = None
					if d['type'] == "FUNCTIONDEF":
						lineNum = d['lineNum']
					elif funcParent is not None:
						lineNum = funcParent['lineNum']
					# lineNum取本身或者所属的function定义的行号
					if lineNum is None: continue

					# 根据版本号和行号查到对应的def，记录action信息
					for n, vs in defs.iteritems():
						if version in vs and vs[version] == lineNum:
							f_n = utils.getStringKeys(f, n)
							if f_n not in data[diff]:
								data[diff][f_n] = []
							data[diff][f_n].append(actionInfo)
							break
					else:
						print 'AST diff cannot find funciton line number %s' % repr((version, prev, post, f, lineNum, actionInfo))

		cls = self.__class__
		path = 'data/%s/%s.json' % (self.flow.project, cls.__name__)
		utils.saveData(path, data)
		self.data = data

		return True
