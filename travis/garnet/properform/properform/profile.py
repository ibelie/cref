#-*- coding: utf-8 -*-
# Copyright 2020 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from cProfile import Profile

profiler = None

def start():
	global profiler
	profiler = Profile()
	profiler.enable()

def collect(filename = None):
	global profiler
	if profiler:
		if filename:
			profiler.dump_stats(filename)
		else:
			profiler.create_stats()
			return profiler.stats
