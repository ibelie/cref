# -*- coding: utf-8 -*-

import detector
import json
import sys
import os

detector.LOG_LEVEL = 15
detector.WARN_LEVEL = 15

def check_is_instance(binding_type, instance_type):
	# return binding_type is instance_type
	if isinstance(binding_type, detector.UnionType):
		for t in binding_type.types:
			if check_is_instance(t, instance_type):
				return True
	return binding_type is instance_type

def check_contains_instance(container_type, instance_type):
	# return check_contains_instance_exact(container_type, instance_type)
	if isinstance(container_type, detector.DictType):
		return check_is_instance(container_type.key, instance_type) or check_is_instance(container_type.value, instance_type)
	elif isinstance(container_type, detector.FixedDictType):
		for key_type, value_types in container_type.entries.items():
			if check_is_instance(key_type, instance_type) or check_is_instance(value_types, instance_type):
				return True
	elif isinstance(container_type, (detector.FixedListType, detector.FixedTupleType, detector.SetType)):
		for item_type in container_type.items:
			if check_is_instance(item_type, instance_type):
				return True
	elif isinstance(container_type, (detector.GeneratorType, detector.ListType, detector.TupleType)):
		return check_is_instance(container_type.item, instance_type)
	elif isinstance(container_type, detector.UnionType):
		for t in container_type.types:
			if check_contains_instance(t, instance_type):
				return True
	return False

def check_is_instance_exact(binding_type, instance_type):
	# return check_is_instance(binding_type, instance_type)
	return binding_type is instance_type

def check_contains_instance_exact(container_type, instance_type):
	# return check_contains_instance(container_type, instance_type)
	if isinstance(container_type, detector.DictType):
		return container_type.key is instance_type or container_type.value is instance_type
	elif isinstance(container_type, detector.FixedDictType):
		for key_type, value_types in container_type.entries.items():
			if key_type is instance_type or value_types is instance_type:
				return True
	elif isinstance(container_type, (detector.FixedListType, detector.FixedTupleType, detector.SetType)):
		for item_type in container_type.items:
			if item_type is instance_type:
				return True
	elif isinstance(container_type, (detector.GeneratorType, detector.ListType, detector.TupleType)):
		return container_type.item is instance_type
	elif isinstance(container_type, detector.UnionType):
		for t in container_type.types:
			if check_contains_instance_exact(t, instance_type):
				return True
	return False

def find_self_reference(classes):
	def _check_self_reference(instance_type):
		for name, bindings in instance_type.scope.bindings.items():
			for binding in bindings:
				if check_is_instance_exact(binding.type, instance_type):
					return True
		return False

	for class_type in classes:
		for instance_type in class_type.instances:
			if _check_self_reference(instance_type):
				yield class_type,
				break

def find_self_with_container(classes):
	def _check_self_with_container(instance_type):
		for name, bindings in instance_type.scope.bindings.items():
			for binding in bindings:
				if check_contains_instance_exact(binding.type, instance_type):
					return True
		return False

	for class_type in classes:
		for instance_type in class_type.instances:
			if _check_self_with_container(instance_type):
				yield class_type,
				break

def find_instance_method(classes):
	def _check_instance_method(instance_type):
		for name, bindings in instance_type.scope.bindings.items():
			for binding in bindings:
				if isinstance(binding.type, detector.MethodType) and check_is_instance_exact(binding.type.instance_type, instance_type):
					return True
				elif isinstance(binding.type, detector.UnionType):
					for t in binding.type.types:
						if isinstance(t, detector.MethodType) and check_is_instance_exact(t.instance_type, instance_type):
							return True
		return False

	for class_type in classes:
		for instance_type in class_type.instances:
			if _check_instance_method(instance_type):
				yield class_type,
				break

def find_couple_reference(classes):
	def _check_couple_reference(inst1_type, inst2_type):
		for name, bindings in inst1_type.scope.bindings.items():
			for binding in bindings:
				if check_is_instance(binding.type, inst2_type):
					return True
		return False

	for class_type in classes:
		couple_types = set()
		for instance_type in class_type.instances:
			for name, bindings in instance_type.scope.bindings.items():
				for binding in bindings:
					if binding.type is instance_type:
						continue
					elif isinstance(binding.type, detector.InstanceType) and isinstance(binding.type.class_type, detector.ClassType) and _check_couple_reference(binding.type, instance_type):
						couple_types.add(binding.type.class_type)
					elif isinstance(binding.type, detector.UnionType):
						for t in binding.type.types:
							if t is instance_type:
								continue
							elif isinstance(t, detector.InstanceType) and isinstance(t.class_type, detector.ClassType) and _check_couple_reference(t, instance_type):
								couple_types.add(t.class_type)
		if couple_types:
			for couple_type in couple_types:
				yield class_type, couple_type

