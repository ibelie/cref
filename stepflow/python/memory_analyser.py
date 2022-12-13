#-*- coding: utf-8 -*-
# Copyright 2019-2020 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow import utils
from stepflow.step import Step
import subprocess
import codecs
import zlib
import sys
import os
import re

GROUP = 'Memory Analyzer'


# ooo        ooooo oooooooooooo ooo        ooooo      ooooo        oooooooooooo       .o.       oooo    oooo      oooooooooo.         .o.       ooooooooooooo       .o.
# `88.       .888' `888'     `8 `88.       .888'      `888'        `888'     `8      .888.      `888   .8P'       `888'   `Y8b       .888.      8'   888   `8      .888.
#  888b     d'888   888          888b     d'888        888          888             .8"888.      888  d8'          888      888     .8"888.          888          .8"888.
#  8 Y88. .P  888   888oooo8     8 Y88. .P  888        888          888oooo8       .8' `888.     88888[            888      888    .8' `888.         888         .8' `888.
#  8  `888'   888   888    "     8  `888'   888        888          888    "      .88ooo8888.    888`88b.          888      888   .88ooo8888.        888        .88ooo8888.
#  8    Y     888   888       o  8    Y     888        888       o  888       o  .8'     `888.   888  `88b.        888     d88'  .8'     `888.       888       .8'     `888.
# o8o        o888o o888ooooood8 o8o        o888o      o888ooooood8 o888ooooood8 o88o     o8888o o888o  o888o      o888bood8P'   o88o     o8888o     o888o     o88o     o8888o

class MemLeakVertex(object):
	__slots__ = 'index', 'edges', 'visited', 'prev', 'next', 'parent'

