# -*- coding: utf-8 -*-
# Copyright 2017 - 2019 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

__version__ = '0.2.0'
__author__ = 'joungtao'

import os

COVERAGE_PATH = os.getenv('PROPERFORM_COVERAGE_PATH')
MEMLEAK_PATH = os.getenv('PROPERFORM_MEMLEAK_PATH')
PROFILE_PATH = os.getenv('PROPERFORM_PROFILE_PATH')
OUTPUT_PATH = os.getenv('PROPERFORM_OUTPUT_PATH')

if COVERAGE_PATH or MEMLEAK_PATH or PROFILE_PATH or OUTPUT_PATH:
	import sys
	if MEMLEAK_PATH or OUTPUT_PATH:
		if sys.version_info[0] == 3:
			import properform.memory_leak as memleak
		else:
			import memory_leak as memleak
		memleak.start()

	if PROFILE_PATH or OUTPUT_PATH:
		if sys.version_info[0] == 3:
			import properform.profile as profile
		else:
			import profile as profile
		profile.start()

	if COVERAGE_PATH:
		coverage = {}
		def coverage_collector(frame, event, arg):
			global coverage
			code = getattr(frame, 'f_code', None)
			code and coverage.setdefault(code.co_filename, {}).setdefault(code.co_firstlineno, set()).add(code.co_name)

		import threading
		threading.settrace(coverage_collector)

	def write_coverage(path):
		import codecs
		global coverage
		with codecs.open(path, 'a') as f:
			for p in sorted(coverage):
				f.write('"%s",%d\n' % (p, len(coverage[p])))
				for l in sorted(coverage[p]):
					f.write('%s,%s\n' % (l, repr(sorted(coverage[p][l]))))

	def check_large_file(path, writer, *data):
		curr_path = path
		if os.path.isfile(path):
			curr_path = path + '_tmp'
		writer(curr_path, *data)
		if curr_path == path: return
		try:
			last_size = os.path.getsize(path)
		except:
			last_size = 0
		try:
			curr_size = os.path.getsize(curr_path)
		except:
			curr_size = 0
		if curr_size >= last_size:
			os.unlink(path)
			os.rename(curr_path, path)
		else:
			os.unlink(curr_path)

	def write_memleak(path, mleak):
		import codecs, json
		with codecs.open(path, 'w') as f:
			json.dump(mleak, f)

	def write_profile(path, stats):
		import marshal
		with open(path, 'wb') as f:
			marshal.dump(stats, f)

	def write_output(path, mleak, stats):
		if sys.version_info[0] == 3:
			import properform.properform as ppf
		else:
			import properform as ppf
		import struct
		with open(path, 'wb') as f:
			compressor = DataCompressor(f)
			ppf.AppendProfile(compressor, stats)
			ppf.AppendMemLeak(compressor, mleak)
			compressor.flush()

	import atexit
	@atexit.register
	def _output_files():
		if MEMLEAK_PATH or OUTPUT_PATH:
			mleak = memleak.collect()
			MEMLEAK_PATH and check_large_file(MEMLEAK_PATH, write_memleak, mleak)
		if PROFILE_PATH or OUTPUT_PATH:
			stats = profile.collect()
			PROFILE_PATH and check_large_file(PROFILE_PATH, write_profile, stats)
		OUTPUT_PATH and check_large_file(OUTPUT_PATH, write_output, mleak, stats)
		COVERAGE_PATH and write_coverage(COVERAGE_PATH)
