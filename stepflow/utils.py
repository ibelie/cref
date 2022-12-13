#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

import os
import sys
import zlib
import json
import struct
import urllib

if sys.version_info[0] == 3:
	from io import BytesIO
else:
	from cStringIO import StringIO as BytesIO

def getStringKeys(*args):
	return repr(tuple(map(lambda a: str(a) if not isinstance(a, basestring) else a.encode(errors='ignore'), args)))


def getFileSize(path):
	try:
		return os.path.getsize(path)
	except Exception as err:
		pass
		# print err


def saveData(path, data):
	folder = path.rpartition('/')[0]
	not os.path.isdir(folder) and os.makedirs(folder)
	with open(path, 'w') as f:
		json.dump(data, f, indent = 4, sort_keys = True)


def readData(path):
	with open(path, 'r') as f:
		return json.load(f)


def readURL(cache, url):
	cache = 'data/cache/%s' % cache
	if os.path.isfile(cache):
		with open(cache, 'r') as f:
			return f.read()

	try:
		content = urllib.urlopen(url).read()
	except:
		return None

	folder = cache.rpartition('/')[0]
	not os.path.isdir(folder) and os.makedirs(folder)
	with open(cache, 'w') as f:
		f.write(content)

	return content

def drawDF(ax, title, xlabel, ylabel, df, kind = None):

	ax.set_title(title)
	if kind is None:
		df.plot(ax = ax)
	elif kind == 'boxplot':
		df.boxplot(ax = ax)
	else:
		df.plot(kind = kind, ax = ax)
	ax.set_xlabel(xlabel)
	ax.set_ylabel(ylabel)

class Struct(object):
	def __init__(self, format):
		self.format = format

	def pack(self, writer, *args):
		writer.write(struct.pack(self.format, *args))

	def unpack(self, reader):
		return struct.unpack(self.format, reader.read(struct.calcsize(self.format)))

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
		self.compressor = zlib.compressobj(zlib.Z_BEST_COMPRESSION, zlib.DEFLATED, zlib.MAX_WBITS, zlib.Z_BEST_COMPRESSION)

	def write(self, data):
		self.writer.write(self.compressor.compress(data))

	def flush(self):
		self.writer.write(self.compressor.flush())