class MemLeakData(Step):
	'extract circular reference from memory leak data'

	REQUIRE = 'MemLeakProjects', 'projectInfo'

	MIN_SIZE = 400000

	DATA_STRINGSET_COUNT = utils.Struct('!I')
	DATA_STRINGSET_ITEM = utils.Struct('!H')
	DATA_PROJECTS_COUNT = utils.Struct('!I')
	DATA_PROJECTS_ITEM = utils.Struct('!II')
	DATA_TYPES_COUNT = utils.Struct('!I')
	DATA_TYPES_HEAD = utils.Struct('!I')
	DATA_TYPES_ITEM = utils.Struct('!I')
	DATA_OBJECTS_COUNT = utils.Struct('!I')
	DATA_OBJECTS_ITEM = utils.Struct('!IQI')
	DATA_CIRCLES_COUNT = utils.Struct('!I')
	DATA_CIRCLES_HEAD = utils.Struct('!I')
	DATA_CIRCLES_ITEM = utils.Struct('!I')

	separaterRe = re.compile(r'[^0-9a-zA-Z_]+', re.I)

	@classmethod
	def prepare(cls):
		path = 'data/%s/%s.raw' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		if not os.path.isfile(path):
			with open(path[:-4] + '.data', 'rb') as f:
				with open(path, 'wb') as t:
					t.write(zlib.decompress(f.read()))
		return path

	def load(self):
		path = self.prepare()
		with open(path, 'rb') as f:
			data = f # utils.DataDecompressor(f)
			strings = []
			string_count, = self.DATA_STRINGSET_COUNT.unpack(data)
			for _ in range(string_count):
				size, = self.DATA_STRINGSET_ITEM.unpack(data)
				s = data.read(size)
				s = s if isinstance(s, str) else s.decode('utf-8')
				strings.append(s)
			types = []
			types_count, = self.DATA_TYPES_COUNT.unpack(data)
			for _ in range(types_count):
				types_len, = self.DATA_TYPES_HEAD.unpack(data)
				object_type = tuple(strings[self.DATA_TYPES_ITEM.unpack(data)[0]] for _ in range(types_len))
				types.append(object_type)
			objects = []
			objects_count, = self.DATA_OBJECTS_COUNT.unpack(data)
			for _ in range(objects_count):
				objects.append(self.DATA_OBJECTS_ITEM.unpack(data))
			circles = []
			circles_count, = self.DATA_CIRCLES_COUNT.unpack(data)
			for _ in range(circles_count):
				circles_len, = self.DATA_CIRCLES_HEAD.unpack(data)
				circles.append(tuple(self.DATA_CIRCLES_ITEM.unpack(data)[0] for _ in range(circles_len)))
			projects = []
			projects_count, = self.DATA_PROJECTS_COUNT.unpack(data)
			for _ in range(projects_count):
				projects.append(tuple(strings[p] for p in self.DATA_PROJECTS_ITEM.unpack(data)))
		self.types = types
		self.objects = objects
		self.circles = circles
		self.projects = projects
		return True

	def generate(self):
		import json.decoder
		def decode(self, s, _w = json.decoder.WHITESPACE.match):
			obj, end = self.raw_decode(s, idx=_w(s, 0).end())
			end = _w(s, end).end()
			return obj
		json.decoder.JSONDecoder.decode = decode

		types_map = {}
		circles = set()
		objects = []
		projects = []
		for project, size, path, _ in self.flow.MemLeakProjects.iter_projects():
			author = self.flow.projectInfo.projects[project]['author']
			project_index = len(projects)
			projects.append((project, author))

			if size < self.MIN_SIZE:
				continue

			print '\tloading memory leak:', path
			memleak = utils.readData(path)
			object_map = {}
			for index in memleak:
				object_type = tuple(t.strip() for t in self.separaterRe.split(memleak[index][0]) if t.strip())
				if object_type[0] in ('type', 'class'):
					object_type = object_type[1:]
				if object_type == ('instancemethod', ):
					object_type = ('method', )
				if object_type not in types_map:
					types_map[object_type] = len(types_map)
				object_map[index] = len(objects)
				objects.append((project_index, int(index), types_map[object_type]))

			def on_cycle_found(indices):
				circles.add(tuple(object_map[i] for i in indices))
			MemLeakData.list_reference_cycles(memleak, on_cycle_found)
		circles = sorted(circles)
		types = sorted(types_map, key = lambda t: types_map[t])

		cls = self.__class__
		path = 'data/%s/%s.data' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		with open(path, 'wb') as f:
			compressor = utils.DataCompressor(f)
			stringset = set()
			for ts in types:
				for t in ts:
					stringset.add(t)
			for p, a in projects:
				stringset.add(p)
				stringset.add(a)

			self.DATA_STRINGSET_COUNT.pack(compressor, len(stringset))
			strings = {}
			for ss in stringset:
				s = ss if isinstance(ss, type(b'')) else ss.encode('utf-8', 'replace')
				self.DATA_STRINGSET_ITEM.pack(compressor, len(s))
				compressor.write(s)
				strings[ss] = len(strings)

			self.DATA_TYPES_COUNT.pack(compressor, len(types))
			for ts in types:
				self.DATA_TYPES_HEAD.pack(compressor, len(ts))
				for t in ts:
					self.DATA_TYPES_ITEM.pack(compressor, strings[t])
			self.DATA_OBJECTS_COUNT.pack(compressor, len(objects))
			for p, i, t in objects:
				self.DATA_OBJECTS_ITEM.pack(compressor, p, i, t)
			self.DATA_CIRCLES_COUNT.pack(compressor, len(circles))
			for cs in circles:
				self.DATA_CIRCLES_HEAD.pack(compressor, len(cs))
				for c in cs:
					self.DATA_CIRCLES_ITEM.pack(compressor, c)
			self.DATA_PROJECTS_COUNT.pack(compressor, len(projects))
			for p, a in projects:
				self.DATA_PROJECTS_ITEM.pack(compressor, strings[p], strings[a])
			compressor.flush()

		self.types = types
		self.objects = objects
		self.circles = circles
		self.projects = projects

		return True

	@staticmethod
	def _list_reference_cycles_dfs_proc(vertex, on_cycle_found):
		vertex.visited = -1
		vertex.prev.next = vertex.next
		if vertex.next:
			vertex.next.prev = vertex.prev
		for next_vertex in vertex.edges:
			if next_vertex.visited == 0:
				next_vertex.parent = vertex
				MemLeakData._list_reference_cycles_dfs_proc(next_vertex, on_cycle_found)
			elif next_vertex.visited == -1: # found a cycle
				on_cycle_found(next_vertex, vertex)
		vertex.visited = 1

	@staticmethod
	def list_reference_cycles(memleak, on_cycle_found):
		sys.setrecursionlimit(50000)

		# this is a graph DFS based algorithm
		vertices_list_head = MemLeakVertex() # dummy head of linked list
		vertices_list_head.next = None
		oid2vertex = {}

		# make vertices
		for i in memleak:
			vertex = MemLeakVertex()
			vertex.index = i
			vertex.visited = 0
			vertex.prev = vertices_list_head
			vertex.next = vertices_list_head.next
			if vertices_list_head.next:
				vertices_list_head.next.prev = vertex
			vertices_list_head.next = vertex
			oid2vertex[int(i)] = vertex

		# make edges
		vertex = vertices_list_head.next
		while vertex is not None:
			vertex.edges = [oid2vertex[r] for r in memleak[vertex.index][-1]]
			vertex = vertex.next

		def _on_cycle_found(vertex1, vertex2):
			"there is a path from vertex1 to vertex2, and an edge from vertex2 to vertex1"
			path = []
			v = vertex2
			while v is not vertex1:
				path = [v.index] + path
				v = v.parent
			path = [vertex1.index] + path
			on_cycle_found(path)

		# DFS visit all vertices
		while vertices_list_head.next is not None:
			vertex = vertices_list_head.next
			vertex.parent = None
			MemLeakData._list_reference_cycles_dfs_proc(vertex, _on_cycle_found)

		# clean up to remove reference cycles between Vertex objects
		for vertex in oid2vertex.values():
			vertex.edges = None
			vertex.prev = None
			vertex.next = None
			vertex.parent = None