def find_couple_with_container(classes):
	def _check_couple_with_container(inst1_type, inst2_type):
		for name, bindings in inst1_type.scope.bindings.items():
			for binding in bindings:
				if check_contains_instance(binding.type, inst2_type):
					return True
		return False

	for class_type in classes:
		couple_types = set()
		for instance_type in class_type.instances:
			for name, bindings in instance_type.scope.bindings.items():
				for binding in bindings:
					if binding.type is instance_type:
						continue
					elif isinstance(binding.type, detector.InstanceType) and isinstance(binding.type.class_type, detector.ClassType) and _check_couple_with_container(binding.type, instance_type):
						couple_types.add(binding.type.class_type)
					elif isinstance(binding.type, detector.UnionType):
						for t in binding.type.types:
							if t is instance_type:
								continue
							elif isinstance(t, detector.InstanceType) and isinstance(t.class_type, detector.ClassType) and _check_couple_with_container(t, instance_type):
								couple_types.add(t.class_type)
		if couple_types:
			for couple_type in couple_types:
				yield class_type, couple_type

def find_couple_with_method(classes):
	def _check_couple_with_method(inst1_type, inst2_type):
		for name, bindings in inst1_type.scope.bindings.items():
			for binding in bindings:
				if isinstance(binding.type, detector.MethodType) and check_is_instance_exact(binding.type.instance_type, inst2_type):
					return True
		return False

	for class_type in classes:
		couple_types = set()
		for instance_type in class_type.instances:
			for name, bindings in instance_type.scope.bindings.items():
				for binding in bindings:
					if binding.type is instance_type or not isinstance(binding.type, detector.InstanceType) or not isinstance(binding.type.class_type, detector.ClassType):
						continue
					if _check_couple_with_method(binding.type, instance_type):
						couple_types.add(binding.type.class_type)
		if couple_types:
			for couple_type in couple_types:
				yield class_type, couple_type

def collect_definitions(coverage, source_dir, classes, functions):
	new_classes = set()
	for class_type in detector.ClassType.classes:
		if class_type in classes or not class_type.node: continue
		if class_type.name.endswith('TestCase'): continue
		class_node = class_type.node
		if not class_node.filename.startswith(source_dir):
			continue
		filename = class_node.filename[len(source_dir):]
		if filename not in coverage:
			continue
		for lineno in coverage[filename]:
			if class_node.start_lineno <= lineno <= class_node.end_lineno:
				new_classes.add(class_type)
				classes.add(class_type)
				break

	new_functions = set()
	for function_type in detector.FunctionType.functions:
		if function_type in functions: continue
		function_node = function_type.node
		if not function_node.filename.startswith(source_dir):
			continue
		filename = function_node.filename[len(source_dir):]
		if filename not in coverage:
			continue
		for lineno in coverage[filename]:
			if True or (function_node.start_lineno <= lineno <= function_node.end_lineno):
				if not function_type.invoke_count:
					new_functions.add(function_type)
					functions.add(function_type)
				break

	return new_classes, new_functions

MethodInvokeCallback = None
OriginMethodInvoke = detector.MethodType.invoke
def MethodInvoke(self, scope, node, args, keywords, starargs, kwargs):
	global MethodInvokeCallback
	global OriginMethodInvoke
	if MethodInvokeCallback:
		MethodInvokeCallback(self.instance_type, self.function_type)
	return OriginMethodInvoke(self, scope, node, args, keywords, starargs, kwargs)
detector.MethodType.invoke = MethodInvoke

def fineStaticType(git_path, class_type):
	node = class_type.node
	if not node:
		return ('', class_type.name)
	elif not node.filename.startswith(git_path):
		return (node.filename, class_type.name)
	return (node.filename[len(git_path):].lstrip('/'), class_type.name)

def fineStaticCircle(git_path, circle):
	return tuple(fineStaticType(git_path, t) for t in circle)

