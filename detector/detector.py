# -*- coding: utf-8 -*-

import traceback
import warnings
import weakref
import sys
import ast
import os
import _io

try:
	long
except:
	long = int

class _C:
	def _m(self): pass
class _B(object): pass
PythonClassType = type(_C), type
PythonModuleType = type(os)
PythonStringType = type(''), type(b''), type(u'')
PythonIntegerType = int, long
PythonDictType = type(_B.__dict__), dict
PythonFunctionType = type(lambda: None), type(os.open), type(_C._m), type(_C()._m), type(object.__hash__), type(object.__sizeof__)
PythonMemberType = type(_io.TextIOWrapper.closed), type(_io.TextIOWrapper.encoding)
PythonCodeType = type((lambda:None).__code__)

sys.setrecursionlimit(50000)

LOG_LEVEL = 5

NO_FIXED_TYPES = False

def log(level, *args):
	if LOG_LEVEL is False or (LOG_LEVEL is not True and level < LOG_LEVEL): return
	sys.stdout.write(' '.join(map(str, args)) + '\n')

def info(*args): log(0, *args)

WARN_LEVEL = 5

def warn_level(level):
	return WARN_LEVEL is True or (WARN_LEVEL is not False and level >= WARN_LEVEL)

SHOW_MODULE_BINDINGS = {
	'demo',
}

SHOW_FUNCTION_INVOCATION = {
	'main': 'demo.py',
}

MAX_UNION_CONSTANT = 30
MAX_FIXED_SEQUENCE = 10000
MAX_INVOKE_NODE = 100
MAX_INVOKE_INST = 10

class Node(object):
	@staticmethod
	def Root(source, module_name, filename, ast_node):
		root = Node()
		root.parent = None
		root.source = source
		root.module_name = module_name
		root.filename = filename
		root.ast_node = ast_node
		root.start = 0
		root.end = len(source)

		# function _splitlines_no_ff from ast module
		idx = 0
		lines = []
		next_line = ''
		while idx < len(source):
			c = source[idx]
			next_line += c
			idx += 1
			# Keep \r\n together
			if c == '\r' and idx < len(source) and source[idx] == '\n':
				next_line += '\n'
				idx += 1
			if c in '\r\n':
				lines.append((idx - len(next_line), next_line))
				next_line = ''

		if next_line:
			lines.append((idx - len(next_line), next_line))
		root.lines = lines

		if hasattr(ast_node, 'lineno'):
			root.start_lineno = ast_node.lineno
			root.start_col_offset = ast_node.col_offset
		else:
			root.start_lineno = 0
			root.start_col_offset = 0

		if hasattr(ast_node, 'end_lineno'):
			root.end_lineno = ast_node.end_lineno
			root.end_col_offset = ast_node.end_col_offset
		else:
			root.end_lineno = len(lines)
			root.end_col_offset = lines and len(lines[-1]) or 0

		root._hash = root.get_hash()
		return root

	def Child(parent, ast_node):
		child = Node()
		child.parent = parent
		child.ast_node = ast_node

		if not hasattr(ast_node, 'lineno'):
			child.start_lineno = parent.start_lineno
			child.start_col_offset = parent.start_col_offset
			child.end_lineno = parent.end_lineno
			child.end_col_offset = parent.end_col_offset
			child.start = parent.start
			child.end = parent.end
			child.filename = parent.filename
			child._hash = child.get_hash()
			return child

		child.start_lineno = ast_node.lineno
		child.start_col_offset = ast_node.col_offset

		if hasattr(ast_node, 'end_lineno'):
			child.end_lineno = ast_node.end_lineno
			child.end_col_offset = ast_node.end_col_offset
		else:
			def _iter_children(ast_node):
				for name in ast_node._fields:
					value = getattr(ast_node, name, None)
					if isinstance(value, ast.AST):
						if not hasattr(value, 'lineno'):
							for c in _iter_children(value):
								yield c
						else:
							yield value
					elif isinstance(value, list):
						for item in value:
							if isinstance(item, ast.AST):
								if not hasattr(item, 'lineno'):
									for c in _iter_children(item):
										yield c
								else:
									yield item

			nodes = sorted((n.lineno, n.col_offset, n) for n in _iter_children(parent.ast_node))
			for i, (_, _, n) in enumerate(nodes):
				if n is ast_node:
					if i + 1 < len(nodes):
						child.end_lineno, child.end_col_offset, _ = nodes[i + 1]
					else:
						child.end_lineno = parent.end_lineno
						child.end_col_offset = parent.end_col_offset
					break
			else:
				assert False, '%s is not child of %s: %s' % (ast_node, parent, nodes)

		root = parent.root
		lines = root.lines

		start_idx, start_line = lines[child.start_lineno - 1]
		try:
			child.start = start_idx + len(start_line.encode()[:child.start_col_offset].decode())
		except:
			child.start = start_idx + len(start_line[:child.start_col_offset])

		end_idx, end_line = lines[child.end_lineno - 1]
		try:
			child.end = end_idx + len(end_line.encode()[:child.end_col_offset].decode())
		except:
			child.end = end_idx + len(end_line[:child.end_col_offset])

		child.filename = root.filename
		child._hash = child.get_hash()

		return child

	@property
	def root(self):
		return self.parent and self.parent.root or self

	def __repr__(self):
		if self.start_lineno is None:
			return '<%s from %r>' % (self.ast_node.__class__.__name__, self.root.filename)

		source = self.root.source[self.start:self.end]
		if len(source) > 100:
			source = source[:30] + ' ... ' + source[-30:]
		return '<%s %r from %r [%d:%d - %d:%d]>' % (
			self.ast_node.__class__.__name__, source, self.filename,
			self.start_lineno, self.start_col_offset, self.end_lineno, self.end_col_offset)

	def get_hash(self):
		return hash((self.filename, self.start, self.end))

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.filename == other.filename and self.start == other.start and self.end == other.end

class Binding(object):
	ATTRIBUTE = 0   # attr accessed with "." on some other object
	CLASS = 1       # class definition
	CONSTRUCTOR = 2 # __init__ functions in classes
	FUNCTION = 3    # plain function
	VARIABLE = 4    # local variable
	MODULE = 5      # module objects
	RESULT = 7      # function result
	YIELD = 8       # function yield

	NameMap = {
		ATTRIBUTE: 'Attribute',
		CLASS: 'Class',
		CONSTRUCTOR: 'Constructor',
		FUNCTION: 'Function',
		VARIABLE: 'Variable',
		MODULE: 'Module',
		RESULT: 'Result',
		YIELD: 'Yield',
	}

	def __init__(self, kind, name, node, type):
		self.kind = kind
		self.name = name
		self.node = node
		self.type = type
		self._hash = hash((self.kind, self.name, self.node, self.type))

	def __repr__(self):
		return '<Binding %s "%s" of %s %s>' % (
			self.NameMap[self.kind], self.name, self.node, self.type)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.kind == other.kind and self.name == other.name and self.node == other.node and self.type == other.type

class Scope(object):
	CLASS = 0
	INSTANCE = 1
	FUNCTION = 2
	INVOKE = 3
	MODULE = 4
	BRANCH = 6
	PROBABLE = 7

	NameMap = {
		CLASS: 'Class',
		INSTANCE: 'Instance',
		FUNCTION: 'Function',
		INVOKE: 'Invoke',
		MODULE: 'Module',
		BRANCH: 'Branch',
		PROBABLE: 'Probable',
	}

	def __init__(self, kind, type, parent):
		self.kind = kind
		self.parent = parent
		self.result = None
		self.bindings = {}
		self.locals = {}

		if not type or self.kind == self.MODULE:
			self.type = type
		else:
			self.type = weakref.proxy(type)

		if self.kind in (self.CLASS, self.INVOKE):
			self.globals = set()
			self.nonlocals = set()

	def __repr__(self):
		return '<Scope %s of %s>' % (self.NameMap[self.kind], self.type.__repr__())

	def is_probable(self):
		if self.kind == self.PROBABLE:
			return True
		elif self.parent:
			return self.parent.is_probable()
		else:
			return False

	def is_branch(self):
		if self.kind == self.BRANCH:
			return True
		elif self.parent:
			return self.parent.is_branch()
		else:
			return False

	def is_global(self, name):
		if self.kind in (self.CLASS, self.INVOKE):
			return name in self.globals
		elif self.parent:
			return self.parent.is_global(name)
		else:
			return False

	def add_global(self, name):
		if self.kind in (self.CLASS, self.INVOKE):
			self.globals.add(name)
		elif self.parent:
			self.parent.add_global(name)

	def is_nonlocal(self, name):
		if self.kind in (self.CLASS, self.INVOKE):
			return name in self.nonlocals
		elif self.parent:
			return self.parent.is_nonlocal(name)
		else:
			return False

	def add_nonlocal(self, name):
		if self.kind in (self.CLASS, self.INVOKE):
			self.nonlocals.add(name)
		elif self.parent:
			self.parent.add_nonlocal(name)

	@property
	def module_scope(self):
		if self.kind == self.MODULE:
			return self
		elif self.parent:
			return self.parent.module_scope
		else:
			return None

	def lookup_bindings(self, name, _nonlocal):
		if self.is_global(name):
			module_scope = self.module_scope
			if module_scope and module_scope is not self and name in module_scope.bindings:
				return module_scope.bindings[name]

		if not _nonlocal and not self.is_nonlocal(name) and self.locals and name in self.locals:
			return {self.locals[name]}
		elif name in self.bindings:
			return self.bindings[name]

		if self.parent:
			return self.parent.lookup_bindings(name, _nonlocal)

		return None

	def lookup_type(self, scope, node, name, _nonlocal):
		bindings = self.lookup_bindings(name, _nonlocal)
		return bindings and UnionType(scope, node, *(b.type for b in bindings)) or None

	def merge(self, other):
		for name in other.bindings:
			self.bindings.setdefault(name, set()).update(other.bindings[name])
			for binding in other.bindings[name]:
				if isinstance(binding.type, UnionType):
					for t in binding.type.types:
						if t.bindings is not None:
							t.bindings[id(self), name] = weakref.ref(self)
				elif binding.type.bindings is not None:
					binding.type.bindings[id(self), name] = weakref.ref(self)
		if other.result:
			self.result = self.result or set()
			self.result.update(other.result)

	def combine(self, scope, node, ignore_origin, *others):
		locals = set()
		for other in others:
			self.merge(other)
			if other.locals:
				locals.update(other.locals)
		for name in locals:
			bindings = set()
			if not ignore_origin and name in self.locals:
				bindings.add(self.locals[name])
			for other in others:
				if name in other.locals:
					bindings.add(other.locals[name])
				else:
					bindings.update(other.lookup_bindings(name, False))
			self.locals[name] = Binding(self.get_binding_kind(name), name, node, UnionType(scope, node, *(b.type for b in bindings)))

	def get_binding_kind(self, name):
		if self.kind == self.CLASS:
			if name == '__init__':
				kind = Binding.CONSTRUCTOR
			else:
				kind = Binding.CLASS
		elif self.kind == self.INSTANCE:
			kind = Binding.ATTRIBUTE
		elif self.kind == self.FUNCTION:
			kind = Binding.FUNCTION
		elif self.kind == self.MODULE:
			kind = Binding.MODULE
		elif self.kind in (self.INVOKE, self.BRANCH, self.PROBABLE):
			kind = Binding.VARIABLE
		return kind

	def assign(self, scope, node, name, type):
		if scope and scope.is_probable():
			if isinstance(type, (BooleanType, IntegerType, FloatType, ComplexType, StringType)) and type.value != '?':
				type = type.__class__('?')
			elif isinstance(type, FixedDictType):
				type = DictType(UnionType(scope, node, *type.entries.keys()), UnionType(scope, node, *type.entries.values()))
			elif isinstance(type, FixedListType):
				type = ListType(UnionType(scope, node, *type.items))
			elif isinstance(type, FixedTupleType):
				type = TupleType(UnionType(scope, node, *type.items))

		binding = Binding(self.get_binding_kind(name), name, node, type)
		self.bindings.setdefault(name, set()).add(binding)
		if isinstance(type, UnionType):
			for t in type.types:
				if t.bindings is not None:
					t.bindings[id(self), name] = weakref.ref(self)
		elif type.bindings is not None:
			type.bindings[id(self), name] = weakref.ref(self)
		if self.kind in (self.CLASS, self.INVOKE, self.BRANCH, self.PROBABLE) or (self.kind == self.INSTANCE and (not scope or (not scope.is_probable() and not scope.is_branch()))):
			self.locals[name] = binding

	def set_result(self, node, type, kind):
		self.result = self.result or set()
		self.result.add(Binding(kind, Binding.NameMap[kind], node, type))

class Type(object):
	bases = ()
	scope = None
	bindings = None
	builtins = None

	@property
	def type_name(self):
		return self.__class__.__name__

	def get_mro(self):
		return (self, )

	def __repr__(self):
		raise NotImplementedError

	def __hash__(self):
		raise NotImplementedError

	def __eq__(self, other):
		raise NotImplementedError

	def __lt__(self, other):
		hash_self = hash(self)
		hash_other = hash(other)
		if hash_self != hash_other:
			return hash_self < hash_other
		elif self == other:
			return False
		else:
			return id(self) < id(other)

	def to_boolean(self, scope, node):
		raise NotImplementedError

	def get_type(self, scope, node):
		raise NotImplementedError

	def update_bindings(self, scope, node, bindings):
		if self.bindings is None: return
		self.bindings.update(bindings)
		for (_, name), ref in self.bindings.items():
			binding = ref and ref()
			binding and binding.assign(scope, node, name, self)

	def lookup_attr(self, scope, node, name, codebase, value_node, value_type):
		if name == '__class__':
			return self.get_type(scope, node)
		elif name == '__dict__':
			if not self.scope:
				return UnknownType(node, 'unsupported __dict__ of %s' % self, None)
			return BuiltinDictType(self)

		value_type = value_type or self
		if isinstance(self, InstanceType):
			class_type = self.class_type
		elif isinstance(self, ClassType):
			class_type = self.metaclass or self
		else:
			class_type = self

		if self.builtins and name in self.builtins:
			attr_type = self.builtins[name]
		else:
			attr_type = self.scope and self.scope.lookup_type(scope, node, name, not isinstance(self, InstanceType))

		if not attr_type:
			for base in (self.bases or class_type.bases):
				attr_type = base.lookup_attr(scope, node, name, codebase, value_node, value_type)
				if attr_type: break

		if not attr_type: return attr_type

		attr_types = set()
		desc_types = attr_type.types if isinstance(attr_type, UnionType) else {attr_type}
		for attr_type in desc_types:
			if isinstance(attr_type, PropertyType):
				attr_types.add(attr_type.fget.invoke(scope, node, [value_type], None, None, None))
			elif isinstance(attr_type, MethodType):
				attr_types.add(attr_type)
			elif isinstance(attr_type, BuiltinMethodType_base):
				attr_types.add(MethodType(class_type, attr_type, value_type))
			elif not isinstance(attr_type, FunctionType) or getattr(attr_type, 'is_static_method', False):
				attr_types.add(attr_type)
			elif not isinstance(value_type, InstanceType):
				if getattr(attr_type, 'is_class_method', False):
					attr_types.add(MethodType(class_type, attr_type, value_type))
				else:
					attr_types.add(attr_type)
			elif value_type.scope and name in value_type.scope.bindings:
				attr_types.add(attr_type)
			elif getattr(attr_type, 'is_class_method', False):
				attr_types.add(MethodType(class_type, attr_type, value_type.class_type))
			else:
				attr_types.add(MethodType(class_type, attr_type, value_type))
		return UnionType(scope, node, *attr_types)

	def foreach_type(self, scope, node):
		assert self is not UndefinedType
		return UnknownType(node, 'unsupported foreach', self)

	def get_subscript(self, scope, node, key):
		assert self is not UndefinedType
		return UnknownType(node, 'unsupported get subscript', self)

	def set_subscript(self, scope, node, key, value):
		assert self is not UndefinedType
		return UnknownType(node, 'unsupported set subscript', self)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		assert self is not UndefinedType
		return UnknownType(node, 'unsupported call', self)

class BooleanType(Type):
	TRUE = None
	FALSE = None
	UNKNOWN = None

	COERCE_NUMBER_LEVEL = 0

	def __new__(cls, value):
		if NO_FIXED_TYPES: value = '?'
		if value is True:
			if cls.TRUE is None:
				cls.TRUE = super(BooleanType, BooleanType).__new__(cls)
				cls.TRUE.value = True
				cls.TRUE._hash = hash((cls.TRUE.type_name, cls.TRUE.value))
			return cls.TRUE
		elif value is False:
			if cls.FALSE is None:
				cls.FALSE = super(BooleanType, BooleanType).__new__(cls)
				cls.FALSE.value = False
				cls.FALSE._hash = hash((cls.FALSE.type_name, cls.FALSE.value))
			return cls.FALSE
		else:
			if cls.UNKNOWN is None:
				cls.UNKNOWN = super(BooleanType, BooleanType).__new__(cls)
				cls.UNKNOWN.value = '?'
				cls.UNKNOWN._hash = hash((cls.UNKNOWN.type_name, cls.UNKNOWN.value))
			return cls.UNKNOWN

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.value)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.value == other.value

	def to_boolean(self, scope, node):
		return self

	def get_type(self, scope, node):
		return BUILTINS['bool']

class BuiltinDictType(Type):
	def __init__(self, binding_type):
		assert binding_type.scope, binding_type
		self.binding_type = binding_type
		self._hash = hash((self.type_name, self.binding_type))

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.binding_type)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.binding_type == other.binding_type

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['dict']

	def foreach_type(self, scope, node):
		return StringType('?')

	def get_subscript(self, scope, node, key):
		bindings = set()
		for name in self.binding_type.scope.bindings:
			bindings |= self.binding_type.scope.bindings[name]
		return UnionType(scope, node, *(b.type for b in bindings))

	def set_subscript(self, scope, node, key, value):
		if isinstance(key, StringType) and key.value != '?':
			self.binding_type.scope.assign(scope, node, key.value, value)
		elif isinstance(key, UnionType):
			for t in key.types:
				self.set_subscript(scope, node, t, value)
		else:
			warn_level(2) and warnings.warn('unsupported set subscript key: %s %s %s' % (key, self, node), RuntimeWarning)
		return UndefinedType

