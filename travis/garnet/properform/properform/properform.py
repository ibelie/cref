# -*- coding: utf-8 -*-
# Copyright 2017 - 2019 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from __future__ import print_function

import os
import sys
import zlib
import json
import codecs
import struct
import marshal

if sys.version_info[0] == 3:
	from urllib.parse import quote
	from urllib.request import Request, urlopen
	from io import BytesIO
else:
	from urllib import quote
	from urllib2 import Request, urlopen
	from cStringIO import StringIO as BytesIO


PROFILE_NAMESET_LEN = '!I'
PROFILE_NAMESET_ITEM = '!H'
PROFILE_CALLEE_LEN = '!I'
PROFILE_CALLEE_ITEM = '!IIIIIddI'
PROFILE_CALLER_ITEM = '!IIIIIdd'

def serialize_profile(writer, stats):
	nameset = set()
	for (f, l, n), (pc, rc, it, ct, callers) in stats.items():
		nameset.add(f)
		nameset.add(n)
		for (f, l, n), (pc, rc, it, ct) in callers.items():
			nameset.add(f)
			nameset.add(n)

	writer.write(struct.pack(PROFILE_NAMESET_LEN, len(nameset)))
	names = {}
	for name in nameset:
		s = name if isinstance(name, type(b'')) else name.encode('utf-8', 'replace')
		writer.write(struct.pack(PROFILE_NAMESET_ITEM, len(s)))
		writer.write(s)
		names[name] = len(names)

	writer.write(struct.pack(PROFILE_CALLEE_LEN, len(stats)))
	for (f, l, n), (pc, rc, it, ct, callers) in stats.items():
		writer.write(struct.pack(PROFILE_CALLEE_ITEM, names[f], l, names[n], pc, rc, it, ct, len(callers)))
		for (f, l, n), (pc, rc, it, ct) in callers.items():
			writer.write(struct.pack(PROFILE_CALLER_ITEM, names[f], l, names[n], pc, rc, it, ct))

def deserialize_profile(reader):
	names = []
	name_count, = struct.unpack(PROFILE_NAMESET_LEN, reader.read(struct.calcsize(PROFILE_NAMESET_LEN)))
	for _ in range(name_count):
		size, = struct.unpack(PROFILE_NAMESET_ITEM, reader.read(struct.calcsize(PROFILE_NAMESET_ITEM)))
		name = reader.read(size)
		name = name if isinstance(name, str) else name.decode('utf-8')
		names.append(name)

	stats = {}
	stat_count, = struct.unpack(PROFILE_CALLEE_LEN, reader.read(struct.calcsize(PROFILE_CALLEE_LEN)))
	for _ in range(stat_count):
		f, l, n, pc, rc, it, ct, caller_count = struct.unpack(PROFILE_CALLEE_ITEM, reader.read(struct.calcsize(PROFILE_CALLEE_ITEM)))
		callers = {}
		stats[(names[f], l, names[n])] = (pc, rc, it, ct, callers)
		for _ in range(caller_count):
			f, l, n, pc, rc, it, ct = struct.unpack(PROFILE_CALLER_ITEM, reader.read(struct.calcsize(PROFILE_CALLER_ITEM)))
			callers[(names[f], l, names[n])] = (pc, rc, it, ct)

	return stats


MEMLEAK_STRINGSET_LEN = '!I'
MEMLEAK_STRINGSET_ITEM = '!H'
MEMLEAK_OBJECT_LEN = '!I'
MEMLEAK_OBJECT_ITEM = '!QIIIIII'
MEMLEAK_TRACEBACK_ITEM = '!II'
MEMLEAK_REFERENCE_ITEM = '!Q'

def serialize_memleak(writer, memleak):
	stringset = set()
	for t, v, f, l, ts, rs in memleak.values():
		stringset.add(t)
		stringset.add(v)
		stringset.add(f)
		for f, n in ts:
			stringset.add(f)

	writer.write(struct.pack(MEMLEAK_STRINGSET_LEN, len(stringset)))
	strings = {}
	for ss in stringset:
		s = ss if isinstance(ss, type(b'')) else ss.encode('utf-8', 'replace')
		writer.write(struct.pack(MEMLEAK_STRINGSET_ITEM, len(s)))
		writer.write(s)
		strings[ss] = len(strings)

	writer.write(struct.pack(MEMLEAK_OBJECT_LEN, len(memleak)))
	for i, (t, v, f, l, ts, rs) in memleak.items():
		writer.write(struct.pack(MEMLEAK_OBJECT_ITEM, int(i), strings[t], strings[v], strings[f], l, len(ts), len(rs)))
		for f, n in ts:
			writer.write(struct.pack(MEMLEAK_TRACEBACK_ITEM, strings[f], n))
		for r in rs:
			writer.write(struct.pack(MEMLEAK_REFERENCE_ITEM, r))