def fineDynamicType(git_path, search_paths, object_type_source, object_type):
	object_type = tuple(object_type)
	if object_type not in object_type_source:
		filename = '/'.join(object_type[:-1]) + '.py'
		package = '/'.join(object_type[:-1]) + '/__init__.py'
		for p in search_paths:
			source_path = os.path.join(p, filename)
			if os.path.isfile(source_path):
				object_type_source[object_type] = source_path[len(git_path):].lstrip('\\/').replace('\\', '/')
				break
			source_path = os.path.join(p, package)
			if os.path.isfile(source_path):
				object_type_source[object_type] = source_path[len(git_path):].lstrip('\\/').replace('\\', '/')
				break
	return (object_type_source[object_type], object_type[-1])

def fineDynamicCircle(g, s, o, circle):
	return tuple(fineDynamicType(g, s, o, t) for t in circle if len(t) > 1 or t[0] not in ('list', 'dict', 'tuple', 'set', 'method'))

def iterDerivedCircles(fine_classes, circle):
	if len(circle) == 1:
		for derived_type in set(fine_classes[circle[0]][1]) | fine_classes[circle[0]][2]:
			yield derived_type,
	else:
		for derived_tail in iterDerivedCircles(fine_classes, circle[1:]):
			for derived_type in set(fine_classes[circle[0]][1]) | fine_classes[circle[0]][2]:
				yield (derived_type, ) + derived_tail

def iterBaseCircles(fine_classes, circle):
	if len(circle) == 1:
		for i, derived_type in enumerate(fine_classes[circle[0]][1]):
			yield i, (derived_type, )
	else:
		for i, derived_tail in iterBaseCircles(fine_classes, circle[1:]):
			for j, derived_type in enumerate(fine_classes[circle[0]][1]):
				yield (i + j), ((derived_type, ) + derived_tail)

def checkCircles(fine_classes, found_circles, answer_circles):
	accuracy_set = set()
	right_circles = set()
	extra_circles = set()
	wrong_circles = set()
	assert all(all((t in fine_classes) for t in c) for c in answer_circles)
	for fine_circle in found_circles:
		found_answer = False
		for i, answer in enumerate(answer_circles):
			if len(fine_circle) != len(answer):
				continue
			elif fine_circle == answer or fine_circle[::-1] == answer:
				found_answer = True
				accuracy_set.add(i)
				right_circles.add(fine_circle)
		if not found_answer:
			for i, answer in enumerate(answer_circles):
				if len(fine_circle) != len(answer): continue
				for derived_circles in iterDerivedCircles(fine_classes, fine_circle):
					for derived_answer in iterDerivedCircles(fine_classes, answer):
						if derived_circles == derived_answer or derived_circles[::-1] == derived_answer:
							found_answer = True
							break
					if found_answer: break
				if found_answer:
					accuracy_set.add(i)
					extra_circles.add(fine_circle)
		if not found_answer:
			wrong_circles.add(tuple(sorted(fine_circle)))

	base_circles = {}
	remove_circles = set()
	for fine_circle in wrong_circles:
		base_circles[fine_circle] = {}
		for depth, base_circle in iterBaseCircles(fine_classes, fine_circle):
			base_circles[fine_circle][base_circle] = depth
			if base_circle != fine_circle and (base_circle in wrong_circles or base_circle[::-1] in wrong_circles):
				remove_circles.add(fine_circle)
				break
			for i in range(1, len(base_circle)):
				if base_circle[:i] in wrong_circles:
					remove_circles.add(fine_circle)
					break
			else:
				continue
			break
		if fine_circle in remove_circles:
			base_circles.pop(fine_circle)
	wrong_circles -= remove_circles

	merged_circles = True
	while merged_circles:
		remove_circles = set()
		merged_circles = set()
		for circle in wrong_circles:
			if circle in base_circles: continue
			base_circles[circle] = {c: d for d, c in iterBaseCircles(fine_classes, circle)}
		for circle1 in wrong_circles:
			if circle1 in remove_circles: continue
			for circle2 in wrong_circles:
				if circle1 == circle2 or circle2 in remove_circles: continue
				common_circles = set(base_circles[circle1]) & set(base_circles[circle2])
				if not common_circles: continue
				merged_circles.add(sorted(common_circles, key = lambda c: base_circles[circle1][c] + base_circles[circle2][c])[0])
				remove_circles.add(circle1)
				remove_circles.add(circle2)
				break
			else:
				continue
			break
		if merged_circles:
			wrong_circles = (wrong_circles - remove_circles) | merged_circles

	return [sorted(right_circles), sorted(extra_circles), sorted(wrong_circles),
		sorted(answer_circles[i] for i in accuracy_set),
		sorted(c for i, c in enumerate(answer_circles) if i not in accuracy_set),
	]