class MemLeakStatistic(Step):
	'memory leak statistic'

	REQUIRE = 'MemLeakProjects', 'MemLeakData',

	CONTAINER_TYPES = (('list', ), ('dict', ), ('tuple', ), ('set', ))
	BUILTIN_TYPES = CONTAINER_TYPES + (('method', ), ('function', ), ('cell', ), ('module', ), ('traceback', ), ('frame', ), ('type', ), ('getset_descriptor', ))
	TYPES_LIST = tuple(t for t, in BUILTIN_TYPES) + ('user-defined', )

	def load(self):
		return False

	@classmethod
	def is__mro__(cls, data, circle):
		'class.__mro__造成的循环引用'
		if len(circle) != 2: return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		for i, t in enumerate(circle_types):
			if t == ('tuple', ) and circle_types[i - 1] not in cls.BUILTIN_TYPES:
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
		return False

	@classmethod
	def is_linked_list(cls, data, circle):
		'使用list实现循环链表造成的循环引用'
		circle_types = set(data.types[data.objects[i][2]] for i in circle)
		if circle_types == {('list', )}:
			return (('list', ), )
		return False

	@classmethod
	def is_self_reference(cls, data, circle):
		'class的自引用'
		if len(circle) not in (1, 2): return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		if len(circle_types) == 1:
			if circle_types[0] not in cls.BUILTIN_TYPES:
				return circle_types
		else:
			for i, t in enumerate(circle_types):
				if t == ('dict', ) and circle_types[i - 1] not in cls.BUILTIN_TYPES:
					circle_types = circle_types[i - 1:] + circle_types[:i - 1]
					return circle_types
		return False

	@classmethod
	def is_self_with_container(cls, data, circle):
		'class通过container自引用'
		if len(circle) not in (2, 3): return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		for i, t in enumerate(circle_types):
			if len(circle) == 2 and t in (('list', ), ('set', )) \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES:
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
			elif len(circle) == 3 and t == ('dict', ) \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES \
				and circle_types[i - 2] in cls.CONTAINER_TYPES:
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
		return False

	@classmethod
	def is_couple_reference(cls, data, circle):
		'两个class相互引用'
		if len(circle) not in (2, 4): return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		if len(circle) == 2:
			for t in circle_types:
				if t in cls.BUILTIN_TYPES:
					return False
			return circle_types
		for i, t in enumerate(circle_types):
			if t == circle_types[i - 2] == ('dict', ) \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES \
				and circle_types[i - 3] not in cls.BUILTIN_TYPES:
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
		return False

	@classmethod
	def is_couple_with_container(cls, data, circle):
		'两个class通过container相互引用'
		if len(circle) not in (3, 5): return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		for i, t in enumerate(circle_types):
			if len(circle) == 3 and t in cls.CONTAINER_TYPES \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES \
				and circle_types[i - 2] not in cls.BUILTIN_TYPES:
				circle_types = circle_types[i - 2:] + circle_types[:i - 2]
				return circle_types
			elif len(circle) == 5 and t == circle_types[i - 2] == ('dict', ) \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES \
				and circle_types[i - 3] not in cls.BUILTIN_TYPES \
				and circle_types[i - 4] in cls.CONTAINER_TYPES:
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
		return False

	@classmethod
	def is_couple_with_method(cls, data, circle):
		'两个class通过method相互引用'
		if len(circle) not in (3, 5): return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		for i, t in enumerate(circle_types):
			if len(circle) == 3 and t == ('method', ) \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES \
				and circle_types[i - 2] not in cls.BUILTIN_TYPES:
				circle_types = circle_types[i - 2:] + circle_types[:i - 2]
				return circle_types
			elif len(circle) == 5 and t == circle_types[i - 2] == ('dict', ) \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES \
				and circle_types[i - 3] not in cls.BUILTIN_TYPES \
				and circle_types[i - 4] == ('method', ):
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
		return False

	@classmethod
	def is_trinity_reference(cls, data, circle):
		'三个class相互引用'
		if len(circle) not in (3, 6): return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		if len(circle) == 3:
			for t in circle_types:
				if t in cls.BUILTIN_TYPES:
					return False
			return circle_types
		for i, t in enumerate(circle_types):
			if t == circle_types[i - 2] == circle_types[i - 4] == ('dict', ) \
				and circle_types[i - 1] not in cls.BUILTIN_TYPES \
				and circle_types[i - 3] not in cls.BUILTIN_TYPES \
				and circle_types[i - 5] not in cls.BUILTIN_TYPES:
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
		return False

	@classmethod
	def is_func_globals(cls, data, circle):
		'function.func_globals造成的循环引用'
		if len(circle) != 2: return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		for i, t in enumerate(circle_types):
			if t == ('dict', ) and circle_types[i - 1] == ('function', ):
				circle_types = circle_types[i - 1:] + circle_types[:i - 1]
				return circle_types
		return False

	@classmethod
	def is_closure_leak(cls, data, circle):
		'闭包造成的循环引用'
		if len(circle) < 3: return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		for i, t in enumerate(circle_types):
			if t == ('function', ):
				circle_types = circle_types[i:] + circle_types[:i]
				break
		else:
			return False
		if circle_types[:3] == (('function', ), ('tuple', ), ('cell', )):
			return circle_types
		return False

	@classmethod
	def is_instance_method(cls, data, circle):
		'属性引用instance method造成的循环引用'
		if len(circle) != 3: return False
		circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
		for i, t in enumerate(circle_types):
			if t == ('method', ):
				circle_types = circle_types[i:] + circle_types[:i]
				circle_types = circle_types[-1:] + circle_types[:-1]
				break
		else:
			return False
		if circle_types[0] == ('dict', ) and circle_types[-1] not in cls.BUILTIN_TYPES:
			return circle_types
		return False

	def generate(self):
		# 搜集定义的pattern判定函数
		pattern_filters = {}
		for name in dir(self.__class__):
			if not name.startswith('is_'): continue
			func = getattr(self, name)
			if not callable(func): continue
			name = name[3:]
			if name.endswith('__') and name[0] == '_' and name[1] != '_':
				name = '_' + name
			pattern_filters[name] = func

		max_size = 10
		data = self.flow.MemLeakData
		statistic_projects = {i: {
			'types': [0] * len(self.TYPES_LIST),
			'circles': {c: 0 for c in range(1, max_size + 2)},
			'origin_circles': {c: 0 for c in range(1, max_size + 2)},
			'caused_circles': {c: 0 for c in range(1, max_size + 2)},
			'pattern': {n: 0 for n in pattern_filters},
			'pcaused': {n: 0 for n in pattern_filters},
			'unknown': 0,
			'ucaused': 0,
			'project': p,
			'author': a,
		} for i, (p, a) in enumerate(data.projects)}

		for project_index, _, type_index in data.objects:
			object_type = data.types[type_index]
			if len(object_type) == 1 and object_type[0] in self.TYPES_LIST:
				statistic_projects[project_index]['types'][self.TYPES_LIST.index(object_type[0])] += 1
			else:
				statistic_projects[project_index]['types'][-1] += 1

		object_tags = [None] * len(data.objects)

		# 先扫一遍把确定pattern的记录下来，未确定的记录在unknown_circles
		pattern_references = {n: set() for n in pattern_filters}
		count_patterns_1 = {n: 0 for n in pattern_filters} # 满足pattern的循环引用
		count_patterns_2 = {n: 0 for n in pattern_filters} # 由pattern引发的泄露
		unknown_circles = set()
		for circle in data.circles:
			project_index = {data.objects[i][0] for i in circle}
			assert len(project_index) == 1
			project_index = project_index.pop()
			project = statistic_projects[project_index]
			for name, func in pattern_filters.iteritems():
				circle_types = func(data, circle)
				if circle_types is not False:
					project['pattern'][name] += 1
					count_patterns_1[name] += 1
					for i, c in enumerate(circle):
						pattern_references[name].add((circle[i - 1], c))
					if len(circle) > max_size:
						project['origin_circles'][max_size + 1] += 1
					else:
						project['origin_circles'][len(circle)] += 1
					for object_index in circle:
						if object_tags[object_index] is None:
							object_tags[object_index] = (name, 0)
					break
			if circle_types is False:
				unknown_circles.add((project_index, circle))
			if len(circle) > max_size:
				project['circles'][max_size + 1] += 1
			else:
				project['circles'][len(circle)] += 1

		# 反复扫unknown_circles，找到和已知pattern关联的circle
		found_circle_pattern = None
		while found_circle_pattern or found_circle_pattern is None:
			if found_circle_pattern:
				unknown_circles = unknown_circles - found_circle_pattern
			found_circle_pattern = set()
			for project_index, circle in unknown_circles:
				for name, references in pattern_references.iteritems():
					if [c for i, c in enumerate(circle) if (circle[i - 1], c) in references]:
						for i, c in enumerate(circle):
							references.add((circle[i - 1], c))
						found_circle_pattern.add((project_index, circle))
						count_patterns_2[name] += 1
						project = statistic_projects[project_index]
						project['pcaused'][name] += 1
						if len(circle) > max_size:
							project['caused_circles'][max_size + 1] += 1
						else:
							project['caused_circles'][len(circle)] += 1
						for object_index in circle:
							if object_tags[object_index] is None:
								object_tags[object_index] = (name, 1)
						break

		# 按环从小到大扫unknown_circles，忽略和小环关联的circle
		types_set = {}
		count_unknown_1 = {size: 0 for size in range(1, max_size + 2)} # 统计未知pattern的循环引用
		count_unknown_2 = {size: 0 for size in range(1, max_size + 2)} # 由未知pattern引发的泄露
		unknown_references = set()
		for size in range(1, max_size + 2):
			accessed_circles = set()
			for project_index, circle in unknown_circles:
				if min(len(circle), max_size + 1) != size: continue
				accessed_circles.add((project_index, circle))
				relation = [c for i, c in enumerate(circle) if (circle[i - 1], c) in unknown_references]
				for i, c in enumerate(circle):
					unknown_references.add((circle[i - 1], c))
				project = statistic_projects[project_index]
				if not relation:
					project['unknown'] += 1
					count_unknown_1[size] += 1
					if len(circle) > max_size:
						project['origin_circles'][max_size + 1] += 1
					else:
						project['origin_circles'][len(circle)] += 1
					for object_index in circle:
						if object_tags[object_index] is None:
							object_tags[object_index] = ('unknown', 0)
					if size == 4:
						circle_types = tuple(data.types[data.objects[i][2]] for i in circle)
						# if circle_types not in types_set:
						# 	print circle_types, data.projects[data.objects[circle[0]][0]]
						# types_set[circle_types] = types_set.get(circle_types, 0) + 1
				else:
					project['ucaused'] += 1
					count_unknown_2[size] += 1
					if len(circle) > max_size:
						project['caused_circles'][max_size + 1] += 1
					else:
						project['caused_circles'][len(circle)] += 1
					for object_index in circle:
						if object_tags[object_index] is None:
							object_tags[object_index] = ('unknown', 1)
			unknown_circles = unknown_circles - accessed_circles

		for circle_types, count in types_set.iteritems():
			print count, circle_types
		print '\n'

		print 'total:', len(data.circles), '\n'

		print 'unknown:', sum(count_unknown_1.values()), sum(count_unknown_2.values())
		for size in range(1, max_size + 2):
			if size == 11:
				print '>10', count_unknown_1[size], count_unknown_2[size]
			else:
				print size, count_unknown_1[size], count_unknown_2[size]
		print '\n'

		print 'pattern:', sum(count_patterns_1.values()), sum(count_patterns_2.values())
		for name in pattern_filters:
			print name, count_patterns_1[name], count_patterns_2[name]

		print 'skip csv!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
		return

		cls = self.__class__
		path = 'data/%s/%s.csv' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		with codecs.open(path, 'w', 'utf-8') as f:
			f.write('project,author,"unknown circles","caused by unknown circles",%(pattern_columns)s,%(circle_columns)s,%(origin_circle_columns)s,%(caused_circle_columns)s,%(type_columns)s\n' % {
				'pattern_columns': ','.join('"pattern %s circles","caused by pattern %s circles"' % (n, n) for n in pattern_filters),
				'circle_columns': ','.join('"circle size %s"' % (('of %d' % c) if c <= max_size else ('> %d' % max_size)) for c in range(1, max_size + 2)),
				'origin_circle_columns': ','.join('"origin circle size %s"' % (('of %d' % c) if c <= max_size else ('> %d' % max_size)) for c in range(1, max_size + 2)),
				'caused_circle_columns': ','.join('"caused circle size %s"' % (('of %d' % c) if c <= max_size else ('> %d' % max_size)) for c in range(1, max_size + 2)),
				'type_columns': ','.join('"type of %s"' % n for n in self.TYPES_LIST),
			})
			for i in statistic_projects:
				project = statistic_projects[i]
				f.write('"%(project)s","%(author)s",%(unknown)d,%(ucaused)d,%(pattern_columns)s,%(circle_columns)s,%(origin_circle_columns)s,%(caused_circle_columns)s,%(type_columns)s\n' % {
					'pattern_columns': ','.join('%d,%d' % (project['pattern'][n], project['pcaused'][n]) for n in pattern_filters),
					'circle_columns': ','.join(str(project['circles'][c]) for c in range(1, max_size + 2)),
					'origin_circle_columns': ','.join(str(project['origin_circles'][c]) for c in range(1, max_size + 2)),
					'caused_circle_columns': ','.join(str(project['caused_circles'][c]) for c in range(1, max_size + 2)),
					'type_columns': ','.join(str(c) for c in project['types']),
					'unknown': project['unknown'],
					'ucaused': project['ucaused'],
					'project': project['project'],
					'author': project['author'],
				})

		import json.decoder
		def decode(self, s, _w = json.decoder.WHITESPACE.match):
			obj, end = self.raw_decode(s, idx=_w(s, 0).end())
			end = _w(s, end).end()
			return obj
		json.decoder.JSONDecoder.decode = decode

		objects_columns = tuple(pattern_filters) + ('unknown', )
		path = 'data/%s/%s_objects.csv' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		with codecs.open(path, 'w', 'utf-8') as f:
			f.write('project,author,%(pattern_columns)s\n' % {
				'pattern_columns': ','.join('"pattern %s objects","caused by pattern %s circle objects","other caused by pattern %s objects"' % (n, n, n) for n in objects_columns),
			})
			for project_index, (project_name, _) in enumerate(data.projects):
				path = self.flow.MemLeakProjects.get_path(project_name)
				object_statistic = {n: [0, 0, 0] for n in objects_columns}

				if self.flow.MemLeakProjects.data[project_name]['size'] < MemLeakData.MIN_SIZE:
					f.write('"%(project)s","%(author)s",%(pattern_columns)s\n' % {
						'pattern_columns': ','.join(','.join(map(str, object_statistic[n])) for n in objects_columns),
						'project': project_statistic['project'],
						'author': project_statistic['author'],
					})
					continue

				print '\tloading memory leak:', path
				memleak = utils.readData(path)

				object_map = {o_id: i for i, (p_id, o_id, _) in enumerate(data.objects) if p_id == project_index}

				found_tags = True
				while found_tags:
					found_tags = False
					for o_id, index in object_map.items():
						if object_tags[index] is None:
							continue
						pattern_name, _ = object_tags[index]
						for related_object in memleak[str(o_id)][-1]:
							related_index = object_map[related_object]
							if object_tags[related_index] is None:
								object_tags[related_index] = (pattern_name, 2)

				for o_id, index in object_map.items():
					if object_tags[index] is None:
						object_statistic['unknown'][2] += 1
						continue
					pattern_name, caused_type = object_tags[index]
					object_statistic[pattern_name][caused_type] += 1

				project_statistic = statistic_projects[project_index]
				assert sum(project_statistic['types']) == sum(sum(v) for v in object_statistic.values()) == len(object_map)

				f.write('"%(project)s","%(author)s",%(pattern_columns)s\n' % {
					'pattern_columns': ','.join(','.join(map(str, object_statistic[n])) for n in objects_columns),
					'project': project_statistic['project'],
					'author': project_statistic['author'],
				})