def deserialize_memleak(reader):
	strings = []
	string_count, = struct.unpack(MEMLEAK_STRINGSET_LEN, reader.read(struct.calcsize(MEMLEAK_STRINGSET_LEN)))
	for _ in range(string_count):
		size, = struct.unpack(MEMLEAK_STRINGSET_ITEM, reader.read(struct.calcsize(MEMLEAK_STRINGSET_ITEM)))
		s = reader.read(size)
		s = s if isinstance(s, str) else s.decode('utf-8')
		strings.append(s)

	memleak = {}
	memleak_count, = struct.unpack(MEMLEAK_OBJECT_LEN, reader.read(struct.calcsize(MEMLEAK_OBJECT_LEN)))
	for _ in range(memleak_count):
		i, t, v, f, l, ts_count, rs_count = struct.unpack(MEMLEAK_OBJECT_ITEM, reader.read(struct.calcsize(MEMLEAK_OBJECT_ITEM)))
		ts = []
		rs = []
		memleak[i] = (strings[t], strings[v], strings[f], l, ts, rs)
		for _ in range(ts_count):
			f, n = struct.unpack(MEMLEAK_TRACEBACK_ITEM, reader.read(struct.calcsize(MEMLEAK_TRACEBACK_ITEM)))
			ts.append((strings[f], n))
		for _ in range(rs_count):
			r, = struct.unpack(MEMLEAK_REFERENCE_ITEM, reader.read(struct.calcsize(MEMLEAK_REFERENCE_ITEM)))
			rs.append(r)

	return memleak


DATA_TYPE_PROFILE = 1
DATA_TYPE_MEMLEAK = 2
DATA_TYPE_HEADER = '!H'

class DataFormatException(BaseException):
	pass

class DataDecompressor(object):
	BLOCK_SIZE = 1024

	def __init__(self, reader):
		self.bytes = BytesIO()
		self.reader = reader
		self.decompressor = zlib.decompressobj()

	def read(self, count):
		while len(self.bytes.getvalue()) - self.bytes.tell() < count:
			data = self.reader.read(self.BLOCK_SIZE)
			curr_pos = self.bytes.tell()
			self.bytes.seek(len(self.bytes.getvalue()))
			if data:
				self.bytes.write(self.decompressor.decompress(data))
			if len(data) < self.BLOCK_SIZE:
				self.bytes.write(self.decompressor.flush())
			self.bytes.seek(curr_pos)
			if not data: break

		data = self.bytes.read(count)

		size = len(self.bytes.getvalue())
		if size > 0 and float(size - self.bytes.tell()) / size < 0.2:
			bytes = BytesIO()
			bytes.write(self.bytes.read())
			bytes.seek(0)
			self.bytes = bytes

		return data

class DataCompressor(object):
	def __init__(self, writer):
		self.writer = writer
		self.compressor = zlib.compressobj(level = zlib.Z_BEST_COMPRESSION, memLevel = zlib.Z_BEST_COMPRESSION)

	def write(self, data):
		self.writer.write(self.compressor.compress(data))

	def flush(self):
		self.writer.write(self.compressor.flush())

def Iterate(reader):
	data = DataDecompressor(reader)
	header = data.read(struct.calcsize(DATA_TYPE_HEADER))
	while header:
		t, = struct.unpack(DATA_TYPE_HEADER, header)
		if t == DATA_TYPE_PROFILE:
			yield t, deserialize_profile(data)
		elif t == DATA_TYPE_MEMLEAK:
			yield t, deserialize_memleak(data)
		else:
			raise DataFormatException()
		header = data.read(struct.calcsize(DATA_TYPE_HEADER))

def AppendProfile(writer, data):
	writer.write(struct.pack(DATA_TYPE_HEADER, DATA_TYPE_PROFILE))
	serialize_profile(writer, data)

def AppendMemLeak(writer, data):
	writer.write(struct.pack(DATA_TYPE_HEADER, DATA_TYPE_MEMLEAK))
	serialize_memleak(writer, data)

def Push(url, token, project, commit, profile = '', memleak = '', tag = 'default'):
	assert profile or memleak
	data = BytesIO()
	compressor = DataCompressor(data)
	if os.path.isfile(profile):
		with open(profile, 'rb') as f:
			AppendProfile(compressor, marshal.load(f))
	if os.path.isfile(memleak):
		with open(memleak, 'rb') as f:
			AppendMemLeak(compressor, json.load(f))
	compressor.flush()

	if not url.startswith('http'):
		url = 'http://' + url
	request = Request('%(url)s?token=%(token)s&project=%(project)s&commit=%(commit)s&tag=%(tag)s' % {
		'url': url,
		'token': token,
		'project': project,
		'commit': commit,
		'tag': quote(tag),
	}, data.getvalue())
	response = json.load(urlopen(request))
	if not response['error']:
		print('[Properform] Push Success!')
	else:
		print('[Properform] Push Error: %(error)s!' % response)

def Convert(dst, src):
	with open(src, 'rb') as s:
		for t, data in Iterate(s):
			if t == DATA_TYPE_PROFILE:
				with open(dst, 'wb') as d:
					marshal.dump(data, d)
				break
			elif t == DATA_TYPE_MEMLEAK:
				with codecs.open(dst, 'w') as d:
					json.dump(data, d)
				break