def find_circles(git_path, commit, circles_path, coverage_path, result_path, pattern):
	git_path = git_path.replace('\\', '/')
	dynamic_circles = {}
	object_type_source = {}
	search_paths = [os.path.dirname(git_path)] + [p for p, ds, fs in os.walk(git_path)]
	with open(circles_path, 'r') as f:
		for name, circle_type in json.load(f):
			fine_circle = fineDynamicCircle(git_path, search_paths, object_type_source, circle_type)
			dynamic_circles.setdefault(name, []).append(fine_circle)

	with open(coverage_path, 'r') as f:
		coverage = json.load(f)

	pwd = os.getcwd()
	os.chdir(git_path)
	cmd = 'git checkout %s' % commit
	# assert os.system(cmd) == 0
	os.chdir(pwd)

	detector.log(20, '==================================================')
	detector.log(20, 'loading:', os.path.basename(git_path), commit)

	paths = [p for p, ds, fs in os.walk(git_path)]
	code_base = detector.CodeBase(paths + [os.path.join(os.path.dirname(__file__), 'lib')])
	code_base.load(git_path)

	global MethodInvokeCallback
	source_dir = git_path.replace('\\', '/') + '/'
	classes = set()
	functions = set()
	new_classes, new_functions = collect_definitions(coverage, source_dir, classes, functions)
	while new_classes or new_functions:
		for class_type in new_classes:
			scopes = [t.scope for t in class_type.get_mro() if t.scope]
			methods = set()
			for scope in scopes:
				for name, bindings in scope.bindings.items():
					if name in ('__init__', '__new__'): continue
					for binding in bindings:
						if binding.type in functions:
							methods.add(name)
			instance_type = class_type.invoke(None, None, None, None, None, None)
			called_methods = set()
			MethodInvokeCallback = lambda i_t, f_t: called_methods.add(getattr(f_t, 'name', None)) if i_t is instance_type else None
			for name in methods:
				if 'setup' not in name.lower() or name in called_methods: continue
				method_type = class_type.lookup_attr(None, None, name, code_base, None, instance_type)
				method_type.invoke(None, None, None, None, None, None)
			for name in methods:
				if 'setup' in name.lower() or name in called_methods: continue
				method_type = class_type.lookup_attr(None, None, name, code_base, None, instance_type)
				method_type.invoke(None, None, None, None, None, None)
			MethodInvokeCallback = None

		for function_type in new_functions:
			not function_type.invoke_count and function_type.invoke(None, None, None, None, None, None)

		new_classes, new_functions = collect_definitions(coverage, source_dir, classes, functions)

	fine_classes = {}
	for class_type in detector.ClassType.classes:
		fine_class = fineStaticType(git_path, class_type)
		base_types = fine_classes.setdefault(fine_class, [class_type, [], set()])[1]
		for base_type in class_type.get_mro():
			if isinstance(base_type, detector.ClassType) and base_type.node and base_type.node.filename.startswith(git_path):
				fine_base = fineStaticType(git_path, base_type)
				base_types.append(fine_base)
				fine_classes.setdefault(fine_base, [base_type, [], set()])[2].add(fine_class)

	static_circles = {}
	total_found_circles = set()
	total_answer_circles = set()
	for name, func in sorted(globals().items()):
		if name == 'find_circles' or not name.startswith('find_') or not callable(func):
			continue
		name = name[len('find_'):]
		if pattern != 'all' and name != pattern: continue

		found_circles = [fineStaticCircle(git_path, circle) for circle in func(classes)]
		answer_circles = dynamic_circles.get(name, ())
		static_circles[name] = checkCircles(fine_classes, found_circles, answer_circles)
		total_found_circles.update(found_circles)
		total_answer_circles.update(answer_circles)
		detector.log(20, name, [len(s) for s in static_circles[name]])
	static_circles['all'] = checkCircles(fine_classes, sorted(total_found_circles), sorted(total_answer_circles))
	detector.log(20, 'all', [len(s) for s in static_circles['all']])

	folder = result_path.rpartition('/')[0]
	not os.path.isdir(folder) and os.makedirs(folder)
	with open(result_path, 'w') as f:
		json.dump(static_circles, f, indent = 4, sort_keys = True)

if __name__ == '__main__':
	find_circles(*sys.argv[1:])
