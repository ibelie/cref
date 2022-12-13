#-*- coding: utf-8 -*-
# Copyright 2020 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from __future__ import print_function

import re
import sys
import codecs

PythonPathRe = re.compile(r'.*(?P<path>~/virtualenv/\S+)/bin/activate.*', re.S)

def inject(text, writer):
	code_0, head, code_1 = text.partition('function travis_run_setup() {')
	code_1, tail, code_2 = code_1.partition('\n:\n}\n')
	m = PythonPathRe.match(code_1)
	if m:
		python_path = m.group('path')
		writer.write(code_0)
		writer.write(head)
		writer.write(code_1)
		writer.write('''
travis_cmd python\ -m\ pip\ install\ ~/.properform/properform
travis_cmd sudo\ chmod\ 666\ $(find %(python_path)s/ ! -path "*/site-packages/*" -a -name encodings)/__init__.py
travis_cmd echo\ -e\ '%(start_properform)s'>>$(find %(python_path)s/ ! -path "*/site-packages/*" -a -name encodings)/__init__.py
		''' % {
		'python_path': python_path,
		'start_properform': '''
try:
	import _thread as thread
except:
	import thread

def start_properform():
	try:
		import properform
	except:
		thread.start_new_thread(start_properform, ())
start_properform()
'''.replace('\n', '\\\\n').replace('\t', '\\\\t').replace('(', '\\(').replace(')', '\\)')})
		writer.write(tail)
		writer.write(code_2)

if __name__ == '__main__':
	try:
		with codecs.open(sys.argv[1], 'r', 'utf-8') as f:
			text = f.read()
		writer = codecs.open(sys.argv[1], 'w', 'utf-8')
	except:
		text = sys.stdin.read()
		writer = sys.stdout
	inject(text, writer)
	if writer is not sys.stdout:
		writer.close()
