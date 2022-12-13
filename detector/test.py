import detector
import os

def myprintType(v):
	print('\ttype:',v )
	if isinstance(v,detector.ModuleType):
		for k,v1 in v.scope.bindings.items():
			for vv1 in v1:
				myprintBinding(vv1)
	if isinstance(v,detector.FunctionType):
		for k,v1 in v.scope.bindings.items():
			for vv1 in v1:
				myprintBinding(vv1)
		for k,v1 in v.invocations.bindings.items():
			for vv1 in v1:
				myprintBinding(vv1)
	if isinstance(v,detector.ClassType):
		for k,v1 in v.scope.bindings.items():
			for vv1 in v1:
				myprintBinding(vv1)
		for v1 in v.instances:
			myprintType(v1)
		# myprintType(v.instances)
	if isinstance(v,detector.InstanceType):
		for k,v1 in v.scope.bindings.items():
			for vv1 in v1:
				myprintBinding(vv1)
	if isinstance(v,detector.MethodType):
		for k,v1 in v.scope.bindings.items():
			for vv1 in v1:
				myprintBinding(vv1)
	if isinstance(v,detector.UnionType):
		for t in v.types:
			myprintType(t)
	

def myprintBinding(v):
	print('___________')
	print('\tkind:',v.kind)
	print('\tname:',v.name)
	print('\tnode:',v.node)
	print('___________')
	myprintType(v.type)



#需要运行的项目路径
projectPath ='./result/test.py'
paths = [p for p, ds, fs in os.walk(projectPath)]
code_base = detector.CodeBase(paths + [os.path.join(os.path.dirname(__file__), 'lib')])
code_base.load(projectPath)

import pprint
for k,v in code_base.modules.items():
	myprintType(v)
