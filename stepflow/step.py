#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

import sys

class MetaStep(type):
	Steps = {}

	def __new__(mcs, clsname, bases, attrs):
		if clsname in mcs.Steps:
			raise NameError, 'Step name "%s" conflict with %s.' % (clsname, str(mcs.Steps[clsname]))

		cls = super(MetaStep, mcs).__new__(mcs, clsname, bases, attrs)
		module = sys.modules.get(cls.__module__)
		if hasattr(module, 'GROUP'):
			cls.GROUP = module.GROUP
			mcs.Steps[clsname] = cls

		return cls

	def __str__(cls):
		return '%s["%s", (%s)]' % (cls.__name__, cls.__doc__, ', '.join(cls.REQUIRE))


class Step(object):
	'base step'

	__metaclass__ = MetaStep
	REQUIRE = ()

	def __init__(self, flow):
		self.flow = flow
		try:
			self.isReady = self.load()
		except:
			self.isReady = False
			# raise

	def load(self):
		raise NotImplementedError, '%s should implemente method "load".' % str(self.__class__)

	def generate(self):
		raise NotImplementedError, '%s should implemente method "generate".' % str(self.__class__)

	def __del__(self):
		del self.flow