class ClassType(Type):
	classes = set()

	def __init__(self, parent, node, name, bases, metaclass):
		self.name = name
		self.node = node
		self.bases = bases
		self.metaclass = metaclass
		self._hash = hash((self.type_name, self.name, self.node, self.bases))
		self.scope = Scope(Scope.CLASS, self, parent)
		self.instances = set()
		self.classes.add(self)
		self.mro_types = None

	@staticmethod
	def _is_object(bases):
		global BUILTINS
		return len(bases) == 1 and bases[0] is BUILTINS['object']

	@staticmethod
	def _not_in_tail(t, l):
		if not l or len(l) <= 1:
			return True
		return t not in l[1:]

	def get_mro(self):
		if self.mro_types:
			return (self, ) + self.mro_types
		elif not self.bases:
			return (self, )
		elif self._is_object(self.bases):
			return (self, BUILTINS['object'], )
		mro_types = []
		merge = [list(base.get_mro()) for base in self.bases] + [list(self.bases)]
		while True:
			while [] in merge:
				merge.remove([])
			if all([self._is_object(m) for m in merge]):
				merge = merge and [BUILTINS['object']]
				break
			head = None
			for index, sublist in enumerate(merge):
				if self._is_object(sublist): continue
				if all(self._not_in_tail(sublist[0], l) for l in merge[index:]):
					head = sublist[0]
					break
			if head:
				mro_types.append(head)
				for l in merge:
					if head in l:
						l.remove(head)
		self.mro_types = tuple(mro_types + merge)
		return (self, ) + self.mro_types

	def __repr__(self):
		return '<%s of %s %s>' % (self.type_name, self.name, self.node)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.name == other.name and self.node == other.node and self.bases == other.bases

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return self.metaclass or BUILTINS['type']

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		for class_type in self.get_mro():
			if class_type.builtins and '__new__' in class_type.builtins:
				new_func = class_type.builtins['__new__']
			elif class_type.scope and '__new__' in class_type.scope.bindings:
				new_func = UnionType(scope, node, *(b.type for b in class_type.scope.bindings['__new__']))
			else:
				continue
			if new_func:
				if args:
					new_args = (self, ) + tuple(args)
				else:
					new_args = (self, )
				instance_type = new_func.invoke(scope, node, new_args, keywords, starargs, kwargs)
				break
		else:
			instance_type = InstanceType(node, self, None)

		init_func = self.lookup_attr(scope, node, '__init__', None, None, instance_type)
		if init_func:
			init_func.invoke(scope, node, args, keywords, starargs, kwargs)

		return instance_type

class ComplexType(Type):
	COERCE_NUMBER_LEVEL = 3

	def __init__(self, value):
		if NO_FIXED_TYPES: value = '?'
		if isinstance(value, (complex, int, long, float)):
			self.value = value
		else:
			self.value = '?'
		self._hash = hash((self.type_name, self.value))

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.value)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.value == other.value

	def to_boolean(self, scope, node):
		if isinstance(self.value, complex):
			return BooleanType(bool(self.value))
		else:
			return BooleanType(self.value)

	def get_type(self, scope, node):
		return BUILTINS['complex']

class DictType(Type):
	def __init__(self, key, value):
		self.key = key
		self.value = value
		self.bindings = {}
		self._hash = hash((self.type_name, self.key, self.value))
		assert isinstance(self.key, Type) and isinstance(self.value, Type)

	def __repr__(self):
		return '<%s of %s : %s>' % (self.type_name, self.key, self.value)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.key == other.key and self.value == other.value

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['dict']

	def foreach_type(self, scope, node):
		return self.key

	def get_subscript(self, scope, node, key):
		return self.value

	def set_subscript(self, scope, node, key, value):
		dict_type = DictType(UnionType(scope, node, self.key, key), UnionType(scope, node, self.value, value))
		dict_type.update_bindings(scope, node, self.bindings)
		return dict_type

class FixedClassType(Type):
	def __init__(self, name, cls, members):
		self.name = name
		self.cls = cls
		self.builtins = members
		self._hash = hash((self.type_name, self.name, id(self.cls)))

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.name)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.name == other.name and self.cls is other.cls

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['type']

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		return InstanceType(node, self, None)

	def lookup_attr(self, scope, node, name, codebase, value_node, value_type):
		if name not in self.builtins and self.cls and hasattr(self.cls, name) and codebase:
			self.builtins[name] = codebase.get_python_type(scope, node, getattr(self.cls, name, None))
		return self.builtins.get(name, None)

class FixedDictType(Type):
	if NO_FIXED_TYPES:
		def __new__(cls, scope, node, entries):
			return DictType(UnionType(scope, node, *entries.keys()), UnionType(scope, node, *entries.values()))

	def __init__(self, scope, node, entries):
		self.entries = entries
		self.bindings = {}
		self._hash = hash((self.type_name, tuple(sorted(self.entries.items()))))
		for key in self.entries:
			assert (key is NoneType or (isinstance(key, (BooleanType, ComplexType, FloatType, IntegerType, StringType)) and key.value != '?')) and isinstance(self.entries[key], Type)

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.entries)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.entries == other.entries

	def to_boolean(self, scope, node):
		return BooleanType(bool(self.entries))

	def get_type(self, scope, node):
		return BUILTINS['dict']

	def foreach_type(self, scope, node):
		return UnionType(scope, node, *self.entries.keys())

	def get_subscript(self, scope, node, key):
		if key in self.entries:
			return self.entries[key]
		return UnionType(scope, node, *self.entries.values())

	def set_subscript(self, scope, node, key, value):
		if key is not NoneType and (not isinstance(key, (BooleanType, ComplexType, FloatType, IntegerType, StringType)) or key.value == '?'):
			dict_type = DictType(UnionType(scope, node, key, *self.entries.keys()), UnionType(scope, node, value, *self.entries.values()))
		else:
			entries = {k: v for k, v in self.entries.items()}
			entries[key] = value
			dict_type = FixedDictType(scope, node, entries)
		dict_type.update_bindings(scope, node, self.bindings)
		return dict_type

class FixedFunctionType(Type):
	def __init__(self, name, func, args, defaults, vararg, kwarg, result):
		self.name = name
		self.func = func
		self.args = args
		self.defaults = defaults
		self.vararg = vararg
		self.kwarg = kwarg
		self.result = result
		self._hash = hash((self.type_name, self.name, self.args, self.defaults, self.vararg, self.kwarg, self.result))

	def __repr__(self):
		return '<%s of %s(%s, %s, %s, %s) => %s>' % (self.type_name, self.name, self.args, self.defaults, self.vararg, self.kwarg, self.result)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.name == other.name and self.args == other.args and self.defaults == other.defaults and self.vararg == other.vararg and self.kwarg == other.kwarg and self.result == other.result

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return FunctionType_Type

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		return self.result

class FixedListType(Type):
	if NO_FIXED_TYPES:
		def __new__(cls, scope, node, *items):
			return ListType(UnionType(scope, node, *items))

	def __init__(self, scope, node, *items):
		self.items = items
		self.bindings = {}
		self._hash = hash((self.type_name, self.items))
		for item in self.items:
			assert isinstance(item, Type)

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.items)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.items == other.items

	def to_boolean(self, scope, node):
		return BooleanType(bool(self.items))

	def get_type(self, scope, node):
		return BUILTINS['list']

	def foreach_type(self, scope, node):
		return UnionType(scope, node, *self.items)

	def get_subscript(self, scope, node, key):
		if isinstance(key, SliceType):
			constant_slice = key.get_constant_slice()
			if constant_slice:
				return FixedListType(scope, node, *self.items[constant_slice])
			return ListType(UnionType(scope, node, *self.items))
		elif isinstance(key, (BooleanType, IntegerType)):
			if key.value != '?':
				try:
					return self.items[key.value]
				except Exception as e:
					return UnknownType(node, 'get subscript with exception: %s %s' % (key, e), self)
			return UnionType(scope, node, *self.items)
		elif isinstance(key, UnionType):
			return UnionType(scope, node, *[self.get_subscript(scope, node, k) for k in key.types])
		elif isinstance(key, UnknownType):
			warn_level(0) and warnings.warn('get subscript with key: %s %s %s' % (key, self, node), RuntimeWarning)
			return UnionType(scope, node, *self.items)
		return UnknownType(node, 'unsupported get subscript key: %s' % key, self)

	def set_subscript(self, scope, node, key, value):
		if isinstance(key, SliceType):
			constant_slice = key.get_constant_slice()
			if constant_slice and isinstance(value, (FixedListType, FixedTupleType)):
				items = [item for item in self.items]
				items[constant_slice] = value.items
				list_type = FixedListType(scope, node, *items)
			else:
				list_type = ListType(UnionType(scope, node, value.foreach_type(scope, node), *self.items))
		elif isinstance(key, (BooleanType, IntegerType)):
			if key.value != '?':
				items = [item for item in self.items]
				try:
					items[key.value] = value
				except Exception as e:
					warn_level(1) and warnings.warn('set subscript with exception: %s %s' % (e, node), RuntimeWarning)
					return self
				list_type = FixedListType(scope, node, *items)
			else:
				list_type = ListType(UnionType(scope, node, value, *self.items))
		elif isinstance(key, UnionType):
			list_type = UnionType(scope, node, *[self.set_subscript(scope, node, k, value) for k in key.types])
		elif isinstance(key, UnknownType):
			warn_level(0) and warnings.warn('set subscript with key: %s %s %s' % (key, self, node), RuntimeWarning)
			list_type = ListType(UnionType(scope, node, value, *self.items))
		else:
			warn_level(2) and warnings.warn('unsupported set subscript key: %s %s %s' % (key, self, node), RuntimeWarning)
			return self
		list_type.update_bindings(scope, node, self.bindings)
		return list_type

class FixedTupleType(Type):
	if NO_FIXED_TYPES:
		def __new__(cls, scope, node, *items):
			return TupleType(UnionType(scope, node, *items))

	def __init__(self, scope, node, *items):
		self.items = items
		self._hash = hash((self.type_name, self.items))
		for item in self.items:
			assert isinstance(item, Type)

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.items)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.items == other.items

	def to_boolean(self, scope, node):
		return BooleanType(bool(self.items))

	def get_type(self, scope, node):
		return BUILTINS['tuple']

	def foreach_type(self, scope, node):
		return UnionType(scope, node, *self.items)

	def get_subscript(self, scope, node, key):
		if isinstance(key, SliceType):
			constant_slice = key.get_constant_slice()
			if constant_slice:
				return FixedTupleType(scope, node, *self.items[constant_slice])
			return TupleType(UnionType(scope, node, *self.items))
		elif isinstance(key, (BooleanType, IntegerType)):
			if key.value != '?':
				try:
					return self.items[key.value]
				except Exception as e:
					return UnknownType(node, 'get subscript with exception: %s %s' % (key, e), self)
			return UnionType(scope, node, *self.items)
		elif isinstance(key, UnionType):
			return UnionType(scope, node, *[self.get_subscript(scope, node, k) for k in key.types])
		elif isinstance(key, UnknownType):
			warn_level(0) and warnings.warn('get subscript with key: %s %s %s' % (key, self, node), RuntimeWarning)
			return UnionType(scope, node, *self.items)
		return UnknownType(node, 'unsupported get subscript key: %s' % key, self)

	def set_subscript(self, scope, node, key, value):
		warn_level(2) and warnings.warn('unsupported set subscript: %s %s' % (self, node), RuntimeWarning)
		return UndefinedType

class FloatType(Type):
	COERCE_NUMBER_LEVEL = 2

	def __init__(self, value):
		if NO_FIXED_TYPES: value = '?'
		if isinstance(value, (int, long, float)):
			self.value = value
		else:
			self.value = '?'
		self._hash = hash((self.type_name, self.value))

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.value)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.value == other.value

	def to_boolean(self, scope, node):
		if isinstance(self.value, (int, long, float)):
			return BooleanType(bool(self.value))
		else:
			return BooleanType(self.value)

	def get_type(self, scope, node):
		return BUILTINS['float']

class FunctionType(Type):
	functions = set()
	call_stack = []
	invoke_inst = None

	def __init__(self, parent, node, name, codebase):
		self.name = name
		self.node = node
		self._hash = hash((self.type_name, self.name, self.node))
		self.scope = Scope(Scope.FUNCTION, self, parent)
		self.codebase = weakref.proxy(codebase)

		args_node = self.node.ast_node.args
		self.parameters = tuple(self.node.Child(parameter) for parameter in args_node.args)
		self.defaults = tuple(self.codebase.inference(parent, self.node.Child(default_value)) for default_value in args_node.defaults)
		if hasattr(ast, 'arg'):
			self.vararg = args_node.vararg and args_node.vararg.arg
			self.kwarg = args_node.kwarg and args_node.kwarg.arg
			self.param_map = {parameter.arg if isinstance(parameter, ast.arg) else '@anonymouse_parameter_%d' % i: i for i, parameter in enumerate(args_node.args)}
		else:
			self.vararg = args_node.vararg
			self.kwarg = args_node.kwarg
			self.param_map = {parameter.id if isinstance(parameter, ast.Name) else '@anonymouse_parameter_%d' % i: i for i, parameter in enumerate(args_node.args)}

		self.invocations = Scope(Scope.INVOKE, self, self.scope)
		self.result_cache = {}
		self.invoke_count = {}
		self.invoke_insts = {}
		self.functions.add(self)

	def __repr__(self):
		return '<%s of %s %s>' % (self.type_name, self.name, self.node)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.name == other.name and self.node == other.node

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return FunctionType_Type

	@staticmethod
	def parse_args(func, scope, node, param_map, defaults, need_vararg, need_kwarg, args, keywords, starargs, kwargs):
		args = args or ()
		vararg = []
		arg_index = 0
		arguments = [None] * len(param_map)
		for arg_type in args:
			if arg_index < len(arguments):
				arguments[arg_index] = arg_type
				arg_index += 1
			else:
				vararg.append(arg_type)

		if isinstance(starargs, (FixedListType, FixedTupleType)):
			for arg_type in starargs.items:
				if arg_index < len(arguments):
					arguments[arg_index] = arg_type
					arg_index += 1
				else:
					vararg.append(arg_type)

		kwarg = {}
		keywords = keywords or ()
		for arg_name in keywords:
			arg_type = keywords[arg_name]
			if arg_name in param_map:
				arg_index = param_map[arg_name]
				if arguments[arg_index] is not None:
					warn_level(3) and warnings.warn('%s get multiple values for keyword argument "%s": %s %s %s' % (func, arg_name, arguments[arg_index], arg_type, (node, args, keywords, starargs, kwargs)), RuntimeWarning)
				arguments[arg_index] = arg_type
			else:
				kwarg[StringType(arg_name)] = arg_type

		kwargs = kwargs or ()
		for kwargs_dict in kwargs:
			if isinstance(kwargs_dict, FixedDictType):
				for arg_name, arg_type in kwargs_dict.entries.items():
					if hasattr(arg_name, 'value') and arg_name.value in param_map:
						arg_index = param_map[arg_name.value]
						if arguments[arg_index] is not None:
							warn_level(3) and warnings.warn('%s get multiple values for keyword argument "%s": %s %s %s' % (func, arg_name, arguments[arg_index], arg_type, (node, args, keywords, starargs, kwargs)), RuntimeWarning)
						arguments[arg_index] = arg_type
					else:
						kwarg[arg_name] = arg_type

		if None in arguments:
			arg_type = None
			if starargs and not isinstance(starargs, (FixedListType, FixedTupleType)):
				arg_type = arg_type and UnionType(scope, node, arg_type, starargs.foreach_type(scope, node)) or starargs.foreach_type(scope, node)
			if kwargs:
				for kwargs_dict in kwargs:
					if isinstance(kwargs_dict, DictType):
						arg_type = arg_type and UnionType(scope, node, arg_type, kwargs_dict.value) or kwargs_dict.value
					elif not isinstance(kwargs_dict, FixedDictType):
						warn_level(3) and warnings.warn('%s get unexpected kwargs value: %s' % (func, (node, args, keywords, starargs, kwargs)), RuntimeWarning)

			defaults = defaults or ()
			for i in range(len(arguments)):
				if arguments[i] is None:
					default_index = i - len(arguments) + len(defaults)
					if default_index >= 0:
						arguments[i] = arg_type and UnionType(scope, node, arg_type, defaults[default_index]) or defaults[default_index]
					else:
						arguments[i] = arg_type

		if None in arguments:
			warn_level(3) and warnings.warn('%s not enough arguments: %s' % (func, (node, args, keywords, starargs, kwargs)), RuntimeWarning)
			arguments = [argument or UnknownType(node, 'missing argument', None) for argument in arguments]

		if need_vararg:
			if starargs and not isinstance(starargs, (FixedListType, FixedTupleType)):
				vararg = TupleType(UnionType(scope, node, starargs.foreach_type(scope, node), *vararg))
			else:
				vararg = FixedTupleType(scope, node, *vararg)
		else:
			vararg = None

		if need_kwarg:
			keys_type = [kwargs_dict.key for kwargs_dict in kwargs if isinstance(kwargs_dict, DictType)]
			values_type = [kwargs_dict.value for kwargs_dict in kwargs if isinstance(kwargs_dict, DictType)]
			if keys_type or values_type:
				kwarg = DictType(UnionType(scope, node, *(keys_type + list(kwarg.keys()))), UnionType(scope, node, *(values_type + list(kwarg.values()))))
			else:
				kwarg = FixedDictType(scope, node, kwarg or {})
		else:
			kwarg = None

		return tuple(arguments), vararg, kwarg

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		arguments, vararg, kwarg = self.parse_args(self, scope, node, self.param_map, self.defaults, self.vararg, self.kwarg, args, keywords, starargs, kwargs)
		if node not in self.invoke_count:
			self.invoke_count[node] = 1
		else:
			self.invoke_count[node] += 1
		if not self.invoke_inst:
			pass
		elif self.invoke_inst not in self.invoke_insts:
			self.invoke_insts[self.invoke_inst] = 1
		else:
			self.invoke_insts[self.invoke_inst] += 1
		use_cache = self in self.call_stack or self.invoke_count[node] > MAX_INVOKE_NODE * MAX_INVOKE_INST or (self.invoke_count[node] > MAX_INVOKE_NODE and (not self.invoke_inst or self.invoke_insts[self.invoke_inst] > MAX_INVOKE_INST))
		if use_cache:
			if node in self.result_cache:
				return self.result_cache[node]
			else:
				self.result_cache[node] = UnknownType(node, 'recursive invocation', None)

		self.call_stack.append(self)
		invocation = Scope(Scope.INVOKE, self, self.scope)

		for i, parameter in enumerate(self.parameters):
			self.codebase.assign(invocation, parameter, arguments[i])

		if self.vararg:
			invocation.assign(scope, node, self.vararg, vararg)

		if self.kwarg:
			invocation.assign(scope, node, self.kwarg, kwarg)

		if use_cache:
			probable_scope = Scope(Scope.PROBABLE, None, invocation)
		else:
			probable_scope = invocation

		if isinstance(self.node.ast_node, ast.Lambda):
			body_node = self.node.Child(self.node.ast_node.body)
			value_type = self.codebase.inference(probable_scope, body_node)
			if not isinstance(self.node.ast_node.body, ast.Yield):
				probable_scope.set_result(body_node, value_type, Binding.RESULT)
		else:
			for stmt in self.node.ast_node.body:
				self.codebase.inference(probable_scope, self.node.Child(stmt))

		if use_cache:
			invocation.merge(probable_scope)
		self.invocations.merge(invocation)
		self.call_stack.pop()

		if not invocation.result:
			self.result_cache[node] = NoneType
			return NoneType

		results = {binding.type for binding in invocation.result if binding.kind == Binding.RESULT}
		yields = {binding.type for binding in invocation.result if binding.kind == Binding.YIELD}

		if yields:
			result_type = GeneratorType(UnionType(scope, node, *yields))
		else:
			result_type = results and UnionType(scope, node, *results) or NoneType

		if use_cache:
			self.result_cache[node] = result_type
		return result_type

