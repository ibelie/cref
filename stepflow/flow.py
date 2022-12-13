#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from step import MetaStep
import threading

class Flow(object):
	REPEAT_TEST = 5
	CPU_COUNT = 15
	MEM_LIMIT = '2G'

	def __init__(self, EXT, project):
		self.EXT = EXT
		self.project = project
		self.CPU_LIST = set(map(str, xrange(self.CPU_COUNT)))
		self.CPU_SEMA = threading.Semaphore(self.CPU_COUNT)

	def run(self, stepName):
		def initStep(stepName):
			stepCls = MetaStep.Steps[stepName]
			for require in stepCls.REQUIRE:
				initStep(require)
			not hasattr(self, stepName) and setattr(self, stepName, stepCls(self))
		initStep(stepName)
		

		steps = []
		def checkStep(stepName):
			step = getattr(self, stepName)
			if step and step.isReady:
				return

			stepCls = MetaStep.Steps[stepName]
			for require in stepCls.REQUIRE:
				checkStep(require)
			stepName not in steps and steps.append(stepName)
		checkStep(stepName)

		print '[Flow] Steps:', ', '.join(steps)

		for stepName in steps:
			step = getattr(self, stepName)
			print '[Flow] => Step:', step.__class__
			step.isReady = step.generate()
			if not step.isReady:
				break

	def dispose(self):
		del self.__dict__


def run(EXT, step, project):
	flow = Flow(EXT, project)
	flow.run(step)
	flow.dispose()