class MemLeakStatisticS_Data(object):
	__slots__ = 'types', 'objects'

class MemLeakStatisticS(Step):
	'memory leak statistic S'

	REQUIRE = ()

	def load(self):
		return False

	def generate(self):
		d = MemLeakStatisticS_Data()
		path = MemLeakData.prepare()
		with open(path, 'rb') as f:
			data = f # utils.DataDecompressor(f)
			strings = []
			string_count, = MemLeakData.DATA_STRINGSET_COUNT.unpack(data)
			for _ in range(string_count):
				size, = MemLeakData.DATA_STRINGSET_ITEM.unpack(data)
				s = data.read(size)
				s = s if isinstance(s, str) else s.decode('utf-8')
				strings.append(s)
			d.types = []
			types_count, = MemLeakData.DATA_TYPES_COUNT.unpack(data)
			for _ in range(types_count):
				types_len, = MemLeakData.DATA_TYPES_HEAD.unpack(data)
				object_type = tuple(strings[MemLeakData.DATA_TYPES_ITEM.unpack(data)[0]] for _ in range(types_len))
				d.types.append(object_type)
			d.objects = []
			objects_count, = MemLeakData.DATA_OBJECTS_COUNT.unpack(data)
			for _ in range(objects_count):
				d.objects.append(MemLeakData.DATA_OBJECTS_ITEM.unpack(data))

			circles = set()
			circles_count, = MemLeakData.DATA_CIRCLES_COUNT.unpack(data)
			for _ in range(circles_count):
				circles_len, = MemLeakData.DATA_CIRCLES_HEAD.unpack(data)
				circle = tuple(MemLeakData.DATA_CIRCLES_ITEM.unpack(data)[0] for _ in range(circles_len))
				circle_types = MemLeakStatistic.is_couple_with_container(d, circle)
				if circle_types is not False:
					# circles.add((d.objects[circle[0]][0], circle_types))
					circles.add((d.objects[circle[0]][0], tuple(d.objects[i][1] for i in circle)))

			projects = []
			projects_count, = MemLeakData.DATA_PROJECTS_COUNT.unpack(data)
			for _ in range(projects_count):
				projects.append(tuple(strings[p] for p in MemLeakData.DATA_PROJECTS_ITEM.unpack(data)))

			import json.decoder
			def decode(self, s, _w = json.decoder.WHITESPACE.match):
				obj, end = self.raw_decode(s, idx=_w(s, 0).end())
				end = _w(s, end).end()
				return obj
			json.decoder.JSONDecoder.decode = decode

			memleak = utils.readData('data/memleak/sc2reader_20156ecd41d03cb581071dc74e23b63a3fffe2f0.json')
			objects = {}

			count = 0
			for project_index, data in circles:
				# print projects[project_index], data
				if projects[project_index][0] == 'sc2reader' and count < 10:
					count += 1
					for object_index in data:
						objects[str(object_index)] = memleak[str(object_index)]
			utils.saveData('data/sc2reader_couple_with_container.json', objects)