class GeneratorType(Type):
	def __init__(self, item):
		self.item = item
		self._hash = hash((self.type_name, self.item))
		assert isinstance(self.item, Type)

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.item)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.item == other.item

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return GeneratorType_Type

	def foreach_type(self, scope, node):
		return self.item

class InstanceType(Type):
	def __init__(self, node, class_type, union_instances):
		self.node = node
		self.class_type = class_type
		self.union_instances = union_instances or ()
		self._hash = id(self)
		hasattr(class_type, 'instances') and class_type.instances.add(self)
		self.scope = Scope(Scope.INSTANCE, self, class_type.scope)
		for instance_type in self.union_instances:
			assert isinstance(instance_type, InstanceType) and instance_type.class_type == self.class_type
			self.scope.merge(instance_type.scope)
		assert isinstance(self.class_type, Type)

	def get_union_instances(self):
		union_instances = {self}
		for instance_type in self.union_instances:
			union_instances |= instance_type.get_union_instances()
		return union_instances

	def __repr__(self):
		return '<%s of %s at 0x%016X>' % (self.type_name, self.class_type, self._hash)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return self is other

	def to_boolean(self, scope, node):
		nonzero_func = self.lookup_attr(scope, node, '__nonzero__', None, None, self)
		if nonzero_func:
			return nonzero_func.invoke(scope, node, [self], None, None, None).to_boolean(scope, node)
		return BooleanType(True)

	def get_type(self, scope, node):
		return self.class_type

	def foreach_type(self, scope, node):
		iter_func = self.lookup_attr(scope, node, '__iter__', None, None, self)
		if iter_func:
			iter_type = iter_func.invoke(scope, node, [self], None, None, None)
			if iter_type != self:
				return iter_type.foreach_type(scope, node)
			next_func = self.lookup_attr(scope, node, 'next', None, None, self)
			if next_func:
				return next_func.invoke(scope, node, [self], None, None, None)
		return UnknownType(node, '__iter__ not found', self)

	def get_subscript(self, scope, node, key):
		getitem_func = self.lookup_attr(scope, node, '__getitem__', None, None, self)
		if getitem_func:
			return getitem_func.invoke(scope, node, [self, key], None, None, None)
		return UnknownType(node, '__getitem__ not found', self)

	def set_subscript(self, scope, node, key, value):
		setitem_func = self.lookup_attr(scope, node, '__setitem__', None, None, self)
		if setitem_func:
			setitem_func.invoke(scope, node, [self, key, value], None, None, None)
			return self
		return UnknownType(node, '__setitem__ not found', self)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		call_func = self.lookup_attr(scope, node, '__call__', None, None, self)
		if call_func:
			return call_func.invoke(scope, node, args, keywords, starargs, kwargs)
		return UnknownType(node, '__call__ not found', self)

class IntegerType(Type):
	COERCE_NUMBER_LEVEL = 1

	def __init__(self, value):
		if NO_FIXED_TYPES: value = '?'
		if isinstance(value, PythonIntegerType):
			self.value = value
		elif isinstance(value, float):
			self.value = int(value)
			assert -0.00001 < value - self.value < 0.00001
		else:
			self.value = '?'
		self._hash = hash((self.type_name, self.value))

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.value)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.value == other.value

	def to_boolean(self, scope, node):
		if isinstance(self.value, PythonIntegerType):
			return BooleanType(bool(self.value))
		else:
			return BooleanType(self.value)

	def get_type(self, scope, node):
		return BUILTINS['int']

class ListType(Type):
	def __init__(self, item):
		self.item = item
		self.bindings = {}
		self._hash = hash((self.type_name, self.item))
		assert isinstance(self.item, Type)

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.item)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.item == other.item

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['list']

	def foreach_type(self, scope, node):
		return self.item

	def get_subscript(self, scope, node, key):
		if isinstance(key, SliceType):
			return self
		elif isinstance(key, (BooleanType, IntegerType)):
			return self.item
		elif isinstance(key, UnionType):
			return UnionType(scope, node, *[self.get_subscript(scope, node, k) for k in key.types])
		elif isinstance(key, UnknownType):
			warn_level(0) and warnings.warn('get subscript with key: %s %s %s' % (key, self, node), RuntimeWarning)
			return self.item
		return UnknownType(node, 'unsupported get subscript key: %s' % key, self)

	def set_subscript(self, scope, node, key, value):
		if isinstance(key, SliceType):
			list_type = ListType(UnionType(scope, node, self.item, value.foreach_type(scope, node)))
		elif isinstance(key, (BooleanType, IntegerType)):
			list_type = ListType(UnionType(scope, node, self.item, value))
		elif isinstance(key, UnionType):
			list_type = UnionType(scope, node, *[self.set_subscript(scope, node, k, value) for k in key.types])
		elif isinstance(key, UnknownType):
			warn_level(0) and warnings.warn('get subscript with key: %s %s %s' % (key, self, node), RuntimeWarning)
			list_type = ListType(UnionType(scope, node, self.item, value))
		else:
			return UnknownType(node, 'unsupported set subscript key: %s => %s' % (key, value), self)
		list_type.update_bindings(scope, node, self.bindings)
		return list_type

class MethodType(Type):
	def __init__(self, class_type, function_type, instance_type):
		self.class_type = class_type
		self.function_type = function_type
		self.instance_type = instance_type
		self._hash = hash((self.type_name, self.class_type, self.function_type, self.instance_type))
		self.scope = Scope(Scope.FUNCTION, self, function_type.scope)
		assert isinstance(self.class_type, Type) and isinstance(self.function_type, Type) and isinstance(self.instance_type, Type)

	def __repr__(self):
		return '<%s %s.%s of %s>' % (self.type_name, self.class_type, self.function_type, self.instance_type)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.class_type == other.class_type and self.function_type == other.function_type and self.instance_type == other.instance_type

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return MethodType_Type

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		if not args:
			args = (self.instance_type, )
		else:
			args = (self.instance_type, ) + tuple(args)
		self.function_type.invoke_inst = hash(self.instance_type)
		result_type = self.function_type.invoke(scope, node, args, keywords, starargs, kwargs)
		self.function_type.invoke_inst = None
		return result_type

class ModuleType(Type):
	def __init__(self, name, codebase, path):
		self.name = name
		self.path = path
		self._hash = hash((self.type_name, self.name, self.path))
		self.codebase = codebase and weakref.proxy(codebase)
		self.builtins = {
			'__name__': UnionType(None, None, StringType(self.name), StringType('__main__')),
		}
		if not path:
			self.scope = Scope(Scope.MODULE, self, None)

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.name)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.name == other.name and self.path == other.path

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return ModuleType_Type

	def lookup_attr(self, scope, node, name, codebase, value_node, value_type):
		if name == '__class__':
			return self.get_type(scope, node)
		elif name == '__dict__':
			if not self.scope and self.path:
				self.codebase.lazy_load(self)
			return BuiltinDictType(self)
		elif self.name == '__builtin__' and name in self.codebase.builtins:
			return self.codebase.builtins[name]
		if not self.scope and self.path:
			self.codebase.lazy_load(self)
		if self.scope:
			attr_type = self.scope.lookup_type(scope, node, name, True)
		if not attr_type and name in self.builtins:
			attr_type = self.builtins[name]
		return attr_type

class PropertyType(Type):
	def __init__(self, fget, fset, fdel, doc):
		self.fget = fget
		self.fset = fset
		self.fdel = fdel
		self.doc = doc
		self._hash = hash((self.type_name, self.fget, self.fset, self.fdel, self.doc))
		assert isinstance(self.fget, Type) and isinstance(self.fset, Type) and isinstance(self.fdel, Type) and isinstance(self.doc, Type)

	def __repr__(self):
		return '<%s of %s : %s : %s : %s>' % (self.type_name, self.fget, self.fset, self.fdel, self.doc)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.fget == other.fget and self.fset == other.fset and self.fdel == other.fdel and self.doc == other.doc

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['property']

class SetType(Type):
	def __init__(self, scope, node, *items):
		items = items and UnionType(scope, node, *items)
		if isinstance(items, UnionType):
			self.items = items.types
		elif items:
			assert isinstance(items, Type)
			self.items = {items}
		else:
			self.items = set()
		self.bindings = {}
		self._hash = hash((self.type_name, tuple(sorted(self.items))))

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.items)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.items == other.items

	def to_boolean(self, scope, node):
		return BooleanType(bool(self.items))

	def get_type(self, scope, node):
		return BUILTINS['set']

	def foreach_type(self, scope, node):
		return UnionType(scope, node, *self.items)

class SingletonType(Type):
	def __init__(self, name):
		self.name = name
		self._hash = hash((self.type_name, self.name))

	def __repr__(self):
		return self.name

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.name == other.name

	def to_boolean(self, scope, node):
		assert self is not UndefinedType
		if self is NoneType:
			return BooleanType(False)
		return BooleanType(True)

	def get_type(self, scope, node):
		assert self is not UndefinedType
		if self is NotImplementedType:
			return NotImplementedType_Type
		elif self is EllipsisType:
			return EllipsisType_Type
		elif self is NoneType:
			return NoneType_Type
		elif self.name.endswith('_Type'):
			return BUILTINS['type']
		else:
			assert False, 'unexpected singleton type'

class SliceType(Type):
	def __init__(self, lower, upper, step):
		self.lower = lower
		self.upper = upper
		self.step = step
		self._hash = hash((self.type_name, self.lower, self.upper, self.step))
		assert isinstance(self.lower, Type) and isinstance(self.upper, Type) and isinstance(self.step, Type)

	def __repr__(self):
		return '<%s of %s : %s : %s>' % (self.type_name, self.lower, self.upper, self.step)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.lower == other.lower and self.upper == other.upper and self.step == other.step

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['slice']

	@staticmethod
	def get_constant_index(value):
		if value is NoneType:
			return None
		elif isinstance(value, (BooleanType, IntegerType)) and value.value != '?':
			return int(value.value)
		else:
			return False

	def get_constant_slice(self):
		lower = self.get_constant_index(self.lower)
		upper = self.get_constant_index(self.upper)
		step = self.get_constant_index(self.step)
		if lower is False or upper is False or step is False:
			return None
		return slice(lower, upper, step)

class StringType(Type):
	def __init__(self, value):
		if NO_FIXED_TYPES: value = '?'
		if isinstance(value, PythonStringType):
			try:
				self.value = str(value)
			except UnicodeEncodeError:
				self.value = value.encode('utf-8', errors = 'ignore')
		else:
			self.value = '?'
		self._hash = hash((self.type_name, self.value))

	def __repr__(self):
		return '<%s of %r>' % (self.type_name, self.value)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.value == other.value

	def to_boolean(self, scope, node):
		if isinstance(self.value, PythonStringType):
			return BooleanType(bool(self.value))
		else:
			return BooleanType(self.value)

	def get_type(self, scope, node):
		return BUILTINS['str']

	def foreach_type(self, scope, node):
		return StringType('?')

	def get_subscript(self, scope, node, key):
		if isinstance(key, SliceType):
			constant_slice = key.get_constant_slice()
			if constant_slice and self.value != '?':
				return StringType(self.value[constant_slice])
			return StringType('?')
		elif isinstance(key, (BooleanType, IntegerType)):
			if key.value != '?' and self.value != '?':
				try:
					return StringType(self.value[key.value])
				except Exception as e:
					return UnknownType(node, 'get subscript with exception: %s %s' % (key, e), self)
			return StringType('?')
		elif isinstance(key, UnionType):
			return UnionType(scope, node, *[self.get_subscript(scope, node, k) for k in key.types])
		elif isinstance(key, UnknownType):
			warn_level(0) and warnings.warn('get subscript with key: %s %s %s' % (key, self, node), RuntimeWarning)
			return StringType('?')
		return UnknownType(node, 'unsupported get subscript key: %s' % key, self)

	def set_subscript(self, scope, node, key, value):
		warn_level(2) and warnings.warn('unsupported set subscript: %s %s' % (self, node), RuntimeWarning)
		return UndefinedType

class SuperType(Type):
	def __init__(self, class_type, instance_type):
		self.class_type = class_type
		self.instance_type = instance_type
		self._hash = hash((self.type_name, self.class_type, self.instance_type))
		if isinstance(self.instance_type, InstanceType):
			self.mro_types = self.instance_type.class_type.get_mro()
		else:
			self.mro_types = self.instance_type.get_mro()
		if self.class_type in self.mro_types:
			self.mro_types = self.mro_types[self.mro_types.index(self.class_type) + 1:]
		assert isinstance(self.class_type, Type) and isinstance(self.instance_type, Type)

	def __repr__(self):
		return '<%s of %s : %s>' % (self.type_name, self.class_type, self.instance_type)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.class_type == other.class_type and self.instance_type == other.instance_type

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['super']

	def lookup_attr(self, scope, node, name, codebase, value_node, value_type):
		if name == '__class__': return self.get_type(scope, node)
		for t in self.mro_types:
			attr_type = t.lookup_attr(scope, node, name, codebase, value_node, self.instance_type)
			if attr_type: return attr_type
		return UnknownType(node, 'super attribute "%s" not found' % name, None)

class TupleType(Type):
	def __init__(self, item):
		self.item = item
		self._hash = hash((self.type_name, self.item))
		assert isinstance(self.item, Type)

	def __repr__(self):
		return '<%s of %s>' % (self.type_name, self.item)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.item == other.item

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['tuple']

	def foreach_type(self, scope, node):
		return self.item

	def get_subscript(self, scope, node, key):
		if isinstance(key, SliceType):
			return self
		elif isinstance(key, (BooleanType, IntegerType)):
			return self.item
		elif isinstance(key, UnionType):
			return UnionType(scope, node, *[self.get_subscript(scope, node, k) for k in key.types])
		elif isinstance(key, UnknownType):
			warn_level(0) and warnings.warn('get subscript with key: %s %s %s' % (key, self, node), RuntimeWarning)
			return self.item
		return UnknownType(node, 'unsupported get subscript key: %s' % key, self)

	def set_subscript(self, scope, node, key, value):
		warn_level(2) and warnings.warn('unsupported set subscript: %s %s' % (self, node), RuntimeWarning)
		return UndefinedType