class MemLeakStaticAnalyseProjects(Step):
	'memory leak static analyse projects'

	REQUIRE = 'MemLeakProjects', 'projectInfo', 'travisYAML', 'gitRepo'

	pythonRe = re.compile(r'\s*python\s*:[\s\'"]*(?P<python>[0-9\.]+)[\s\'"]*', re.I)

	CIRCLE_TYPES = (
		'self_reference',
		'self_with_container',
		'couple_reference',
		'couple_with_container',
		'couple_with_method',
		'instance_method',
	)

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		self.data = utils.readData(path)
		return True

	def generate(self):
		cls = self.__class__
		static_projects = {}
		d = MemLeakStatisticS_Data()
		path = MemLeakData.prepare()
		with open(path, 'rb') as f:
			data = f # utils.DataDecompressor(f)
			strings = []
			string_count, = MemLeakData.DATA_STRINGSET_COUNT.unpack(data)
			for _ in range(string_count):
				size, = MemLeakData.DATA_STRINGSET_ITEM.unpack(data)
				s = data.read(size)
				s = s if isinstance(s, str) else s.decode('utf-8')
				strings.append(s)
			d.types = []
			types_count, = MemLeakData.DATA_TYPES_COUNT.unpack(data)
			for _ in range(types_count):
				types_len, = MemLeakData.DATA_TYPES_HEAD.unpack(data)
				object_type = tuple(strings[MemLeakData.DATA_TYPES_ITEM.unpack(data)[0]] for _ in range(types_len))
				d.types.append(object_type)
			d.objects = []
			objects_count, = MemLeakData.DATA_OBJECTS_COUNT.unpack(data)
			for _ in range(objects_count):
				d.objects.append(MemLeakData.DATA_OBJECTS_ITEM.unpack(data))

			circles = {}
			circles_count, = MemLeakData.DATA_CIRCLES_COUNT.unpack(data)
			for _ in range(circles_count):
				circles_len, = MemLeakData.DATA_CIRCLES_HEAD.unpack(data)
				circle = tuple(MemLeakData.DATA_CIRCLES_ITEM.unpack(data)[0] for _ in range(circles_len))
				project_index = d.objects[circle[0]][0]
				for name in self.CIRCLE_TYPES:
					circle_types = getattr(MemLeakStatistic, 'is_' + name)(d, circle)
					if circle_types is not False:
						circles.setdefault(project_index, {}).setdefault((name, circle_types), set()).add(circle)

			projects = []
			projects_count, = MemLeakData.DATA_PROJECTS_COUNT.unpack(data)
			for _ in range(projects_count):
				projects.append(tuple(strings[p] for p in MemLeakData.DATA_PROJECTS_ITEM.unpack(data)))

			import json.decoder
			def decode(self, s, _w = json.decoder.WHITESPACE.match):
				obj, end = self.raw_decode(s, idx=_w(s, 0).end())
				end = _w(s, end).end()
				return obj
			json.decoder.JSONDecoder.decode = decode

			pwd = os.getcwd()
			memleak_data = {}
			circles_data = {}
			coverage_data = {}
			for i, (project_index, circles_map) in enumerate(circles.items()):
				project_name, project_author = projects[project_index]
				if hasattr(self, 'data') and project_name not in self.data: continue
				if not os.path.isdir('data/gitRepo/%s' % project_name): continue
				path = self.flow.MemLeakProjects.get_path(project_name)
				print '\t%d/%d loading memory leak:' % (i, len(circles)), path
				memleak = utils.readData(path)

				commit = self.flow.MemLeakProjects.data[project_name]['commit']
				git_path = self.flow.gitRepo.prepare(project_name)
				os.chdir(git_path)
				assert os.system('git checkout %s' % commit) == 0
				os.chdir(pwd)

				search_paths = [os.path.dirname(git_path)] + [p for p, ds, fs in os.walk(git_path)]
				static_circles = set()
				static_memleak = {}
				static_coverage = {}
				object_type_source = {}
				source_dir = '/home/travis/build/runMemLeak/' + project_name + '/'
				for (pattern_name, circle_types), pattern_circles in circles_map.items():
					for circle in pattern_circles:
						is_covered_circle = True
						for j, object_index in enumerate(circle):
							object_type = circle_types[j]
							object_data = memleak[str(d.objects[object_index][1])]
							if object_type in MemLeakStatistic.BUILTIN_TYPES: continue
							for f, l in object_data[4]:
								if f.startswith(source_dir) and os.path.isfile(os.path.join(git_path, f[len(source_dir):])):
									static_coverage.setdefault(f[len(source_dir):], set()).add(l)
								elif os.path.isfile(os.path.join(git_path, f)):
									static_coverage.setdefault(f, set()).add(l)
							if object_data[2].startswith(source_dir) and os.path.isfile(os.path.join(git_path, object_data[2][len(source_dir):])):
								static_coverage.setdefault(object_data[2][len(source_dir):], set()).add(object_data[3])
							elif os.path.isfile(os.path.join(git_path, object_data[2])):
								static_coverage.setdefault(object_data[2], set()).add(object_data[3])

							if object_type not in object_type_source:
								f = ''
								l = set()
								filename = '/'.join(object_type[:-1]) + '.py'
								package = '/'.join(object_type[:-1]) + '/__init__.py'
								for p in search_paths:
									source_path = os.path.join(p, filename)
									if os.path.isfile(source_path):
										f = source_path[len(git_path):].lstrip('\\/').replace('\\', '/')
										break
									source_path = os.path.join(p, package)
									if os.path.isfile(source_path):
										f = source_path[len(git_path):].lstrip('\\/').replace('\\', '/')
										break
								if f and not object_type[-1].endswith('TestCase') and not object_type[-1].endswith('_unittest'):
									classRe = re.compile(r'\s*class\s+%s\b.*' % object_type[-1], re.I)
									with open(os.path.join(git_path, f), 'r') as s:
										lineno = 1
										line = s.readline()
										while line:
											classRe.match(line) and 'unittest.TestCase' not in line and l.add(lineno)
											lineno += 1
											line = s.readline()
								object_type_source[object_type] = f, l
							f, l = object_type_source[object_type]
							if f and l:
								static_coverage.setdefault(f, set()).update(l)
							else:
								is_covered_circle = False
						if not is_covered_circle: continue

						static_circles.add((pattern_name, circle_types))
						for object_index in circle:
							object_data = memleak[str(d.objects[object_index][1])]
							if object_data[2].startswith(source_dir):
								object_data[2] = object_data[2][len(source_dir):]
							object_data[4] = [[f[len(source_dir):] if f.startswith(source_dir) else f, l] for f, l in object_data[4]]
							static_memleak[str(d.objects[object_index][1])] = object_data

				if not static_memleak or not static_circles:
					continue

				builds = self.flow.projectInfo.get_builds(project_name)
				build = [b for b in builds if b['commit'] == commit].pop()
				travis_yml_root = self.flow.travisYAML.get_root(project_name)
				travis_yml_path = self.flow.travisYAML.get_path(build)
				with open(os.path.join(travis_yml_root, travis_yml_path), 'r') as f:
					line = f.readline()
					while line:
						m = self.pythonRe.match(line)
						if m:
							python_version = eval(m.group('python'))
							break
						line = f.readline()
					else:
						python_version = 'unknown'

				memleak_data[project_name] = static_memleak
				circles_data[project_name] = sorted(static_circles)
				coverage_data[project_name] = {f: sorted(l) for f, l in static_coverage.items()}
				static_projects[project_name] = [python_version, project_author, commit]
				memleak_path = 'data/%s/memleak/%s.json' % (cls.__module__.rpartition('.')[-1], project_name)
				circles_path = 'data/%s/circles/%s.json' % (cls.__module__.rpartition('.')[-1], project_name)
				coverage_path = 'data/%s/coverage/%s.json' % (cls.__module__.rpartition('.')[-1], project_name)
				utils.saveData(memleak_path, memleak_data[project_name])
				utils.saveData(circles_path, circles_data[project_name])
				utils.saveData(coverage_path, coverage_data[project_name])
				print '========================================================'
				print 'can static analyse:', len(static_projects), project_name

		path = 'data/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		self.data = static_projects
		utils.saveData(path, self.data)

		return True