class UnionType(Type):
	def __new__(cls, scope, node, *types):
		types_set = set()
		for t in types:
			if isinstance(t, UnionType):
				for u in t.types:
					if u is not UndefinedType:
						types_set.add(u)
			elif t is not UndefinedType:
				types_set.add(t)

		set_types = set()
		unknown_types = set()
		fixed_dict_types = set()
		fixed_list_types = set()
		fixed_tuple_types = set()
		dict_types = set()
		list_types = set()
		tuple_types = set()
		instance_types = {}
		for t in types_set:
			assert isinstance(t, Type) and not isinstance(t, UnionType), types_set
			if isinstance(t, SetType):
				set_types.add(t)
			elif isinstance(t, UnknownType):
				unknown_types.add(t)
			elif isinstance(t, FixedDictType):
				fixed_dict_types.add(t)
			elif isinstance(t, FixedListType):
				fixed_list_types.add(t)
			elif isinstance(t, FixedTupleType):
				fixed_tuple_types.add(t)
			elif isinstance(t, DictType):
				dict_types.add(t)
			elif isinstance(t, ListType):
				list_types.add(t)
			elif isinstance(t, TupleType):
				tuple_types.add(t)
			elif isinstance(t, InstanceType):
				instance_types.setdefault(t.class_type, set()).add(t)

		if len(set_types) > 1:
			set_items = set()
			for set_type in set_types:
				set_items |= set_type.items
			union_set = SetType(scope, node, *set_items)
			for set_type in set_types:
				union_set.bindings.update(set_type.bindings)
			types_set -= set_types
			types_set.add(union_set)

		if len(unknown_types) > 1:
			types_set -= unknown_types
			types_set.add(UnknownType(node, 'unknown union', None))

		if len(fixed_dict_types) > 1 and not dict_types:
			entries = {}
			for t in fixed_dict_types:
				entries.update(t.entries)
			union_dict = FixedDictType(scope, node, entries)
			for t in fixed_dict_types:
				union_dict.bindings.update(t.bindings)
			types_set -= fixed_dict_types
			types_set.add(union_dict)
		elif len(fixed_dict_types) + len(dict_types) > 1:
			key_types = set()
			value_types = set()
			for t in fixed_dict_types:
				key_type = t.foreach_type(scope, node)
				key_types.add(key_type)
				value_types.add(t.get_subscript(scope, node, key_type))
			for t in dict_types:
				key_type = t.foreach_type(scope, node)
				key_types.add(key_type)
				value_types.add(t.get_subscript(scope, node, key_type))
			union_dict = DictType(UnionType(scope, node, *key_types), UnionType(scope, node, *value_types))
			for t in fixed_dict_types:
				union_dict.bindings.update(t.bindings)
			for t in dict_types:
				union_dict.bindings.update(t.bindings)
			types_set -= dict_types
			types_set -= fixed_dict_types
			types_set.add(union_dict)

		if len(fixed_list_types) > 1 and len({len(t.items) for t in fixed_list_types}) == 1 and not list_types:
			items = None
			for t in fixed_list_types:
				if items is None:
					items = [{item_type} for item_type in t.items]
					continue
				for i, item_type in enumerate(t.items):
					items[i].add(item_type)
			union_list = FixedListType(scope, node, *[UnionType(scope, node, *item_type) for item_type in items])
			for t in fixed_list_types:
				union_list.bindings.update(t.bindings)
			types_set -= fixed_list_types
			types_set.add(union_list)
		elif len(fixed_list_types) + len(list_types) > 1:
			item_types = set()
			for t in fixed_list_types:
				item_types.add(t.foreach_type(scope, node))
			for t in list_types:
				item_types.add(t.foreach_type(scope, node))
			union_list = ListType(UnionType(scope, node, *item_types))
			for t in fixed_list_types:
				union_list.bindings.update(t.bindings)
			for t in list_types:
				union_list.bindings.update(t.bindings)
			types_set -= list_types
			types_set -= fixed_list_types
			types_set.add(union_list)

		if len(fixed_tuple_types) > 1 and len({len(t.items) for t in fixed_tuple_types}) == 1 and not tuple_types:
			items = None
			for t in fixed_tuple_types:
				if items is None:
					items = [{item_type} for item_type in t.items]
					continue
				for i, item_type in enumerate(t.items):
					items[i].add(item_type)
			types_set -= fixed_tuple_types
			types_set.add(FixedTupleType(scope, node, *[UnionType(scope, node, *item_type) for item_type in items]))
		elif len(fixed_tuple_types) + len(tuple_types) > 1:
			item_types = set()
			for t in fixed_tuple_types:
				item_types.add(t.foreach_type(scope, node))
			for t in tuple_types:
				item_types.add(t.foreach_type(scope, node))
			types_set -= tuple_types
			types_set -= fixed_tuple_types
			types_set.add(TupleType(UnionType(scope, node, *item_types)))

		for class_type, union_instances in instance_types.items():
			if len(union_instances) > 1:
				types_set -= union_instances
				types_set.add(InstanceType(node, class_type, tuple(union_instances)))

		if BooleanType('?') in types_set:
			types_set = {t for t in types_set if not isinstance(t, BooleanType) or t.value == '?'}
		if ComplexType('?') in types_set:
			types_set = {t for t in types_set if not isinstance(t, ComplexType) or t.value == '?'}
		elif len([t for t in types_set if isinstance(t, ComplexType)]) > MAX_UNION_CONSTANT:
			types_set = {t for t in types_set if not isinstance(t, ComplexType)} | {ComplexType('?')}
		if FloatType('?') in types_set:
			types_set = {t for t in types_set if not isinstance(t, FloatType) or t.value == '?'}
		elif len([t for t in types_set if isinstance(t, FloatType)]) > MAX_UNION_CONSTANT:
			types_set = {t for t in types_set if not isinstance(t, FloatType)} | {FloatType('?')}
		if IntegerType('?') in types_set:
			types_set = {t for t in types_set if not isinstance(t, IntegerType) or t.value == '?'}
		elif len([t for t in types_set if isinstance(t, IntegerType)]) > MAX_UNION_CONSTANT:
			types_set = {t for t in types_set if not isinstance(t, IntegerType)} | {IntegerType('?')}
		if StringType('?') in types_set:
			types_set = {t for t in types_set if not isinstance(t, StringType) or t.value == '?'}
		elif len([t for t in types_set if isinstance(t, StringType)]) > MAX_UNION_CONSTANT:
			types_set = {t for t in types_set if not isinstance(t, StringType)} | {StringType('?')}

		if not types_set:
			return UnknownType(node, 'empty union', None)
		elif len(types_set) == 1:
			return types_set.pop()

		self = super(UnionType, UnionType).__new__(cls)
		self.types = types_set
		self._hash = hash((self.type_name, ) + tuple(self.types))

		return self

	def __repr__(self):
		return '<%s of [%s]>' % (self.type_name, ', '.join(map(repr, self.types)))

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.types == other.types

	def to_boolean(self, scope, node):
		values = {t.to_boolean(scope, node) for t in self.types}
		if values == {BooleanType(True)}:
			return BooleanType(True)
		elif values == {BooleanType(False)}:
			return BooleanType(False)
		else:
			return BooleanType('?')

	def get_type(self, scope, node):
		return UnionType(scope, node, *[t.get_type(scope, node) for t in self.types])

	def lookup_attr(self, scope, node, name, codebase, value_node, value_type):
		return UnionType(scope, node, *[t.lookup_attr(scope, node, name, codebase, value_node, value_type) or UnknownType(node, 'attribute "%s" not found' % name, None) for t in self.types])

	def foreach_type(self, scope, node):
		return UnionType(scope, node, *[t.foreach_type(scope, node) for t in self.types])

	def get_subscript(self, scope, node, key):
		return UnionType(scope, node, *[t.get_subscript(scope, node, key) for t in self.types])

	def set_subscript(self, scope, node, key, value):
		return UnionType(scope, node, *[t.set_subscript(scope, node, key, value) for t in self.types])

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		return UnionType(scope, node, *[t.invoke(scope, node, args, keywords, starargs, kwargs) for t in self.types])

class UnknownType(Type):
	def __init__(self, node, error, source):
		self.node = node
		self.error = error
		self.source = source
		self._hash = hash((self.type_name, self.node, self.error, self.source))

	def __repr__(self):
		source = repr(self.source)
		if len(source) > 100:
			source = source[:30] + ' ... ' + source[-30:]
		return '<%s "%s" of %s from %s>' % (self.type_name, self.error, self.node, source)

	def __hash__(self):
		return self._hash

	def __eq__(self, other):
		return other and self.type_name == other.type_name and self.node == other.node and self.error == other.error and self.source == other.source

	def to_boolean(self, scope, node):
		return BooleanType('?')

	def get_type(self, scope, node):
		return UnknownType(node, 'type', self)

	def foreach_type(self, scope, node):
		return UnknownType(node, 'foreach', self)

	def get_subscript(self, scope, node, key):
		return UnknownType(node, 'get subscript: %s' % key, self)

	def set_subscript(self, scope, node, key, value):
		return UnknownType(node, 'set subscript: %s => %s' % (key, value), self)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		return UnknownType(node, 'call: %s %s %s %s' % (args, keywords, starargs, kwargs), self)

UndefinedType = SingletonType('UndefinedType')

GeneratorType_Type = SingletonType('GeneratorType_Type')
FunctionType_Type = SingletonType('FunctionType_Type')
MethodType_Type = SingletonType('MethodType_Type')
ModuleType_Type = SingletonType('ModuleType_Type')

NotImplementedType = SingletonType('NotImplementedType')
EllipsisType = SingletonType('EllipsisType')
NoneType = SingletonType('NoneType')

NotImplementedType_Type = SingletonType('NotImplementedType_Type')
EllipsisType_Type = SingletonType('EllipsisType_Type')
NoneType_Type = SingletonType('NoneType_Type')

class BuiltinClassType_base(Type):
	def __repr__(self):
		return '<built-in class %s>' % self.type_name.rpartition('_')[-1]

	def __hash__(self):
		return hash(self.type_name)

	def __eq__(self, other):
		return other and self.type_name == other.type_name

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return BUILTINS['type']

class BuiltinClassType(BuiltinClassType_base):
	@property
	def type_name(self):
		return self.name

	def __init__(self, name, members):
		self.name = name
		self.builtins = members

class BuiltinClassType_bool(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['x'])}
	defaults = (BooleanType(0), )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(x_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		return x_type.to_boolean(scope, node)

class BuiltinClassType_int(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['x', 'base'])}
	defaults = (IntegerType(0), NoneType)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(x_type, base_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if base_type is NoneType and isinstance(x_type, (BooleanType, IntegerType, FloatType)) and x_type.value != '?':
			return IntegerType(int(x_type.value))
		elif isinstance(base_type, (BooleanType, IntegerType)) and base_type.value != '?' and isinstance(x_type, StringType) and x_type.value != '?':
			try:
				return IntegerType(int(x_type.value, base_type.value))
			except Exception as e:
				return UnknownType(node, 'int with exception: %s' % e, x_type)
		return IntegerType('?')

class BuiltinClassType_long(BuiltinClassType_int): pass

class BuiltinClassType_float(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['x'])}
	defaults = (IntegerType(0), )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(x_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(x_type, (BooleanType, IntegerType, FloatType)) and x_type.value != '?':
			return FloatType(float(x_type.value))
		return FloatType('?')

class BuiltinClassType_complex(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['real', 'imag'])}
	defaults = (IntegerType(0), NoneType)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(real_type, imag_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(real_type, (BooleanType, IntegerType, FloatType, ComplexType, StringType)) and real_type.value != '?':
			if imag_type is None:
				return ComplexType(complex(real_type.value))
			elif isinstance(imag_type, (BooleanType, IntegerType, FloatType)) and imag_type.value != '?':
				return ComplexType(complex(real_type.value, imag_type.value))
		return ComplexType('?')

class BuiltinClassType_str(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['object'])}
	defaults = (StringType(''), )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(object_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(object_type, (BooleanType, IntegerType, FloatType, ComplexType, StringType)) and object_type.value != '?':
			return StringType(str(object_type.value))
		return StringType('?')

class BuiltinClassType_unicode(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['string', 'encoding', 'errors'])}
	defaults = (StringType(''), NoneType, NoneType)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(string_type, encoding_type, errors_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(string_type, (BooleanType, IntegerType, FloatType, ComplexType, StringType)) and string_type.value != '?':
			return StringType(str(string_type.value))
		return StringType('?')

class BuiltinClassType_set(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['sequence'])}
	defaults = (FixedListType(None, None), )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(sequence_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(sequence_type, SetType):
			return sequence_type
		elif isinstance(sequence_type, (FixedListType, FixedTupleType)):
			return SetType(scope, node, *sequence_type.items)
		elif isinstance(sequence_type, FixedDictType):
			return SetType(scope, node, *sequence_type.entries.keys())
		else:
			return SetType(scope, node, sequence_type.foreach_type(scope, node))

class BuiltinClassType_dict(BuiltinClassType_base):
	param_map = {str(i): i for i in range(1)}
	defaults = (NoneType, )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(arg_type, ), _, kwarg = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, True, args, keywords, starargs, kwargs)
		if arg_type is NoneType:
			return kwarg
		elif isinstance(arg_type, FixedDictType) and isinstance(kwarg, FixedDictType):
			entries = {k: v for k, v in arg_type.entries.items()}
			entries.update(kwarg.entries)
			return FixedDictType(scope, node, entries)
		elif isinstance(arg_type, (FixedListType, FixedTupleType)) and isinstance(kwarg, FixedDictType):
			entries = {}
			for item_type in arg_type.items:
				if not isinstance(item_type, (FixedListType, FixedTupleType)) or len(item_type.items) != 2:
					break
				elif item_type.items[0] is not NoneType and (not isinstance(item_type.items[0], (BooleanType, ComplexType, FloatType, IntegerType, StringType)) or item_type.items[0].value == '?'):
					break
				entries[item_type.items[0]] = item_type.items[1]
			else:
				entries.update(kwarg.entries)
				return FixedDictType(scope, node, entries)

		arg_key_type = arg_type.foreach_type(scope, node)
		arg_value_type = arg_type.get_subscript(scope, node, arg_key_type)
		if isinstance(arg_value_type, UnknownType) and arg_value_type.error == 'unsupported get subscript':
			if isinstance(arg_key_type, (FixedListType, FixedTupleType)) and len(arg_key_type.items) == 2:
				arg_key_type, arg_value_type = arg_key_type.items
			elif isinstance(arg_key_type, UnionType) and not {t for t in arg_key_type.types if not isinstance(t, (FixedListType, FixedTupleType)) or len(t.items) != 2}:
				arg_value_type = UnionType(scope, node, *{t.items[1] for t in arg_key_type.types})
				arg_key_type = UnionType(scope, node, *{t.items[0] for t in arg_key_type.types})
			else:
				arg_key_type = arg_value_type = arg_key_type.foreach_type(scope, node);

		kwarg_key_type = kwarg.foreach_type(scope, node)
		kwarg_value_type = kwarg.get_subscript(scope, node, kwarg_key_type)
		return DictType(UnionType(scope, node, arg_key_type, kwarg_key_type), UnionType(scope, node, arg_value_type, kwarg_value_type))