class MemLeakStaticCircles(Step):
	'memory leak reference circles from static analysing'

	REQUIRE = 'MemLeakStaticAnalyseProjects', 'gitRepo'

	DATA_PATH = os.path.abspath('data/memleak')

	SELF_REFERENCE_PROJECTS = ('genmod', 'Mathics', 'pymtl', 'skoolkit', 'synapsePythonClient')
	SELF_WITH_CONTAINER_PROJECTS = ('pymtl', 'rabbit', 'skoolkit', 'ZODB')
	INSTANCE_METHOD_PROJECTS = ('boto', 'pymtl', 'pynag', 'PyPump', 'tweepy')
	COUPLE_REFERENCE_PROJECTS = ('boto', 'djblets', 'i8c', 'libNeuroML', 'pyexcel', 'pymtl', 'PyPump', 'skoolkit', 'WALinuxAgent', 'ZODB')
	COUPLE_WITH_CONTAINER_PROJECTS = ('boto', 'djblets', 'Hallo', 'libNeuroML', 'pymtl', 'PyPump', 'skoolkit', 'ZODB')
	COUPLE_WITH_METHOD_PROJECTS = ('boto', 'djblets', 'skoolkit')

	def load(self):
		data = {}
		cls = self.__class__
		for project in self.flow.MemLeakStaticAnalyseProjects.data:
			path = 'data/%s/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__, project)
			data[project] = utils.readData(path)
		self.data = data
		path = 'data/%s/%s.csv' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		return os.path.isfile(path)

	def generate(self):
		data = {}
		cls = self.__class__
		for project, (python_version, _, commit) in self.flow.MemLeakStaticAnalyseProjects.data.items():
			pattern = 'all'
			# if project not in self.COUPLE_REFERENCE_PROJECTS: continue
			# if project in ('skoolkit', 'WALinuxAgent'): continue
			# if project != 'boto': continue
			path = 'data/%s/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__, project)
			if os.path.isfile(path):
				data[project] = utils.readData(path)
				print '=================================================='
				print 'circles:', project, commit
				for name in sorted(data[project]):
					print name, [len(s) for s in data[project][name]]
				continue

			git_path = self.flow.gitRepo.prepare(project)
			python_cmd = 'python3' if python_version >= 3 else 'python'
			circles_path = 'data/%s/circles/%s.json' % (cls.__module__.rpartition('.')[-1], project)
			coverage_path = 'data/%s/coverage/%s.json' % (cls.__module__.rpartition('.')[-1], project)
			assert git_path and os.path.isfile(coverage_path)

			if sys.platform == 'win32':
				assert os.system('detector\\find_circles.bat %s %s %s %s %s %s %s' % (python_cmd, git_path, commit, circles_path, coverage_path, path, pattern)) == 0
			else:
				assert os.system('detector/find_circles.sh %s %s %s %s %s %s %s' % (python_cmd, git_path, commit, circles_path, coverage_path, path, pattern)) == 0

			assert os.path.isfile(path), (os.getcwd(), path)
			data[project] = utils.readData(path)

		self.data = data

		patterns = ('all', 'self_reference', 'self_with_container', 'instance_method', 'couple_reference', 'couple_with_container', 'couple_with_method')
		path = 'data/%s/%s.csv' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		with codecs.open(path, 'w', 'utf-8') as f:
			f.write('project,author,commit,%(pattern_columns)s\n' % {
				'pattern_columns': ','.join('"%s SP","%s SE","%s SN","%s DP","%s DN"' % (n, n, n, n, n) for n in patterns),
			})
			for project in sorted(self.data):
				python_version, author, commit = self.flow.MemLeakStaticAnalyseProjects.data[project]
				f.write('"%(project)s","%(author)s","%(commit)s",%(pattern_columns)s\n' % {
					'pattern_columns': ','.join(','.join(map(lambda c: str(len(c)), self.data[project][n])) for n in patterns),
					'project': project,
					'author': author,
					'commit': commit,
				})

		return True