class BuiltinClassType_list(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['sequence'])}
	defaults = (FixedListType(None, None), )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(sequence_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(sequence_type, (FixedListType, ListType)):
			return sequence_type
		elif isinstance(sequence_type, FixedTupleType):
			return FixedListType(scope, node, *sequence_type.items)
		else:
			return ListType(sequence_type.foreach_type(scope, node))

class BuiltinClassType_tuple(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['sequence'])}
	defaults = (FixedTupleType(None, None), )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(sequence_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(sequence_type, (FixedTupleType, TupleType)):
			return sequence_type
		elif isinstance(sequence_type, FixedListType):
			return FixedTupleType(scope, node, *sequence_type.items)
		else:
			return TupleType(sequence_type.foreach_type(scope, node))

class BuiltinClassType_slice(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['start', 'stop', 'step'])}
	defaults = (NoneType, NoneType, NoneType)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(start_type, stop_type, step_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		return SliceType(start_type, stop_type, step_type)

class BuiltinClassType_super(BuiltinClassType_base):
	param_map = {str(i): i for i in range(2)}
	defaults = (NoneType, NoneType)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(class_type, instance_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if class_type is NoneType and instance_type is NoneType and isinstance(scope.type, FunctionType):
			self_name = {i: n for n, i in scope.type.param_map.items() if i == 0}.pop(0, None)
			if self_name:
				instance_type = scope.lookup_type(scope, node, self_name, False)
				class_type = instance_type.get_type(scope, node)
		elif instance_type is NoneType:
			instance_type = class_type
		return SuperType(class_type, instance_type)

class BuiltinClassType_property(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['fget', 'fset', 'fdel', 'doc'])}
	defaults = (NoneType, NoneType, NoneType, NoneType)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(fget_type, fset_type, fdel_type, doc_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		return PropertyType(fget_type, fset_type, fdel_type, doc_type)

class BuiltinClassType_type(BuiltinClassType_base):
	param_map = {p: i for i, p in enumerate(['name', 'bases', 'dict'])}
	defaults = (NoneType, NoneType, NoneType)

	def __init__(self, members):
		self.builtins = members

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(name_type, bases_type, dict_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if bases_type is NoneType and dict_type is NoneType:
			return name_type.get_type(scope, node)

		if isinstance(name_type, StringType) and name_type.value != '?':
			class_name = name_type.value
		else:
			class_name = '?'

		if isinstance(bases_type, (FixedListType, FixedTupleType)):
			class_bases = bases_type.items
		else:
			class_bases = (bases_type.foreach_type(scope, node), )

		class_type = ClassType(scope, node, class_name, class_bases, None)
		if isinstance(dict_type, FixedDictType):
			for key_type, value_type in dict_type.entries.items():
				if isinstance(key_type, StringType) and key_type.value != '?':
					class_type.scope.assign(scope, node, key_type.value, value_type)

		return class_type

class BuiltinFunctionType_base(Type):
	def __repr__(self):
		return '<built-in function %s>' % self.type_name.rpartition('_')[-1]

	def __hash__(self):
		return hash(self.type_name)

	def __eq__(self, other):
		return other and self.type_name == other.type_name

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return FunctionType_Type

class BuiltinFunctionType(BuiltinFunctionType_base):
	@property
	def type_name(self):
		return self.name

	def __init__(self, name, result):
		self.name = name
		self.result = result

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		return self.result

class BuiltinFunctionType_repr(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(object_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(object_type, (BooleanType, IntegerType, FloatType, ComplexType, StringType)) and object_type.value != '?':
			return StringType(repr(object_type.value))
		return StringType('?')

class BuiltinFunctionType_staticmethod(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(method_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		method_type.is_static_method = True
		return method_type

class BuiltinFunctionType_classmethod(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(method_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		method_type.is_class_method = True
		return method_type

class BuiltinFunctionType_globals(BuiltinFunctionType_base):
	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		return BuiltinDictType(scope.module_scope.type)

class BuiltinFunctionType_chr(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(integer_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(integer_type, (BooleanType, IntegerType)) and integer_type.value != '?':
			try:
				return StringType(chr(integer_type.value))
			except Exception as e:
				return UnknownType(node, 'chr with exception: %s' % e, integer_type)
		return StringType('?')

class BuiltinFunctionType_ord(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(string_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(string_type, StringType) and string_type.value != '?' and len(string_type.value) == 1:
			try:
				return IntegerType(ord(string_type.value))
			except Exception as e:
				return UnknownType(node, 'ord with exception: %s' % e, integer_type)
		return IntegerType('?')

class BuiltinFunctionType_map(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(function_type, sequence_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return ListType(function_type.invoke(scope, node, [sequence_type.foreach_type(scope, node)], None, None, None))

class BuiltinFunctionType_filter(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(function_type, sequence_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return ListType(sequence_type.foreach_type(scope, node))

class BuiltinFunctionType_range(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(3)}
	defaults = (NoneType, NoneType, NoneType)

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(start_type, stop_type, step_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		start = SliceType.get_constant_index(start_type)
		stop = SliceType.get_constant_index(stop_type)
		step = SliceType.get_constant_index(step_type)
		if start is None or start is False or stop is False or step is False:
			return ListType(IntegerType('?'))
		elif stop is None and step is None:
			if start < MAX_FIXED_SEQUENCE:
				return FixedListType(scope, node, *[IntegerType(i) for i in range(start)])
			else:
				return ListType(IntegerType('?'))
		elif step is None:
			if stop - start < MAX_FIXED_SEQUENCE:
				return FixedListType(scope, node, *[IntegerType(i) for i in range(start, stop)])
			else:
				return ListType(IntegerType('?'))
		elif step == 0:
			return UnknownType(node, 'range() step argument must not be zero', None)
		elif (stop - start) / step <= 0:
			return FixedListType(scope, node)
		elif (stop - start) / step < MAX_FIXED_SEQUENCE:
			return FixedListType(scope, node, *[IntegerType(i) for i in range(start, stop, step)])
		else:
			return ListType(IntegerType('?'))

class BuiltinFunctionType_enumerate(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(sequence_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(sequence_type, FixedDictType):
			return FixedListType(scope, node, *[FixedTupleType(scope, node, IntegerType(i), key_type) for i, key_type in enumerate(sequence_type.entries)])
		elif isinstance(sequence_type, (FixedListType, FixedTupleType)):
			return FixedListType(scope, node, *[FixedTupleType(scope, node, IntegerType(i), item_type) for i, item_type in enumerate(sequence_type.items)])
		return ListType(FixedTupleType(scope, node, IntegerType('?'), sequence_type.foreach_type(scope, node)))

class BuiltinFunctionType_len(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(object_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(object_type, FixedDictType):
			return IntegerType(len(object_type.entries))
		elif isinstance(object_type, (FixedListType, FixedTupleType)):
			return IntegerType(len(object_type.items))
		return IntegerType('?')

class BuiltinFunctionType_round(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(object_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(object_type, (BooleanType, IntegerType, FloatType)) and object_type.value != '?':
			return FloatType(round(object_type.value))
		return FloatType('?')

class BuiltinFunctionType_type_static_new(BuiltinFunctionType_base):
	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		args = args or ()
		if len(args) > 0:
			metaclass = args[0]
			args = args[1:]
		elif isinstance(starargs, (FixedListType, FixedTupleType)) and len(starargs.items) > 0:
			metaclass = starargs.items[0]
			starargs = starargs.__class__(*starargs.items[1:])
		else:
			return UnknownType(node, 'undetermined metaclass from starargs: %s' % starargs, None)
		class_type = metaclass.invoke(scope, node, args, keywords, starargs, kwargs)
		return class_type

class BuiltinFunctionType_type_new(BuiltinFunctionType_base):
	param_map = {str(i): i for i in range(4)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(metaclass, name_type, bases_type, dict_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if bases_type is NoneType and dict_type is NoneType:
			return name_type.get_type(scope, node)

		if isinstance(name_type, StringType) and name_type.value != '?':
			class_name = name_type.value
		else:
			class_name = '?'

		if isinstance(bases_type, (FixedListType, FixedTupleType)):
			class_bases = bases_type.items
		else:
			class_bases = (bases_type.foreach_type(scope, node), )

		class_type = ClassType(scope, node, class_name, class_bases, metaclass)
		if isinstance(dict_type, FixedDictType):
			for key_type, value_type in dict_type.entries.items():
				if isinstance(key_type, StringType) and key_type.value != '?':
					class_type.scope.assign(scope, node, key_type.value, value_type)

		return class_type

class BuiltinMethodType_base(Type):
	def __repr__(self):
		return '<built-in method %s.%s>' % tuple(self.type_name.split('_')[-2:])

	def __hash__(self):
		return hash(self.type_name)

	def __eq__(self, other):
		return other and self.type_name == other.type_name

	def to_boolean(self, scope, node):
		return BooleanType(True)

	def get_type(self, scope, node):
		return MethodType_Type

class BuiltinMethodType_builtindict_items(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		items = []
		for name in self_type.binding_type.scope.bindings:
			value_type = self_type.binding_type.scope.lookup_type(scope, node, name, not isinstance(self_type.binding_type, InstanceType))
			items.append(FixedTupleType(scope, node, StringType(name), value_type))
		return FixedTupleType(scope, node, *items)

class BuiltinMethodType_builtindict_keys(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return FixedTupleType(scope, node, *[StringType(name) for name in self_type.binding_type.scope.bindings])

class BuiltinMethodType_builtindict_values(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		values = []
		for name in self_type.binding_type.scope.bindings:
			values.append(self_type.binding_type.scope.lookup_type(scope, node, name, not isinstance(self_type.binding_type, InstanceType)))
		return FixedTupleType(scope, node, *values)

class BuiltinMethodType_builtindict_get(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(3)}
	defaults = (NoneType, )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, key_type, default_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		if isinstance(key_type, StringType) and key_type.value != '?':
			return self_type.binding_type.scope.lookup_type(scope, node, key_type.value, not isinstance(self_type.binding_type, InstanceType)) or default_type
		else:
			return UnknownType(node, 'undetermined key string of %s' % key_type, None)

class BuiltinMethodType_fixeddict_items(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(fixeddict_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return FixedTupleType(scope, node, *[FixedTupleType(scope, node, k, v) for k, v in fixeddict_type.entries.items()])

class BuiltinMethodType_fixeddict_keys(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(fixeddict_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return FixedTupleType(scope, node, *fixeddict_type.entries.keys())

class BuiltinMethodType_fixeddict_values(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(fixeddict_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return FixedTupleType(scope, node, *fixeddict_type.entries.values())

class BuiltinMethodType_fixeddict_setdefault(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(3)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, key_type, value_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if key_type is not NoneType and (not isinstance(key_type, (BooleanType, ComplexType, FloatType, IntegerType, StringType)) or key_type.value == '?'):
			dict_type = DictType(UnionType(scope, node, key_type, *self_type.entries.keys()), UnionType(scope, node, value_type, *self_type.entries.values()))
		else:
			entries = {key_type: value_type}
			entries.update(self_type.entries)
			dict_type = FixedDictType(scope, node, entries)
		dict_type.update_bindings(scope, node, self_type.bindings)
		return dict_type.get_subscript(scope, node, key_type)

class BuiltinMethodType_fixeddict_update(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, other_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(other_type, FixedDictType):
			entries = {k: v for k, v in self_type.entries.items()}
			entries.update(other_type.entries)
			dict_type = FixedDictType(scope, node, entries)
		elif isinstance(other_type, DictType):
			dict_type = DictType(UnionType(scope, node, other_type.key, *self_type.entries.keys()), UnionType(scope, node, other_type.value, *self_type.entries.values()))
		else:
			key_type = other_type.foreach_type(scope, node)
			value_type = other_type.get_subscript(scope, node, key_type)
			dict_type = DictType(UnionType(scope, node, key_type, *self_type.entries.keys()), UnionType(scope, node, value_type, *self_type.entries.values()))
		dict_type.update_bindings(scope, node, self_type.bindings)
		return NoneType

class BuiltinMethodType_dict_items(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(dict_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return TupleType(TupleType(UnionType(scope, node, dict_type.key, dict_type.value)))

class BuiltinMethodType_dict_keys(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(dict_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return TupleType(dict_type.key)

class BuiltinMethodType_dict_values(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(dict_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return TupleType(dict_type.value)

class BuiltinMethodType_dict_setdefault(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(3)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, key_type, value_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		dict_type = DictType(UnionType(scope, node, key_type, self_type.key), UnionType(scope, node, value_type, self_type.value))
		dict_type.update_bindings(scope, node, self_type.bindings)
		return dict_type.get_subscript(scope, node, key_type)

class BuiltinMethodType_dict_update(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, other_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(other_type, FixedDictType):
			dict_type = DictType(UnionType(scope, node, self_type.key, *other_type.entries.keys()), UnionType(scope, node, self_type.value, *other_type.entries.values()))
		elif isinstance(other_type, DictType):
			dict_type = DictType(UnionType(scope, node, self_type.key, other_type.key), UnionType(scope, node, self_type.value, other_type.value))
		else:
			key_type = other_type.foreach_type(scope, node)
			value_type = other_type.get_subscript(scope, node, key_type)
			dict_type = DictType(UnionType(scope, node, self_type.key, key_type), UnionType(scope, node, self_type.value, value_type))
		dict_type.update_bindings(scope, node, self_type.bindings)
		return NoneType

class BuiltinMethodType_dict_get(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(3)}
	defaults = (NoneType, )

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, key_type, default_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, self.defaults, False, False, args, keywords, starargs, kwargs)
		value_type = self_type.get_subscript(scope, node, key_type)
		if isinstance(value_type, UnknownType):
			value_type = default_type
		return value_type

class BuiltinMethodType_property_set(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(property_type, fset_type), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		return PropertyType(property_type.fget, fset_type, property_type.fdel, property_type.doc)

class BuiltinMethodType_object_new(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(1)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(class_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(class_type, (ClassType, FixedClassType)):
			return InstanceType(node, class_type, None)
		else:
			return UnknownType(node, 'unsupported __new__ of %s' % class_type, None)

class BuiltinMethodType_fixedlist_append(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, item_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		fixedlist_type = FixedListType(scope, node, *(self_type.items + (item_type, )))
		fixedlist_type.update_bindings(scope, node, self_type.bindings)
		return NoneType

class BuiltinMethodType_fixedlist_insert(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(3)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, index_type, item_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		if isinstance(index_type, (BooleanType, IntegerType)) and index_type.value != '?':
			list_type = FixedListType(scope, node, *(self_type.items[:index_type.value] + (item_type, ) + self_type.items[index_type.value + 1:]))
		else:
			list_type = ListType(UnionType(scope, node, item_type, *self_type.items))
		list_type.update_bindings(scope, node, self_type.bindings)
		return NoneType

class BuiltinMethodType_list_append(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, item_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		list_type = ListType(UnionType(scope, node, self_type.item, item_type))
		list_type.update_bindings(scope, node, self_type.bindings)
		return NoneType

class BuiltinMethodType_list_insert(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(3)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, index_type, item_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		list_type = ListType(UnionType(scope, node, self_type.item, item_type))
		list_type.update_bindings(scope, node, self_type.bindings)
		return NoneType

class BuiltinMethodType_set_add(BuiltinMethodType_base):
	param_map = {str(i): i for i in range(2)}

	def invoke(self, scope, node, args, keywords, starargs, kwargs):
		(self_type, item_type, ), _, _ = FunctionType.parse_args(self, scope, node, self.param_map, (), False, False, args, keywords, starargs, kwargs)
		set_type = SetType(scope, node, item_type, *self_type.items)
		set_type.update_bindings(scope, node, self_type.bindings)
		return NoneType

BuiltinDictType.builtins = {
	'items': BuiltinMethodType_builtindict_items(),
	'keys': BuiltinMethodType_builtindict_keys(),
	'values': BuiltinMethodType_builtindict_values(),
	'iteritems': BuiltinMethodType_builtindict_items(),
	'iterkeys': BuiltinMethodType_builtindict_keys(),
	'itervalues': BuiltinMethodType_builtindict_values(),
	'get': BuiltinMethodType_builtindict_get(),
}

FixedDictType.builtins = {
	'items': BuiltinMethodType_fixeddict_items(),
	'keys': BuiltinMethodType_fixeddict_keys(),
	'values': BuiltinMethodType_fixeddict_values(),
	'iteritems': BuiltinMethodType_fixeddict_items(),
	'iterkeys': BuiltinMethodType_fixeddict_keys(),
	'itervalues': BuiltinMethodType_fixeddict_values(),
	'setdefault': BuiltinMethodType_fixeddict_setdefault(),
	'update': BuiltinMethodType_fixeddict_update(),
	'get': BuiltinMethodType_dict_get(),
}

DictType.builtins = {
	'items': BuiltinMethodType_dict_items(),
	'keys': BuiltinMethodType_dict_keys(),
	'values': BuiltinMethodType_dict_values(),
	'iteritems': BuiltinMethodType_dict_items(),
	'iterkeys': BuiltinMethodType_dict_keys(),
	'itervalues': BuiltinMethodType_dict_values(),
	'setdefault': BuiltinMethodType_dict_setdefault(),
	'update': BuiltinMethodType_dict_update(),
	'get': BuiltinMethodType_dict_get(),
}

FixedListType.builtins = {
	'append': BuiltinMethodType_fixedlist_append(),
	'insert': BuiltinMethodType_fixedlist_insert(),
}

ListType.builtins = {
	'append': BuiltinMethodType_list_append(),
	'insert': BuiltinMethodType_list_insert(),
}

SetType.builtins = {
	'add': BuiltinMethodType_set_add(),
}

PropertyType.builtins = {
	'setter': BuiltinMethodType_property_set(),
}

StringType.builtins = {
	'split': BuiltinFunctionType('split', ListType(StringType('?'))),
}

MATH_MODULE = ModuleType('math', None, None)
MATH_MODULE.builtins = {
	'pi': FloatType(3.141592653589793),
	'e': FloatType(2.718281828459045),
	'ceil':  BuiltinFunctionType('ceil', IntegerType('?')),
	'floor': BuiltinFunctionType('floor', IntegerType('?')),
	'exp': BuiltinFunctionType('exp', FloatType('?')),
	'log': BuiltinFunctionType('log', FloatType('?')),
	'pow': BuiltinFunctionType('pow', FloatType('?')),
	'sqrt': BuiltinFunctionType('sqrt', FloatType('?')),
	'acos': BuiltinFunctionType('acos', FloatType('?')),
	'asin': BuiltinFunctionType('asin', FloatType('?')),
	'atan': BuiltinFunctionType('atan', FloatType('?')),
	'atan2': BuiltinFunctionType('atan2', FloatType('?')),
	'cos': BuiltinFunctionType('cos', FloatType('?')),
	'sin': BuiltinFunctionType('sin', FloatType('?')),
	'tan': BuiltinFunctionType('tan', FloatType('?')),
	'degrees': BuiltinFunctionType('degrees', FloatType('?')),
	'radians': BuiltinFunctionType('radians', FloatType('?')),
}

RE_MATCH_TYPE = FixedClassType('Match', None, {
	'group': FixedFunctionType('group', None, ('index', ), None, None, None, StringType('?')),
	'groups': FixedFunctionType('groups', None, None, None, None, None, TupleType(StringType('?'))),
})

RE_PATTERN_TYPE = FixedClassType('Pattern', None, {
	'match': FixedFunctionType('match', None, ('string', ), None, None, None, UnionType(None, None, NoneType, InstanceType(None, RE_MATCH_TYPE, None))),
	'fullmatch': FixedFunctionType('fullmatch', None, ('string', ), None, None, None, UnionType(None, None, NoneType, InstanceType(None, RE_MATCH_TYPE, None))),
	'search': FixedFunctionType('search', None, ('string', ), None, None, None, UnionType(None, None, NoneType, InstanceType(None, RE_MATCH_TYPE, None))),
	'sub': FixedFunctionType('sub', None, ('repl', 'string', 'count'), (0, ), None, None, StringType('?')),
	'subn': FixedFunctionType('subn', None, ('repl', 'string', 'count'), (0, ), None, None, StringType('?')),
	'split': FixedFunctionType('split', None, ('pattern', 'string', 'maxsplit', 'flags'), (0, 0), None, None, ListType(StringType('?'))),
	'findall': FixedFunctionType('findall', None, ('string', ), None, None, None, ListType(StringType('?'))),
	'finditer': FixedFunctionType('finditer', None, ('string', ), None, None, None, ListType(InstanceType(None, RE_MATCH_TYPE, None))),
})

RE_MODULE = ModuleType('re', None, None)
RE_MODULE.builtins = {
	'match': FixedFunctionType('match', None, ('pattern', 'string', 'flags'), (0, ), None, None, UnionType(None, None, NoneType, InstanceType(None, RE_MATCH_TYPE, None))),
	'fullmatch': FixedFunctionType('fullmatch', None, ('pattern', 'string', 'flags'), (0, ), None, None, UnionType(None, None, NoneType, InstanceType(None, RE_MATCH_TYPE, None))),
	'search': FixedFunctionType('search', None, ('pattern', 'string', 'flags'), (0, ), None, None, UnionType(None, None, NoneType, InstanceType(None, RE_MATCH_TYPE, None))),
	'sub': FixedFunctionType('sub', None, ('pattern', 'repl', 'string', 'count', 'flags'), (0, 0), None, None, StringType('?')),
	'subn': FixedFunctionType('subn', None, ('pattern', 'repl', 'string', 'count', 'flags'), (0, 0), None, None, StringType('?')),
	'split': FixedFunctionType('split', None, ('pattern', 'string', 'maxsplit', 'flags'), (0, 0), None, None, ListType(StringType('?'))),
	'findall': FixedFunctionType('findall', None, ('pattern', 'string', 'flags'), (0, ), None, None, ListType(StringType('?'))),
	'finditer': FixedFunctionType('finditer', None, ('pattern', 'string', 'flags'), (0, ), None, None, ListType(InstanceType(None, RE_MATCH_TYPE, None))),
	'compile': FixedFunctionType('compile', None, ('pattern', 'flags'), (0, ), None, None, InstanceType(None, RE_PATTERN_TYPE, None)),
}

MODULES = {
	'math': MATH_MODULE,
	're': RE_MODULE,
}

BUILTINS = {
	'int': BuiltinClassType_int(),
	'long': BuiltinClassType_long(),
	'bool': BuiltinClassType_bool(),
	'float': BuiltinClassType_float(),
	'complex': BuiltinClassType_complex(),
	'str': BuiltinClassType_str(),
	'unicode': BuiltinClassType_unicode(),
	'set': BuiltinClassType_set(),
	'dict': BuiltinClassType_dict(),
	'list': BuiltinClassType_list(),
	'tuple': BuiltinClassType_tuple(),
	'slice': BuiltinClassType_slice(),
	'super': BuiltinClassType_super(),
	'property': BuiltinClassType_property(),
	'repr': BuiltinFunctionType_repr(),
	'staticmethod': BuiltinFunctionType_staticmethod(),
	'classmethod': BuiltinFunctionType_classmethod(),
	'globals': BuiltinFunctionType_globals(),
	'chr': BuiltinFunctionType_chr(),
	'ord': BuiltinFunctionType_ord(),
	'map': BuiltinFunctionType_map(),
	'filter': BuiltinFunctionType_filter(),
	'range': BuiltinFunctionType_range(),
	'xrange': BuiltinFunctionType_range(),
	'enumerate': BuiltinFunctionType_enumerate(),
	'len': BuiltinFunctionType_len(),
	'round': BuiltinFunctionType_round(),
	'type': BuiltinClassType_type({
		'__new__': BuiltinFunctionType_type_new(),
	}),
	'object': FixedClassType('object', object, {
		'__new__': BuiltinMethodType_object_new(),
	}),
	'file': BuiltinClassType('file', {
		'read': BuiltinFunctionType('read', StringType('?')),
		'write': BuiltinFunctionType('write', NoneType),
		'readline': BuiltinFunctionType('readline', StringType('?')),
	}),
	'_io.TextIOWrapper': BuiltinClassType('file', {
		'read': BuiltinFunctionType('read', StringType('?')),
		'write': BuiltinFunctionType('write', NoneType),
		'readline': BuiltinFunctionType('readline', StringType('?')),
	}),
	'sys.flags': BuiltinClassType('sys.flags', {
		'bytes_warning': IntegerType('?'),
		'debug': IntegerType('?'),
		'division_new': IntegerType('?'),
		'division_warning': IntegerType('?'),
		'dont_write_bytecode': IntegerType('?'),
		'hash_randomization': IntegerType('?'),
		'ignore_environment': IntegerType('?'),
		'inspect': IntegerType('?'),
		'interactive': IntegerType('?'),
		'n_fields': IntegerType('?'),
		'n_sequence_fields': IntegerType('?'),
		'n_unnamed_fields': IntegerType('?'),
		'no_site': IntegerType('?'),
		'no_user_site': IntegerType('?'),
		'optimize': IntegerType('?'),
		'py3k_warning': IntegerType('?'),
		'tabcheck': IntegerType('?'),
		'unicode': IntegerType('?'),
		'verbose': IntegerType('?'),
	}),
	'sys.float_info': BuiltinClassType('sys.float_info', {
		'max': FloatType('?'),
		'max_exp': IntegerType('?'),
		'max_10_exp': IntegerType('?'),
		'min': FloatType('?'),
		'min_exp': IntegerType('?'),
		'min_10_exp': IntegerType('?'),
		'dig': IntegerType('?'),
		'mant_dig': IntegerType('?'),
		'epsilon': FloatType('?'),
		'radix': IntegerType('?'),
		'rounds': IntegerType('?'),
	}),
	'sys.long_info': BuiltinClassType('sys.long_info', {
		'bits_per_digit': IntegerType('?'),
		'sizeof_digit': IntegerType('?'),
	}),
	'sys.version_info': BuiltinClassType('sys.version_info', {
		'major': IntegerType('?'),
		'minor': IntegerType('?'),
		'micro': IntegerType('?'),
		'releaselevel': StringType('?'),
		'serial': IntegerType('?'),
	}),
}

class CodeBase(object):
	SUFFIX = '.py'

	def __init__(self, source_paths):
		self.callable_functions = set()
		self.source_paths = source_paths# + sys.path
		self.project_path = None
		self.import_stack = []
		self.import_error = set()

		self.builtins = {}
		self.builtins.update(BUILTINS)

		self.modules = {
			'__builtin__': ModuleType('__builtin__', self, None),
			'__main__': ModuleType('__main__', self, None),
		}
		self.modules.update(MODULES)

		try:
			import builtins
			self.modules.update(builtins.modules)
			self.builtins.update(builtins.objects)
		except:
			pass

	def load(self, path):
		if os.path.isfile(path):
			self.project_path = os.path.dirname(path)
			self._load(path)
		else:
			self.project_path = path
			for p, ds, fs in os.walk(path):
				for f in fs:
					self._load(os.path.join(p, f))

		for function in FunctionType.functions:
			if function.name not in SHOW_FUNCTION_INVOCATION: continue
			paths = SHOW_FUNCTION_INVOCATION[function.name]
			if not isinstance(paths, (list, tuple)):
				paths = (paths, )
			for path in paths:
				if path in repr(function):
					log(8, '========================================================')
					log(8, function)
					for name in function.invocations.bindings:
						log(8, '  ', name, '=>')
						for binding in function.invocations.bindings[name]:
							log(8, '    ', binding)
					if function.invocations.result:
						log(8, '  ', 'result', '=>')
						for binding in function.invocations.result:
							log(8, '    ', binding)
					break

	def _load(self, path):
		path = path.replace('\\', '/')
		if not path.endswith('.py'): return
		name = os.path.splitext(os.path.basename(path))[0]
		if path not in self.modules:
			self.modules[path] = ModuleType(name, self, path)
		self.lazy_load(self.modules[path])

	def lazy_load(self, module_type):
		if module_type.scope: return
		if module_type.path in self.import_stack:
			if module_type.path != self.import_stack[-1]:
				warn_level(2) and warnings.warn('recursively import module: %s' % module_type, RuntimeWarning)
			return

		log(9, 'lazy loading:', module_type.path)
		module_type.scope = Scope(Scope.MODULE, module_type, None)

		if module_type.path.endswith('/__init__.py'):
			package_path = os.path.dirname(module_type.path)
			for f in os.listdir(package_path):
				if f == '__init__.py': continue
				submodule_path = os.path.join(package_path, f).replace('\\', '/')
				if not os.path.isfile(submodule_path) or not submodule_path.endswith('.py'):
					continue
				name = os.path.splitext(os.path.basename(submodule_path))[0]
				if submodule_path not in self.modules:
					self.modules[submodule_path] = ModuleType(name, self, submodule_path)
				module_type.builtins[name] = self.modules[submodule_path]

		try:
			source_code = open(module_type.path, 'rU').read()
		except Exception as e:
			log(10, 'Error:', module_type, e)
			return

		try:
			module_node = compile(source_code, module_type.path, 'exec', ast.PyCF_ONLY_AST)
		except Exception as e:
			log(10, 'Error:', module_type, e)
			return

		module_root = Node.Root(source_code, module_type.name, module_type.path, module_node)
		self.import_stack.append(module_type.path)
		for stmt in module_node.body:
			self.inference(module_type.scope, module_root.Child(stmt))
		self.import_stack.pop()

		if module_type.name in SHOW_MODULE_BINDINGS:
			log(8, '********************************************************')
			log(8, module_type)
			for name in module_type.scope.bindings:
				log(8, '  ', name, '=>')
				for binding in module_type.scope.bindings[name]:
					log(8, '    ', binding)

	def resolve_module(self, level, name, node):
		filename = name.replace('.', '/') + '.py'
		package = os.path.join(name.replace('.', '/'), '__init__.py')

		if level:
			dirname = node.root.filename
			for _ in range(level):
				dirname = os.path.dirname(dirname)
			module_path = '%s/%s' % (dirname, filename)
			if os.path.isfile(module_path): return module_path
			module_path = '%s/%s' % (dirname, package)
			if os.path.isfile(module_path): return module_path

		dirname = os.path.dirname(node.root.filename)
		module_path = os.path.join(dirname, filename)
		if os.path.isfile(module_path): return module_path
		module_path = os.path.join(dirname, package)
		if os.path.isfile(module_path): return module_path
		if self.project_path:
			module_path = os.path.join(self.project_path, filename)
			if os.path.isfile(module_path): return module_path
			module_path = os.path.join(self.project_path, package)
			if os.path.isfile(module_path): return module_path
		for path in self.source_paths:
			module_path = os.path.join(path, filename)
			if os.path.isfile(module_path): return module_path
			module_path = os.path.join(path, package)
			if os.path.isfile(module_path): return module_path
		return None

	def set_type(self, path, type):
		target_type = self.modules[path[0]]
		for name in path[1:-1]:
			target_type = target_type.lookup_attr(None, None, name, self, None, None)
		target_type.scope.assign(None, None, path[-1], type)

	def invoke(self, path, args, keywords, starargs, kwargs):
		target_type = self.modules[path[0]]
		for name in path[1:]:
			target_type = target_type.lookup_attr(None, None, name, self, None, None)
		return target_type.invoke(None, None, args, keywords, starargs, kwargs)

	def lookup(self, scope, node, name, _nonlocal):
		value_type = scope and scope.lookup_type(scope, node, name, _nonlocal)
		if not value_type:
			if scope and name in scope.module_scope.type.builtins:
				value_type = scope.module_scope.type.builtins[name]
			elif name in self.builtins:
				value_type = self.builtins[name]
			elif name in __builtins__:
				value_type = self.get_python_type(scope, node, __builtins__[name])
		return value_type

	def get_python_type(self, scope, node, value):
		if value is None:
			return NoneType
		elif value is type:
			return BUILTINS['type']
		elif value is object:
			return BUILTINS['object']
		elif value is Ellipsis:
			return EllipsisType
		elif value is NotImplemented:
			return NotImplementedType
		elif isinstance(value, bool):
			return BooleanType(value)
		elif isinstance(value, complex):
			return ComplexType(value)
		elif isinstance(value, PythonDictType):
			return DictType(UnknownType(node, 'python dict key', None), UnknownType(node, 'python dict value', None))
		elif isinstance(value, float):
			return FloatType(value)
		elif isinstance(value, PythonIntegerType):
			return IntegerType(value)
		elif isinstance(value, list):
			return ListType(UnknownType(node, 'python list item', None))
		elif isinstance(value, PythonModuleType):
			if value.__name__ not in self.modules:
				self.modules[value.__name__] = ModuleType(value.__name__, self, None)
			return self.modules[value.__name__]
		elif isinstance(value, PythonStringType):
			return StringType(value)
		elif isinstance(value, tuple):
			return TupleType(UnknownType(node, 'python tuple item', None))
		elif isinstance(value, PythonClassType):
			return FixedClassType(value.__name__, value, {})
		elif isinstance(value, PythonFunctionType):
			return FixedFunctionType(value.__name__, value, None, None, None, None, UnknownType(node, 'python function result', None))
		elif isinstance(value, PythonMemberType):
			return UnknownType(node, 'python member', None)
		elif hasattr(value, '__class__'):
			class_name = repr(value.__class__)
			if class_name.startswith("<type '") and class_name.endswith("'>"):
				class_name = class_name[len("<type '"):-len("'>")]
			if class_name.startswith("<class '") and class_name.endswith("'>"):
				class_name = class_name[len("<class '"):-len("'>")]
			if class_name.startswith('<class ') and ' at 0x' in class_name and class_name.endswith('>'):
				class_name = class_name.rpartition(' at 0x')[0][len('<class '):]
			class_type = self.lookup(scope, node, class_name, True)
			if class_type:
				return InstanceType(node, class_type, None)

			class_type = self.lookup(scope, node, value.__class__.__name__, True)
			if class_type and getattr(class_type, 'cls', None) == value.__class__:
				return InstanceType(node, class_type, None)

		warn_level(2) and warnings.warn('unsupported value type: %s %s %s' % (getattr(value, '__class__', type(value)), value, node), RuntimeWarning)
		return UnknownType(node, 'unsupported python', None)

	def import_module(self, level, name, node):
		if level:
			module_name = '.'.join(node.root.module_name.split('.')[:-level])
			if module_name:
				module_name = '%s.%s' % (module_name, name)
		else:
			module_name = name

		if module_name in self.modules:
			return self.modules[module_name]

		module_path = self.resolve_module(level, name, node)
		module_path = module_path and module_path.replace('\\', '/')
		module_name = module_path or module_name or name
		if module_name in self.modules:
			return self.modules[module_name]

		if module_path:
			module_type = ModuleType(name, self, module_path)
		else:
			try:
				module_object = __import__(module_name)
			except:
				if module_name not in self.import_error:
					# traceback.print_exc()
					warn_level(2) and warnings.warn('cannot import module: %s' % module_name, RuntimeWarning)
					self.import_error.add(module_name)
				return None

			module_type = ModuleType(module_name, self, None)
			for vname in dir(module_object):
				if vname in ('__spec__', '__loader__'):
					continue
				value = getattr(module_object, vname)
				value_type = self.get_python_type(module_type.scope, node, value)
				module_type.builtins[vname] = value_type

		self.modules[module_name] = module_type
		return module_type

	def assign(self, scope, node, value):
		method = 'assign_' + node.ast_node.__class__.__name__
		assert hasattr(self, method), 'unexpected assign node: %s' % node
		return getattr(self, method)(scope, node, value)

	def assign_Call(self, scope, node, value):
		warn_level(3) and warnings.warn('unsupported assign to invocation result: %s' % node, RuntimeWarning)

	def assign_Attribute(self, scope, node, value):
		value_node = node.Child(node.ast_node.value)
		target_name = node.ast_node.attr
		target_type = self.inference(scope, value_node)

		if isinstance(target_type, UnknownType):
			warn_level(0) and warnings.warn('set attribute "%s" of %s: %s' % (target_name, target_type, node), RuntimeWarning)
			return

		attr_type = target_type.lookup_attr(scope, node, target_name, self, value_node, None)
		if isinstance(attr_type, PropertyType):
			attr_type.fset.invoke(scope, node, [target_type, value], None, None, None)
			return
		elif isinstance(attr_type, UnionType):
			for t in attr_type.types:
				if isinstance(t, PropertyType) and t.fset is not NoneType:
					t.fset.invoke(scope, node, [target_type, value], None, None, None)
					return

		if isinstance(target_type, UnionType):
			for t in target_type.types:
				if isinstance(t, UnknownType):
					warn_level(0) and warnings.warn('set attribute "%s" of %s: %s' % (target_name, t, node), RuntimeWarning)
				elif not t.scope:
					warn_level(1) and warnings.warn('unsupported set attribute "%s" of %s: %s' % (target_name, t, node), RuntimeWarning)
				else:
					t.scope.assign(scope, node, target_name, value)
		elif not target_type.scope:
			warn_level(1) and warnings.warn('unsupported set attribute "%s" of %s: %s' % (target_name, target_type, node), RuntimeWarning)
		else:
			target_type.scope.assign(scope, node, target_name, value)

	def assign_Subscript(self, scope, node, value):
		slice_type = self.inference(scope, node.Child(node.ast_node.slice))
		target_node = node.Child(node.ast_node.value)
		target_type = self.inference(scope, target_node)
		result_type = target_type.set_subscript(scope, node, slice_type, value)

	def _assign_name(self, scope, node, name, value):
		target_scope = None
		if scope.is_global(name):
			module_scope = scope.module_scope
			if module_scope and module_scope is not scope and name in module_scope.bindings:
				target_scope = module_scope
		if not target_scope and scope.is_nonlocal(name):
			target_scope = scope.parent
			while target_scope and name not in target_scope.bindings:
				target_scope = target_scope.parent
			if not target_scope:
				warn_level(1) and warnings.warn('nonlocal variable "%s" not found in %s %s' % (name, scope, node), RuntimeWarning)
		if not target_scope:
			target_scope = scope
		target_scope.assign(scope, node, name, value)

	def assign_Name(self, scope, node, value):
		self._assign_name(scope, node, node.ast_node.id, value)

	def assign_str(self, scope, node, value):
		self._assign_name(scope, node, node.ast_node, value)

	def assign_arg(self, scope, node, value):
		scope.assign(scope, node, node.ast_node.arg, value)

	def assign_List(self, scope, node, value):
		if isinstance(value, (FixedListType, FixedTupleType)):
			for i, item in enumerate(node.ast_node.elts):
				if i >= len(value.items):
					self.assign(scope, node.Child(item), UnknownType(node, 'index out of range: %s' % i, value))
				else:
					self.assign(scope, node.Child(item), value.items[i])
		else:
			for item in node.ast_node.elts:
				self.assign(scope, node.Child(item), value.foreach_type(scope, node))

	def assign_Tuple(self, scope, node, value):
		if isinstance(value, (FixedListType, FixedTupleType)):
			for i, item in enumerate(node.ast_node.elts):
				if i >= len(value.items):
					self.assign(scope, node.Child(item), UnknownType(node, 'index out of range: %s' % i, value))
				else:
					self.assign(scope, node.Child(item), value.items[i])
		else:
			for item in node.ast_node.elts:
				self.assign(scope, node.Child(item), value.foreach_type(scope, node))

	def operator(self, scope, node, *values):
		value_list = None
		for value in values:
			if isinstance(value, UnknownType):
				return UnknownType(node, 'operator: %s' % (values, ), value)
			elif isinstance(value, UnionType):
				if not value_list:
					value_list = [[t] for t in value.types]
				else:
					expand_list = []
					for vv in value_list:
						for t in value.types:
							expand_list.append(vv + [t])
					value_list = expand_list
			elif not value_list:
				value_list = [[value]]
			else:
				for vv in value_list:
					vv.append(value)

		results = set()
		for vv in value_list:
			types = tuple(t.type_name[:-4] if t.type_name.endswith('Type') else t.type_name for t in vv)
			method = 'operator_' + node.ast_node.__class__.__name__ + '_' + '_'.join(types)
			if hasattr(self, method):
				results.add(getattr(self, method)(scope, node, *vv))
				continue

			has_non_number = False
			has_unknown_value = False
			coerce_number_type = None
			for t in vv:
				if not hasattr(t, 'COERCE_NUMBER_LEVEL'):
					has_non_number = True
					break
				if t.value == '?':
					has_unknown_value = True
				if coerce_number_type is None or coerce_number_type.COERCE_NUMBER_LEVEL < t.COERCE_NUMBER_LEVEL:
					coerce_number_type = t.__class__

			if not has_non_number:
				if has_unknown_value:
					if isinstance(node.ast_node, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.Not)):
						results.add(BooleanType('?'))
					else:
						results.add(coerce_number_type('?'))
				elif isinstance(node.ast_node, ast.Add):
					results.add(coerce_number_type(vv[0].value + vv[1].value))
				elif isinstance(node.ast_node, ast.Sub):
					results.add(coerce_number_type(vv[0].value - vv[1].value))
				elif isinstance(node.ast_node, ast.Mult):
					results.add(coerce_number_type(vv[0].value * vv[1].value))
				elif isinstance(node.ast_node, ast.Div):
					try:
						results.add(coerce_number_type(vv[0].value / vv[1].value))
					except Exception as e:
						results.add(UnknownType(node, 'div with exception: %s' % e, vv[1]))
				elif isinstance(node.ast_node, ast.Mod):
					results.add(coerce_number_type(vv[0].value % vv[1].value))
				elif isinstance(node.ast_node, ast.Pow):
					if coerce_number_type is IntegerType and vv[1].value < 0:
						coerce_number_type = FloatType
					results.add(coerce_number_type(vv[0].value ** vv[1].value))
				elif isinstance(node.ast_node, ast.LShift):
					results.add(coerce_number_type(vv[0].value << vv[1].value))
				elif isinstance(node.ast_node, ast.RShift):
					results.add(coerce_number_type(vv[0].value >> vv[1].value))
				elif isinstance(node.ast_node, ast.BitOr):
					results.add(coerce_number_type(vv[0].value | vv[1].value))
				elif isinstance(node.ast_node, ast.BitXor):
					results.add(coerce_number_type(vv[0].value ^ vv[1].value))
				elif isinstance(node.ast_node, ast.BitAnd):
					results.add(coerce_number_type(vv[0].value & vv[1].value))
				elif isinstance(node.ast_node, ast.FloorDiv):
					results.add(coerce_number_type(vv[0].value // vv[1].value))
				elif isinstance(node.ast_node, ast.Invert):
					results.add(coerce_number_type(~vv[0].value))
				elif isinstance(node.ast_node, ast.Not):
					results.add(BooleanType(not vv[0].value))
				elif isinstance(node.ast_node, ast.UAdd):
					results.add(coerce_number_type(+vv[0].value))
				elif isinstance(node.ast_node, ast.USub):
					results.add(coerce_number_type(-vv[0].value))
				elif isinstance(node.ast_node, ast.Eq):
					results.add(BooleanType(vv[0].value == vv[1].value))
				elif isinstance(node.ast_node, ast.NotEq):
					results.add(BooleanType(vv[0].value != vv[1].value))
				elif isinstance(node.ast_node, ast.Lt):
					results.add(BooleanType(vv[0].value < vv[1].value))
				elif isinstance(node.ast_node, ast.LtE):
					results.add(BooleanType(vv[0].value <= vv[1].value))
				elif isinstance(node.ast_node, ast.Gt):
					results.add(BooleanType(vv[0].value > vv[1].value))
				elif isinstance(node.ast_node, ast.GtE):
					results.add(BooleanType(vv[0].value >= vv[1].value))
				elif isinstance(node.ast_node, ast.Is):
					results.add(BooleanType(vv[0].value is vv[1].value))
				elif isinstance(node.ast_node, ast.IsNot):
					results.add(BooleanType(vv[0].value is not vv[1].value))
				else:
					warn_level(1) and warnings.warn('unsupported operator: %s %s' % (node, vv), RuntimeWarning)
				continue

			if isinstance(node.ast_node, ast.Add) and isinstance(vv[0], InstanceType) and isinstance(vv[0].class_type, FixedClassType) and vv[0].class_type.name == 'bytearray':
				results.add(vv[0])
				continue

			if isinstance(node.ast_node, ast.Mod) and isinstance(vv[0], StringType):
				results.add(StringType('?'))
				continue

			if isinstance(node.ast_node, ast.Not):
				result_type = vv[0].to_boolean(scope, node)
				if result_type.value != '?':
					results.add(BooleanType(not result_type.value))
				else:
					results.add(BooleanType('?'))
				continue

			if isinstance(node.ast_node, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn)):
				results.add(BooleanType('?'))
				continue

			undefined = node, types, vv

		if not results:
			for vv in value_list:
				for value in vv:
					if isinstance(value, UnknownType):
						return UnknownType(node, 'operator: %s' % (values, ), value)
			return UnknownType(node, 'unexpected operator node %s for types: %s %s' % undefined, None)

		return UnionType(scope, node, *results)

	def operator_Sub_Set_Set(self, scope, node, value1, value2):
		return value1

	def operator_BitOr_Set_Set(self, scope, node, value1, value2):
		return SetType(scope, node, *(value1.items | value2.items))

	def operator_BitXor_Set_Set(self, scope, node, value1, value2):
		return SetType(scope, node, *(value1.items | value2.items))

	def operator_BitAnd_Set_Set(self, scope, node, value1, value2):
		return SetType(scope, node, *(value1.items & value2.items))

	def operator_Mult_String_Integer(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return StringType(value1.value * value2.value)
		return StringType('?')
	operator_Mult_Integer_String = operator_Mult_String_Integer

	def operator_Mult_FixedList_Integer(self, scope, node, value1, value2):
		if value2.value != '?' and value2.value < MAX_FIXED_SEQUENCE:
			return FixedListType(scope, node, *(value1.items * value2.value))
		else:
			return ListType(UnionType(scope, node, *value1.items))

	def operator_Mult_Integer_FixedList(self, scope, node, value1, value2):
		if value1.value != '?' and value1.value < MAX_FIXED_SEQUENCE:
			return FixedListType(scope, node, *(value1.value * value2.items))
		else:
			return ListType(UnionType(scope, node, *value2.items))

	def operator_Mult_FixedTuple_Integer(self, scope, node, value1, value2):
		if value2.value != '?' and value2.value < MAX_FIXED_SEQUENCE:
			return FixedTupleType(scope, node, *(value1.items * value2.value))
		else:
			return TupleType(UnionType(scope, node, *value1.items))

	def operator_Mult_Integer_FixedTuple(self, scope, node, value1, value2):
		if value1.value != '?' and value1.value < MAX_FIXED_SEQUENCE:
			return FixedTupleType(scope, node, *(value1.value * value2.items))
		else:
			return TupleType(UnionType(scope, node, *value2.items))

	def operator_Mult_List_Integer(self, scope, node, value1, value2):
		return value1

	def operator_Mult_Integer_List(self, scope, node, value1, value2):
		return value2

	def operator_Mult_Tuple_Integer(self, scope, node, value1, value2):
		return value1

	def operator_Mult_Integer_Tuple(self, scope, node, value1, value2):
		return value2

	def operator_Add_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return StringType(value1.value + value2.value)
		return StringType('?')

	def operator_Eq_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value == value2.value)
		return BooleanType('?')

	def operator_NotEq_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value != value2.value)
		return BooleanType('?')

	def operator_Lt_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value < value2.value)
		return BooleanType('?')

	def operator_LtE_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value <= value2.value)
		return BooleanType('?')

	def operator_Gt_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value > value2.value)
		return BooleanType('?')

	def operator_GtE_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value >= value2.value)
		return BooleanType('?')

	def operator_Is_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value is value2.value)
		return BooleanType('?')

	def operator_IsNot_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value is not value2.value)
		return BooleanType('?')

	def operator_In_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value in value2.value)
		return BooleanType('?')

	def operator_NotIn_String_String(self, scope, node, value1, value2):
		if value1.value != '?' and value2.value != '?':
			return BooleanType(value1.value not in value2.value)
		return BooleanType('?')

	def operator_Add_List_List(self, scope, node, value1, value2):
		return ListType(UnionType(scope, node, value1.item, value2.item))

	def operator_Add_List_FixedList(self, scope, node, value1, value2):
		return ListType(UnionType(scope, node, value1.item, *value2.items))

	def operator_Add_FixedList_List(self, scope, node, value1, value2):
		return ListType(UnionType(scope, node, value2.item, *value1.items))

	def operator_Add_FixedList_FixedList(self, scope, node, value1, value2):
		return FixedListType(scope, node, *(value1.items + value2.items))

	def operator_Add_Tuple_Tuple(self, scope, node, value1, value2):
		return TupleType(UnionType(scope, node, value1.item, value2.item))

	def operator_Add_Tuple_FixedTuple(self, scope, node, value1, value2):
		return TupleType(UnionType(scope, node, value1.item, *value2.items))

	def operator_Add_FixedTuple_Tuple(self, scope, node, value1, value2):
		return TupleType(UnionType(scope, node, value2.item, *value1.items))

	def operator_Add_FixedTuple_FixedTuple(self, scope, node, value1, value2):
		return FixedTupleType(scope, node, *(value1.items + value2.items))

	def is_plain_loop(self, ast_node):
		if isinstance(ast_node, (ast.Continue, ast.Break)):
			return False
		for field in ast_node._fields:
			value = getattr(ast_node, field, [])
			if isinstance(value, list):
				for item in value:
					if isinstance(item, ast.AST) and not self.is_plain_loop(item):
						return False
			elif isinstance(value, ast.AST) and not self.is_plain_loop(value):
					return False
		return True

	def inference(self, scope, node):
		method = 'inference_' + node.ast_node.__class__.__name__
		assert hasattr(self, method), 'unexpected inference node: %s' % node
		return getattr(self, method)(scope, node)

	def inference_FunctionDef(self, scope, node):
		function_type = FunctionType(scope, node, node.ast_node.name, self)
		for decorator in node.ast_node.decorator_list:
			decorator_type = self.inference(scope, node.Child(decorator))
			if isinstance(decorator_type, UnknownType): continue
			function_type = decorator_type.invoke(scope, node, [function_type], None, None, None)
		scope.assign(scope, node, node.ast_node.name, function_type)
		args_ast = node.ast_node.args
		if not args_ast.vararg and not not args_ast.vararg and len(args_ast.args) == len(args_ast.defaults):
			self.callable_functions.add(function_type)
		return function_type

	def inference_ClassDef(self, scope, node):
		bases = tuple(self.inference(scope, node.Child(base)) for base in node.ast_node.bases)
		class_type = ClassType(scope, node, node.ast_node.name, bases, None)
		for stmt in node.ast_node.body:
			self.inference(class_type.scope, node.Child(stmt))
		for decorator in node.ast_node.decorator_list:
			decorator_type = self.inference(scope, node.Child(decorator))
			if isinstance(decorator_type, UnknownType): continue
			class_type = decorator_type.invoke(scope, node, [class_type], None, None, None)
		scope.assign(scope, node, node.ast_node.name, class_type)
		return class_type

	def inference_Return(self, scope, node):
		value_type = node.ast_node.value and self.inference(scope, node.Child(node.ast_node.value)) or NoneType
		scope.set_result(node, value_type, Binding.RESULT)
		return UndefinedType

	def inference_Delete(self, scope, node):
		value_type = UnknownType(node, 'delete', None)
		for target in node.ast_node.targets:
			if isinstance(target, ast.Name):
				self.assign(scope, node.Child(target), value_type)
			elif isinstance(target, ast.Attribute):
				value_node = node.Child(target).Child(target.value)
				target_type = self.inference(scope, value_node)
				attr_type = target_type.lookup_attr(scope, node, target.attr, self, value_node, None)
				del_types = attr_type.types if isinstance(attr_type, UnionType) else {attr_type}
				for attr_type in del_types:
					if isinstance(attr_type, PropertyType) and attr_type.fdel is not NoneType:
						attr_type.fdel.invoke(scope, node, [target_type], None, None, None)
						break
				else:
					self.assign(scope, node.Child(target), value_type)
			elif isinstance(target, ast.Subscript):
				target_node = node.Child(target)
				self.inference(scope, target_node.Child(target.value))
				self.inference(scope, target_node.Child(target.slice))
			else:
				warn_level(2) and warnings.warn('unsupported delete target %s %s' % (target, node), RuntimeWarning)

		return UndefinedType

	def inference_Assign(self, scope, node):
		value_type = self.inference(scope, node.Child(node.ast_node.value))
		for target in node.ast_node.targets:
			self.assign(scope, node.Child(target), value_type)
		return UndefinedType

	def inference_AugAssign(self, scope, node):
		target_node = node.Child(node.ast_node.target)
		target_type = self.inference(scope, target_node)
		value_type = self.inference(scope, node.Child(node.ast_node.value))
		result_type = self.operator(scope, node.Child(node.ast_node.op), target_type, value_type)
		self.assign(scope, target_node, result_type)
		return UndefinedType

	def inference_Print(self, scope, node):
		node.ast_node.dest and self.inference(scope, node.Child(node.ast_node.dest))
		for value in node.ast_node.values:
			self.inference(scope, node.Child(value))
		return UndefinedType

	def inference_For(self, scope, node):
		iter_type = self.inference(scope, node.Child(node.ast_node.iter))
		can_expand = self.is_plain_loop(node.ast_node)
		if can_expand and isinstance(iter_type, FixedDictType):
			branch_scopes = []
			for key_type in iter_type.entries:
				body_scope = Scope(Scope.BRANCH, None, scope)
				branch_scopes.append(body_scope)
				self.assign(body_scope, node.Child(node.ast_node.target), key_type)
				for stmt in node.ast_node.body:
					self.inference(body_scope, node.Child(stmt))
			if node.ast_node.orelse:
				orelse_scope = Scope(Scope.BRANCH, None, scope)
				branch_scopes.append(orelse_scope)
				self.assign(orelse_scope, node.Child(node.ast_node.target), iter_type.foreach_type(scope, node))
				for stmt in node.ast_node.orelse:
					self.inference(orelse_scope, node.Child(stmt))
			scope.combine(scope, node, True, *branch_scopes)
		elif can_expand and isinstance(iter_type, (FixedListType, FixedTupleType)):
			branch_scopes = []
			for item_type in iter_type.items:
				body_scope = Scope(Scope.BRANCH, None, scope)
				branch_scopes.append(body_scope)
				self.assign(body_scope, node.Child(node.ast_node.target), item_type)
				for stmt in node.ast_node.body:
					self.inference(body_scope, node.Child(stmt))
			if node.ast_node.orelse:
				orelse_scope = Scope(Scope.BRANCH, None, scope)
				branch_scopes.append(orelse_scope)
				self.assign(orelse_scope, node.Child(node.ast_node.target), iter_type.foreach_type(scope, node))
				for stmt in node.ast_node.orelse:
					self.inference(orelse_scope, node.Child(stmt))
			scope.combine(scope, node, True, *branch_scopes)
		else:
			self.assign(scope, node.Child(node.ast_node.target), iter_type.foreach_type(scope, node))
			body_scope = Scope(Scope.PROBABLE, None, scope)
			for stmt in node.ast_node.body:
				self.inference(body_scope, node.Child(stmt))
			orelse_scope = Scope(Scope.BRANCH, None, scope)
			for stmt in node.ast_node.orelse:
				self.inference(orelse_scope, node.Child(stmt))
			scope.combine(scope, node, False, body_scope, orelse_scope)
		return UndefinedType

	def inference_While(self, scope, node):
		test_type = self.inference(scope, node.Child(node.ast_node.test)).to_boolean(scope, node)
		body_scope = Scope(Scope.PROBABLE, None, scope)
		for stmt in node.ast_node.body:
			self.inference(body_scope, node.Child(stmt))
		orelse_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.orelse:
			self.inference(orelse_scope, node.Child(stmt))
		scope.combine(scope, node, test_type is BooleanType(True), body_scope, orelse_scope)
		return UndefinedType

	def inference_If(self, scope, node):
		test_type = self.inference(scope, node.Child(node.ast_node.test)).to_boolean(scope, node)
		branch_scopes = []
		if test_type is not BooleanType(False):
			true_scope = Scope(Scope.BRANCH, None, scope)
			branch_scopes.append(true_scope)
			for stmt in node.ast_node.body:
				self.inference(true_scope, node.Child(stmt))
		if test_type is not BooleanType(True):
			false_scope = Scope(Scope.BRANCH, None, scope)
			branch_scopes.append(false_scope)
			for stmt in node.ast_node.orelse:
				self.inference(false_scope, node.Child(stmt))
		if branch_scopes:
			scope.combine(scope, node, True, *branch_scopes)
		return UndefinedType

	def inference_With(self, scope, node):
		if hasattr(node.ast_node, 'items'):
			for item in node.ast_node.items:
				value_type = self.inference(scope, node.Child(item.context_expr))
				if item.optional_vars:
					self.assign(scope, node.Child(item.optional_vars), value_type)
		else:
			value_type = self.inference(scope, node.Child(node.ast_node.context_expr))
			if node.ast_node.optional_vars:
				self.assign(scope, node.Child(node.ast_node.optional_vars), value_type)
		for stmt in node.ast_node.body:
			self.inference(scope, node.Child(stmt))
		return UndefinedType

	def inference_Raise(self, scope, node):
		getattr(node.ast_node, 'type', None) and self.inference(scope, node.Child(node.ast_node.type))
		getattr(node.ast_node, 'inst', None) and self.inference(scope, node.Child(node.ast_node.inst))
		getattr(node.ast_node, 'tback', None) and self.inference(scope, node.Child(node.ast_node.tback))
		getattr(node.ast_node, 'exc', None) and self.inference(scope, node.Child(node.ast_node.exc))
		getattr(node.ast_node, 'cause', None) and self.inference(scope, node.Child(node.ast_node.cause))
		return UndefinedType

	def inference_Try(self, scope, node):
		body_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.body:
			self.inference(body_scope, node.Child(stmt))
		handlers_scope = Scope(Scope.BRANCH, None, scope)
		for handler in node.ast_node.handlers:
			self.inference(handlers_scope, node.Child(handler))
		orelse_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.orelse:
			self.inference(orelse_scope, node.Child(stmt))
		finalbody_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.finalbody:
			self.inference(finalbody_scope, node.Child(stmt))
		scope.combine(scope, node, False, body_scope, handlers_scope, orelse_scope, finalbody_scope)
		return UndefinedType

	def inference_TryExcept(self, scope, node):
		body_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.body:
			self.inference(body_scope, node.Child(stmt))
		handlers_scope = Scope(Scope.BRANCH, None, scope)
		for handler in node.ast_node.handlers:
			self.inference(handlers_scope, node.Child(handler))
		orelse_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.orelse:
			self.inference(orelse_scope, node.Child(stmt))
		scope.combine(scope, node, False, body_scope, handlers_scope, orelse_scope)
		return UndefinedType

	def inference_TryFinally(self, scope, node):
		body_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.body:
			self.inference(body_scope, node.Child(stmt))
		finalbody_scope = Scope(Scope.BRANCH, None, scope)
		for stmt in node.ast_node.finalbody:
			self.inference(finalbody_scope, node.Child(stmt))
		scope.combine(scope, node, False, body_scope, finalbody_scope)
		return UndefinedType

	def inference_Assert(self, scope, node):
		node.ast_node.test and self.inference(scope, node.Child(node.ast_node.test))
		node.ast_node.msg and self.inference(scope, node.Child(node.ast_node.msg))
		return UndefinedType

	def inference_Import(self, scope, node):
		for alias in node.ast_node.names:
			module_type = self.import_module(0, alias.name or '', node) or UnknownType(node, 'import', None)
			scope.assign(scope, node, alias.asname or alias.name, module_type)
		return UndefinedType

	def inference_ImportFrom(self, scope, node):
		module_type = self.import_module(node.ast_node.level or 0, node.ast_node.module or '', node)
		module_type and self.lazy_load(module_type)

		for alias in node.ast_node.names:
			imported_name = alias.asname or alias.name
			if imported_name == '*':
				if module_type:
					scope.bindings.update(module_type.scope.bindings)
					for imported_name, imported_type in module_type.builtins.items():
						if imported_name != '__name__':
							scope.assign(scope, node, imported_name, imported_type)
			elif not module_type:
				scope.assign(scope, node, imported_name, UnknownType(node, 'cannot import "%s"' % node.ast_node.module, None))
			elif module_type.scope and alias.name in module_type.scope.bindings:
				scope.bindings[imported_name] = module_type.scope.bindings[alias.name]
			elif alias.name in module_type.builtins:
				scope.assign(scope, node, imported_name, module_type.builtins[alias.name])
			else:
				scope.assign(scope, node, imported_name, UnknownType(node, 'import "%s" not found from "%s"' % (alias.name, module_type), None))

		return UndefinedType

	def inference_Exec(self, scope, node):
		node.ast_node.body and self.inference(scope, node.Child(node.ast_node.body))
		node.ast_node.globals and self.inference(scope, node.Child(node.ast_node.globals))
		node.ast_node.locals and self.inference(scope, node.Child(node.ast_node.locals))
		return UndefinedType

	def inference_Global(self, scope, node):
		for name in node.ast_node.names:
			scope.add_global(name)
		return UndefinedType

	def inference_Nonlocal(self, scope, node):
		for name in node.ast_node.names:
			scope.add_nonlocal(name)
		return UndefinedType

	def inference_Expr(self, scope, node):
		return self.inference(scope, node.Child(node.ast_node.value))

	def inference_Pass(self, scope, node):
		return UndefinedType

	def inference_Break(self, scope, node):
		return UndefinedType

	def inference_Continue(self, scope, node):
		return UndefinedType

	def inference_Slice(self, scope, node):
		return SliceType(
			node.ast_node.lower and self.inference(scope, node.Child(node.ast_node.lower)) or NoneType,
			node.ast_node.upper and self.inference(scope, node.Child(node.ast_node.upper)) or NoneType,
			node.ast_node.step and self.inference(scope, node.Child(node.ast_node.step)) or NoneType)

	def inference_ExtSlice(self, scope, node):
		return FixedTupleType(scope, node, *[self.inference(scope, node.Child(dim)) for dim in node.ast_node.dims])

	def inference_Ellipsis(self, scope, node):
		return EllipsisType

	def inference_Index(self, scope, node):
		return self.inference(scope, node.Child(node.ast_node.value))

	def inference_BoolOp(self, scope, node):
		if isinstance(node.ast_node.op, ast.And):
			stop_value = False
		elif isinstance(node.ast_node.op, ast.Or):
			stop_value = True
		else:
			assert False, node

		result_type = None
		value_types = [self.inference(scope, node.Child(value)) for value in node.ast_node.values]
		for value_type in value_types:
			boolean_type = value_type.to_boolean(scope, node)
			if boolean_type is BooleanType(True):
				if stop_value is True and result_type is None:
					result_type = value_type
			elif boolean_type is BooleanType(False):
				if stop_value is False and result_type is None:
					result_type = value_type
			elif boolean_type is BooleanType('?'):
				return UnionType(scope, node, *value_types)

		if result_type is None:
			result_type = value_types[-1]
		return result_type

	def inference_BinOp(self, scope, node):
		left_type = self.inference(scope, node.Child(node.ast_node.left))
		right_type = self.inference(scope, node.Child(node.ast_node.right))
		return self.operator(scope, node.Child(node.ast_node.op), left_type, right_type)

	def inference_UnaryOp(self, scope, node):
		operand_type = self.inference(scope, node.Child(node.ast_node.operand))
		return self.operator(scope, node.Child(node.ast_node.op), operand_type)

	def inference_Lambda(self, scope, node):
		function_type = FunctionType(scope, node, '<lambda at %s:%d:%d>' % (node.root.filename, node.start_lineno, node.start_col_offset), self)
		args_ast = node.ast_node.args
		if not args_ast.vararg and not not args_ast.vararg and len(args_ast.args) == len(args_ast.defaults):
			self.callable_functions.add(function_type)
		return function_type

	def inference_IfExp(self, scope, node):
		test_type = self.inference(scope, node.Child(node.ast_node.test)).to_boolean(scope, node)
		body_type = self.inference(scope, node.Child(node.ast_node.body))
		else_type = self.inference(scope, node.Child(node.ast_node.orelse))
		if test_type is BooleanType(True):
			return body_type
		elif test_type is BooleanType(False):
			return else_type
		else:
			return UnionType(scope, node, body_type, else_type)

	def inference_Dict(self, scope, node):
		is_fixed = True
		dict_keys = []
		dict_values = []
		dict_others = []
		for i, key_node in enumerate(node.ast_node.keys):
			key_type = key_node and self.inference(scope, node.Child(key_node))
			value_type = self.inference(scope, node.Child(node.ast_node.values[i]))
			if key_type:
				dict_keys.append(key_type)
				dict_values.append(value_type)
			else:
				dict_others.append(value_type)
			if key_type is not NoneType and (not isinstance(key_type, (BooleanType, ComplexType, FloatType, IntegerType, StringType)) or key_type.value == '?'):
				is_fixed = False
			elif not key_type and not isinstance(value_type, FixedDictType):
				is_fixed = False

		if is_fixed:
			entries = dict(zip(dict_keys, dict_values))
			for other in dict_others:
				entries.update(other.entries)
			return FixedDictType(scope, node, entries)

		for other in dict_others:
			key_type = other.foreach_type(scope, node)
			dict_keys.append(key_type)
			dict_values.append(other.get_subscript(scope, node, key_type))
		return DictType(UnionType(scope, node, *dict_keys), UnionType(scope, node, *dict_values))

	def inference_Set(self, scope, node):
		set_items = [self.inference(scope, node.Child(item)) for item in node.ast_node.elts]
		return SetType(scope, node, *set_items)

	def inference_ListComp(self, scope, node):
		for generator in node.ast_node.generators:
			iter_type = self.inference(scope, node.Child(generator.iter)).foreach_type(scope, node)
			self.assign(scope, node.Child(generator.target), iter_type)
			for if_node in generator.ifs:
				self.inference(scope, node.Child(if_node))
		return ListType(self.inference(scope, node.Child(node.ast_node.elt)))

	def inference_SetComp(self, scope, node):
		for generator in node.ast_node.generators:
			iter_type = self.inference(scope, node.Child(generator.iter)).foreach_type(scope, node)
			self.assign(scope, node.Child(generator.target), iter_type)
			for if_node in generator.ifs:
				self.inference(scope, node.Child(if_node))
		return SetType(scope, node, self.inference(scope, node.Child(node.ast_node.elt)))

	def inference_DictComp(self, scope, node):
		for generator in node.ast_node.generators:
			iter_type = self.inference(scope, node.Child(generator.iter)).foreach_type(scope, node)
			self.assign(scope, node.Child(generator.target), iter_type)
			for if_node in generator.ifs:
				self.inference(scope, node.Child(if_node))
		key_type = self.inference(scope, node.Child(node.ast_node.key))
		value_type = self.inference(scope, node.Child(node.ast_node.value))
		return DictType(key_type, value_type)

	def inference_GeneratorExp(self, scope, node):
		for generator in node.ast_node.generators:
			iter_type = self.inference(scope, node.Child(generator.iter)).foreach_type(scope, node)
			self.assign(scope, node.Child(generator.target), iter_type)
			for if_node in generator.ifs:
				self.inference(scope, node.Child(if_node))
		return GeneratorType(self.inference(scope, node.Child(node.ast_node.elt)))

	def inference_Yield(self, scope, node):
		value_type = node.ast_node.value and self.inference(scope, node.Child(node.ast_node.value)) or NoneType
		scope.set_result(node, value_type, Binding.YIELD)
		return UndefinedType

	def inference_Compare(self, scope, node):
		result = BooleanType(True)
		left_type = self.inference(scope, node.Child(node.ast_node.left))
		comparators = [self.inference(scope, node.Child(comparator)) for comparator in node.ast_node.comparators]
		for i, operator in enumerate(node.ast_node.ops):
			compare_type = self.operator(scope, node.Child(operator), left_type, comparators[i])
			if compare_type is BooleanType(False):
				result = BooleanType(False)
			elif compare_type is not BooleanType(True):
				result = BooleanType('?')
			left_type = comparators[i]
		return result

	def inference_Call(self, scope, node):
		starred_args = []
		follow_starred = []
		argument_types = []
		for arg in node.ast_node.args:
			if hasattr(ast, 'Starred') and isinstance(arg, ast.Starred):
				arg_type = self.inference(scope, node.Child(arg).Child(arg.value))
				if isinstance(arg_type, (FixedListType, FixedTupleType)):
					argument_types.extend(arg_type.items)
				else:
					starred_args.append(arg_type)
			elif starred_args:
				follow_starred.append(self.inference(scope, node.Child(arg)))
			else:
				argument_types.append(self.inference(scope, node.Child(arg)))

		if hasattr(node.ast_node, 'starargs') and node.ast_node.starargs:
			assert not starred_args
			starargs = self.inference(scope, node.Child(node.ast_node.starargs))
		elif starred_args:
			starargs = TupleType(UnionType(scope, node, *(follow_starred + [arg.foreach_type(scope, node) for arg in starred_args])))
		else:
			starargs = None

		kwargs = []
		keywords = {}
		for keyword in node.ast_node.keywords:
			keyword_type = self.inference(scope, node.Child(keyword.value))
			if keyword.arg:
				keywords[keyword.arg] = keyword_type
			elif isinstance(keyword_type, FixedDictType):
				for key_type, value_type in keyword_type.entries.items():
					if isinstance(key_type, StringType) and key_type.value != '?':
						keywords[key_type.value] = value_type
			else:
				kwargs.append(keyword_type)
		if hasattr(node.ast_node, 'kwargs') and node.ast_node.kwargs:
			kwargs.append(self.inference(scope, node.Child(node.ast_node.kwargs)))
		func_type = self.inference(scope, node.Child(node.ast_node.func))
		return func_type.invoke(scope, node, argument_types, keywords, starargs, kwargs)

	def inference_Repr(self, scope, node):
		node.ast_node.value and self.inference(scope, node.Child(node.ast_node.value))
		return UndefinedType

	def inference_Constant(self, scope, node):
		value = node.ast_node.value
		if value is None:
			return NoneType
		elif value is Ellipsis:
			return EllipsisType
		elif isinstance(value, bool):
			return BooleanType(value)
		elif isinstance(value, complex):
			return ComplexType(value)
		elif isinstance(value, float):
			return FloatType(value)
		elif isinstance(value, PythonIntegerType):
			return IntegerType(value)
		elif isinstance(value, PythonStringType):
			return StringType(value)
		assert False

	def inference_Num(self, scope, node):
		value = node.ast_node.n
		if isinstance(value, float):
			return FloatType(value)
		elif isinstance(value, PythonIntegerType):
			return IntegerType(value)
		elif isinstance(value, complex):
			return ComplexType(value)
		assert False, (value, type(value))

	def inference_Str(self, scope, node):
		return StringType(node.ast_node.s)

	def inference_Attribute(self, scope, node):
		attr_name = node.ast_node.attr
		value_node = node.Child(node.ast_node.value)
		node_type = self.inference(scope, value_node)
		if node_type is BUILTINS['type'] and attr_name == '__new__':
			return BuiltinFunctionType_type_static_new()
		attr_type = node_type.lookup_attr(scope, node, attr_name, self, value_node, None)
		if not attr_type:
			attr_type = UnknownType(node, 'attribute "%s" not found' % attr_name, node_type)
		return attr_type

	def inference_Subscript(self, scope, node):
		value_type = self.inference(scope, node.Child(node.ast_node.value))
		slice_type = self.inference(scope, node.Child(node.ast_node.slice))
		return value_type.get_subscript(scope, node, slice_type)

	def inference_Name(self, scope, node):
		target_name = node.ast_node.id
		value_type = self.lookup(scope, node, target_name, False)
		return value_type or UnknownType(node, 'variable "%s" not found in %s' % (target_name, scope), None)

	def inference_List(self, scope, node):
		starred_items = []
		list_items = []
		for item in node.ast_node.elts:
			if hasattr(ast, 'Starred') and isinstance(item, ast.Starred):
				item_type = self.inference(scope, node.Child(item).Child(item.value))
				if isinstance(item_type, (FixedListType, FixedTupleType)):
					list_items.extend(item_type.items)
				else:
					starred_items.append(item_type)
			else:
				list_items.append(self.inference(scope, node.Child(item)))

		if starred_items:
			return ListType(UnionType(scope, node, *(list_items + [item.foreach_type(scope, node) for item in starred_items])))
		else:
			return FixedListType(scope, node, *list_items)

	def inference_Tuple(self, scope, node):
		starred_items = []
		tuple_items = []
		for item in node.ast_node.elts:
			if hasattr(ast, 'Starred') and isinstance(item, ast.Starred):
				item_type = self.inference(scope, node.Child(item).Child(item.value))
				if isinstance(item_type, (FixedListType, FixedTupleType)):
					tuple_items.extend(item_type.items)
				else:
					starred_items.append(item_type)
			else:
				tuple_items.append(self.inference(scope, node.Child(item)))

		if starred_items:
			return TupleType(UnionType(scope, node, *(tuple_items + [item.foreach_type(scope, node) for item in starred_items])))
		else:
			return FixedTupleType(scope, node, *tuple_items)

	def inference_ExceptHandler(self, scope, node):
		if node.ast_node.type:
			exception_type = self.inference(scope, node.Child(node.ast_node.type))
			if node.ast_node.name:
				self.assign(scope, node.Child(node.ast_node.name), exception_type)
		for stmt in node.ast_node.body:
			self.inference(scope, node.Child(stmt))
		return UndefinedType

	def inference_TypeIgnore(self, scope, node):
		return UnknownType(node, 'unsupported node of TypeIgnore', None)

	def inference_FormattedValue(self, scope, node):
		return UnknownType(node, 'unsupported node of FormattedValue', None)

	def inference_JoinedStr(self, scope, node):
		return UnknownType(node, 'unsupported node of JoinedStr', None)

	def inference_YieldFrom(self, scope, node):
		return UnknownType(node, 'unsupported node of YieldFrom', None)

	def inference_NamedExpr(self, scope, node):
		return UnknownType(node, 'unsupported node of NamedExpr', None)

	def inference_AnnAssign(self, scope, node):
		return UnknownType(node, 'unsupported node of AnnAssign', None)

	def inference_AsyncFunctionDef(self, scope, node):
		return UnknownType(node, 'unsupported node of AsyncFunctionDef', None)

	def inference_AsyncFor(self, scope, node):
		return UnknownType(node, 'unsupported node of AsyncFor', None)

	def inference_AsyncWith(self, scope, node):
		return UnknownType(node, 'unsupported node of AsyncWith', None)

	def inference_Await(self, scope, node):
		return UnknownType(node, 'unsupported node of Await', None)
