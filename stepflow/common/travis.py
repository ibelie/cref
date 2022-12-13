#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils
import subprocess
import threading
import traceback
import warnings
import shutil
import socket
import stat
import os
import re

GROUP = 'Travis'


#     .                                   o8o
#   .o8                                   `"'
# .o888oo oooo d8b  .oooo.   oooo    ooo oooo   .oooo.o
#   888   `888""8P `P  )88b   `88.  .8'  `888  d88(  "8
#   888    888      .oP"888    `88..8'    888  `"Y88b.
#   888 .  888     d8(  888     `888'     888  o.  )88b
#   "888" d888b    `Y888""8o     `8'     o888o 8""888P'

# 下载需要的docker镜像，创建travis-build镜像
class travis(Step):
	'Pull travis docker images and build the image of travis-build'

	REQUIRE = ()

	TRAVIS_IMAGES = {
		# 'android': 'travis/amethyst',
		# 'erlang':  'travis/amethyst',
		# 'haskell': 'travis/amethyst',
		# 'perl':    'travis/amethyst',
		'default': 'travis/garnet',
		'go':      'travis/garnet',
		'jvm':     'travis/garnet',
		'node_js': 'travis/garnet',
		'php':     'travis/garnet',
		'python':  'travis/garnet',
		'ruby':    'travis/garnet',
	}

	def load(self):
		import docker
		client = docker.from_env(version = 'auto')
		for image in set(self.TRAVIS_IMAGES.itervalues()):
			if not client.api.images(image, quiet = True):
				return False
		self.client = client
		return True

	def generate(self):
		import docker
		client = docker.from_env(version = 'auto')
		for image in set(self.TRAVIS_IMAGES.itervalues()):
			response = client.api.build(path = image, tag = image, rm = True)
			imageID = None
			for event in docker.utils.json_stream.json_stream(response):
				if 'error' in event:
					print event['error']
					return False
				elif 'stream' in event:
					print event['stream'],
					match = re.search(r'(^Successfully built |sha256:)([0-9a-f]+)$', event['stream'])
					if match:
						imageID = match.group(2)
				else:
					print event
			if not imageID:
				return False
		self.client = client
		return True


#     .                                   o8o                oooooo   oooo       .o.       ooo        ooooo ooooo
#   .o8                                   `"'                 `888.   .8'       .888.      `88.       .888' `888'
# .o888oo oooo d8b  .oooo.   oooo    ooo oooo   .oooo.o        `888. .8'       .8"888.      888b     d'888   888
#   888   `888""8P `P  )88b   `88.  .8'  `888  d88(  "8         `888.8'       .8' `888.     8 Y88. .P  888   888
#   888    888      .oP"888    `88..8'    888  `"Y88b.           `888'       .88ooo8888.    8  `888'   888   888
#   888 .  888     d8(  888     `888'     888  o.  )88b           888       .8'     `888.   8    Y     888   888       o
#   "888" d888b    `Y888""8o     `8'     o888o 8""888P'          o888o     o88o     o8888o o8o        o888o o888ooooood8

# 加载已经准备好的.travis.yml
class travisYAML(Step):
	'load prepared .travis.yml'

	REQUIRE = 'projectInfo',

	def load(self):
		if not self.flow.project: return True
		data = {}
		root = self.get_root(self.flow.project)
		for build in self.flow.projectInfo.builds:
			path = self.get_path(build)
			if not os.path.isfile('%s/%s' % (root, path)):
				print 'No %s.travis.yml for %s' % (build['travis_yml'][1][:10], build['commit'])
			else:
				data[build['commit']] = path

		self.root = root
		self.data = data
		return len(data) == len(self.flow.projectInfo.builds)

	def get_root(self, project):
		path = os.path.abspath('data/%s/%s' % (project, self.__class__.__name__))
		if os.path.isdir(path): return path
		return os.path.abspath('data/prepare/%s' % project)

	def get_path(self, build):
		return '%s.travis.yml' % build['travis_yml'][1][:10]

	def generate(self):
		if not self.flow.project: return True
		raise RuntimeError, 'All the .travis.yml should be prepared by yourself!'


#                                                                      .o88o.  o8o  oooo
#                                                                      888 `"  `"'  `888
# oooo d8b oooo  oooo  ooo. .oo.        oo.ooooo.  oooo d8b  .ooooo.  o888oo  oooo   888   .ooooo.
# `888""8P `888  `888  `888P"Y88b        888' `88b `888""8P d88' `88b  888    `888   888  d88' `88b
#  888      888   888   888   888        888   888  888     888   888  888     888   888  888ooo888
#  888      888   888   888   888        888   888  888     888   888  888     888   888  888    .o
# d888b     `V88V"V8P' o888o o888o       888bod8P' d888b    `Y8bod8P' o888o   o888o o888o `Y8bod8P'
#                                        888
#                                       o888o

# 根据项目的.travis.yml在travis docker中构建并运行测试
class runProfile(Step):
	'Build and run project testing with .travis.yml in travis docker'

	REQUIRE = 'projectInfo', 'gitRepo', 'travis', 'tracks', 'travisYAML'

	languageRe = re.compile(r'\s*language\s*:\s*(?P<language>\S+)\s*', re.I)

	def load(self):
		return False

	def run(self, profileKey, **kwargs):
		def _run():
			cls = self.__class__
			try:
				container = self.flow.travis.client.containers.create(
					name = profileKey, cpuset_cpus = cpu,
					mem_limit = self.flow.MEM_LIMIT, **kwargs)
				container.start()

				logs = container.logs(stream = True)
				path = 'data/log/%s' % cls.__name__
				not os.path.isdir(path) and os.makedirs(path)
				with open('data/log/%s/%s.txt' % (cls.__name__, profileKey), 'w') as f:
					for log in logs:
						f.write(log)

				exit_status = container.wait()['StatusCode']
				print '    %s travis exit status:' % profileKey, exit_status

				if exit_status == 0:
					self.flow.tracks.extract(profileKey)

				container.remove()
			except Exception as e:
				warnings.warn('Travis profile "%s" error:\n%s' % (profileKey, traceback.format_exc()), RuntimeWarning)

			self.flow.CPU_LIST.add(cpu)
			self.flow.CPU_SEMA.release()

		self.flow.CPU_SEMA.acquire()
		cpu = self.flow.CPU_LIST.pop()
		threading.Thread(target = _run).start()

	def generate(self):
		cls = self.__class__
		hostIP = socket.gethostbyname(socket.gethostname())
		repoDir = '/home/travis/%s' % cls.__name__
		workDir = '/home/travis/build'
		yamlDir = '/home/travis/travisYAML'
		command = [
			'mkdir -p %s/%s' % (cls.__name__, self.flow.project),
			'cd %s/%s' % (cls.__name__, self.flow.project),
			'git clone %s . ' % repoDir,
			'git remote set-url origin https://github.com/%s/%s.git' % (cls.__name__, self.flow.project),
			'git checkout %s',
			'cp %s/%%s .travis.yml' % yamlDir,
			'~/travis_compile > ci.sh',
			'git remote set-url origin %s' % repoDir,
			'bash ci.sh',
		]
		command = '/bin/bash -lc "%s"' % ' && '.join(command)

		for build in self.flow.projectInfo.builds:
			commit = build['commit']
			path = '%s/%s' % (self.flow.travisYAML.root, self.flow.travisYAML.data[commit])
			with open(path, 'r') as f:
				line = f.readline()
				while line:
					m = self.languageRe.match(line)
					if m:
						image = self.flow.travis.TRAVIS_IMAGES[m.group('language')]
						break
					line = f.readline()
				else:
					image = self.flow.travis.TRAVIS_IMAGES['default']

			needSleep = False
			for i in xrange(self.flow.REPEAT_TEST):
				profileKey = '%s_%s_%d' % (self.flow.project, commit[:10], i)
				if self.flow.tracks.exist(profileKey):
					continue

				needSleep = True
				cmd = command % (commit, self.flow.travisYAML.data[commit])
				self.run(profileKey, image = image, command = cmd, user = 'travis',
					tmpfs = {workDir: 'exec,uid=2000,gid=2000'}, working_dir = workDir,
					volumes = {
						self.flow.gitRepo.path: {'bind': repoDir, 'mode': 'ro'},
						self.flow.travisYAML.root: {'bind': yamlDir, 'mode': 'ro'},
					},
					environment = {
						'HOST_IP': hostIP,
						'PROFILE_KEY': profileKey,
						'PROFILE_PATH': '%s/%s/%s' % (workDir, cls.__name__, self.flow.project),
					})
			import time
			needSleep and time.sleep(30)

		for _ in xrange(self.flow.CPU_COUNT):
			self.flow.CPU_SEMA.acquire()

		return False


#  .o8                     .             oooo             ooooooooo.
# "888                   .o8             `888             `888   `Y88.
#  888oooo.   .oooo.   .o888oo  .ooooo.   888 .oo.         888   .d88' oooo  oooo  ooo. .oo.   ooo. .oo.    .ooooo.  oooo d8b
#  d88' `88b `P  )88b    888   d88' `"Y8  888P"Y88b        888ooo88P'  `888  `888  `888P"Y88b  `888P"Y88b  d88' `88b `888""8P
#  888   888  .oP"888    888   888        888   888        888`88b.     888   888   888   888   888   888  888ooo888  888
#  888   888 d8(  888    888 . 888   .o8  888   888        888  `88b.   888   888   888   888   888   888  888    .o  888
#  `Y8bod8P' `Y888""8o   "888" `Y8bod8P' o888o o888o      o888o  o888o  `V88V"V8P' o888o o888o o888o o888o `Y8bod8P' d888b

# 导出Travis批量测试shell脚本
class batchProfileRunner(Step):
	'generate a shell script of a batch of profile runners'

	REQUIRE = 'projectInfo',

	def load(self):
		return False

	def generate(self):
		projects = []
		info = self.flow.projectInfo
		travis_build_path = '%s/%s' % (info.__module__.rpartition('.')[-1], info.TRAVIS_BUILD_PATH)
		for project, data in info.projects.iteritems():
			builds = utils.readData('data/%s/%s.json' % (travis_build_path, project))
			travis_yml = set((tuple(b['travis_yml']) for b in builds))
			travis_ok = len(filter(lambda (t, _): t, travis_yml))
			if len(travis_yml) != travis_ok:
				continue
			projects.append((project, len(builds)))

		projects.sort(key = lambda (_, builds): builds)

		mean = reduce(lambda s, p: s + p[1], projects[:-1], 0) / (len(projects) - 1)
		with open('batch_runner.sh', 'w') as f:
			f.write('export PYTHONPATH=$(cd `dirname $0`; pwd)\n\n')
			for i, (p, b) in enumerate(filter(lambda (p, _): p in (
				"djvusmooth",
				"anaconda",
				"DataProcessor",
				"i8c",
				"abydos",
				"pyFDA",
				"gofer",
				"petl",
				"custodian",
				"WALinuxAgent",
				"slpkg",
				"TriFusion",
				"sos"
				), projects)):
			# for i, (p, b) in enumerate(filter(lambda (_, b): b >= mean, projects)):
				f.write('echo "Travis run %s ..."\n' % p)
				f.write('[ ! -d data/%s ] && mkdir data/%s\n' % (p, p))
				f.write('[ -d data/%s/travisYAML ] && rm -rf data/%s/travisYAML\n' % (p, p))
				f.write('cp -r data/prepare/%s data/%s/travisYAML\n' % (p, p))
				f.write('python -B -m stepflow -s runProfile -p %s\n\n' % p)
		os.chmod("batch_runner.sh", stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

		return False


#                                                                                          oooo                      oooo
#                                                                                          `888                      `888
# oooo d8b oooo  oooo  ooo. .oo.        ooo. .oo.  .oo.    .ooooo.  ooo. .oo.  .oo.         888   .ooooo.   .oooo.    888  oooo
# `888""8P `888  `888  `888P"Y88b       `888P"Y88bP"Y88b  d88' `88b `888P"Y88bP"Y88b        888  d88' `88b `P  )88b   888 .8P'
#  888      888   888   888   888        888   888   888  888ooo888  888   888   888        888  888ooo888  .oP"888   888888.
#  888      888   888   888   888        888   888   888  888    .o  888   888   888        888  888    .o d8(  888   888 `88b.
# d888b     `V88V"V8P' o888o o888o      o888o o888o o888o `Y8bod8P' o888o o888o o888o      o888o `Y8bod8P' `Y888""8o o888o o888o

# 根据项目的.travis.yml在travis docker中构建并运行测试
class runMemLeak(Step):
	'Build and run project testing with .travis.yml in travis docker'

	REQUIRE = 'projectInfo', 'gitRepo', 'travis', 'travisYAML'

	DATA_PATH = os.path.abspath('data/memleak')

	languageRe = re.compile(r'\s*language\s*:\s*(?P<language>\S+)\s*', re.I)

	MAX_BUILD_COUNT = 50

	PROJECTS = ()

	def load(self):
		return False

	@staticmethod
	def check_log(path):
		if not os.path.isfile(path):
			return False
		try:
			return subprocess.check_output(('tail', path)).strip().endswith('Done. Your build exited with 0.')
		except:
			return False

	@staticmethod
	def check_data(path):
		if not os.path.isfile(path):
			return False
		try:
			return os.path.getsize(path) > 400000
		except:
			return True

	@classmethod
	def run(cls, cpu, project, builds, flow):
		repoDir = '/home/travis/git_repo'
		workDir = '/home/travis/build'
		yamlDir = '/home/travis/travisYAML'
		dataDir = '/home/travis/data'
		command = [
			'mkdir -p %s/%s' % (cls.__name__, project),
			'cd %s/%s' % (cls.__name__, project),
			'git clone %s . ' % repoDir,
			'git remote set-url origin https://github.com/%s/%s.git' % (cls.__name__, project),
			'git checkout %s',
			'cp %s/%%s .travis.yml' % yamlDir,
			'~/travis_compile | python ~/.properform/inject.py > ci.sh',
			'git remote set-url origin %s' % repoDir,
			'bash ci.sh',
		]
		command = '/bin/bash -lc "%s"' % ' && '.join(command)
		commit = None

		log_folder = 'data/log/%s' % cls.__name__
		not os.path.isdir(log_folder) and os.makedirs(log_folder)

		try:
			container = None
			git_path = None
			for build in builds:
				commit = build['commit']

				log_path = os.path.join(log_folder, '%s_%s.txt' % (project, commit))
				if not cls.check_log(log_path):
					continue

				data_path = os.path.join(cls.DATA_PATH, '%s_%s.json' % (project, commit))
				if cls.check_data(data_path):
					break

				if not git_path:
					git_path = flow.gitRepo.prepare(project)
				assert git_path
				travis_yml_root = flow.travisYAML.get_root(project)
				travis_yml_path = flow.travisYAML.get_path(build)
				with open(os.path.join(travis_yml_root, travis_yml_path), 'r') as f:
					line = f.readline()
					while line:
						m = cls.languageRe.match(line)
						if m:
							language = m.group('language')
							if language in flow.travis.TRAVIS_IMAGES:
								image = flow.travis.TRAVIS_IMAGES[language]
							else:
								image = flow.travis.TRAVIS_IMAGES['python']
							break
						line = f.readline()
					else:
						image = flow.travis.TRAVIS_IMAGES['default']

					cmd = command % (commit, travis_yml_path)
					container = flow.travis.client.containers.create(user = 'travis',
						name = '%s_%s' % (project, commit[:10]), cpuset_cpus = cpu,
						mem_limit = flow.MEM_LIMIT, image = image, command = cmd,
						tmpfs = {workDir: 'exec,uid=2000,gid=2000'}, working_dir = workDir,
						volumes = {
							git_path: {'bind': repoDir, 'mode': 'ro'},
							travis_yml_root: {'bind': yamlDir, 'mode': 'ro'},
							cls.DATA_PATH: {'bind': dataDir, 'mode': 'rw'},
						},
						environment = {
							'PROPERFORM_MEMLEAK_PATH': '%s/%s_%s.json' % (dataDir, project, commit),
						})
					container.start()

					logs = container.logs(stream = True)
					with open(log_path, 'w') as f:
						for log in logs:
							f.write(log)

					exit_status = container.wait()['StatusCode']
					print '    %s %s travis exit status:' % (project, commit), exit_status

					container.remove()
					container = None

					if cls.check_data(data_path):
						break

			git_path and os.path.isdir(git_path) and shutil.rmtree(git_path)
		except Exception as e:
			warnings.warn('Travis memory leak "%s" %s error:\n%s' % (project, commit, traceback.format_exc()), RuntimeWarning)
			container and container.remove()

		flow.CPU_LIST.add(cpu)
		flow.CPU_SEMA.release()

	def generate(self):
		projects = self.flow.projectInfo.projects
		if self.flow.project: projects = (self.flow.project, )
		for project in projects:
			if self.PROJECTS and project not in self.PROJECTS: continue
			builds = self.flow.projectInfo.get_builds(project)[:self.MAX_BUILD_COUNT]
			if not builds: continue
			for build in builds:
				commit = build['commit']
				path = os.path.join(self.DATA_PATH, '%s_%s.json' % (project, commit))
				if self.check_data(path):
					break
			else:
				self.flow.CPU_SEMA.acquire()
				cpu = self.flow.CPU_LIST.pop()
				threading.Thread(target = runMemLeak.run, args = (cpu, project, builds, self.flow)).start()

		for _ in xrange(self.flow.CPU_COUNT):
			self.flow.CPU_SEMA.acquire()

		return False


#                                                                                                               oooo                      oooo
#                                                                                                               `888                      `888
# oo.ooooo.  oooo d8b oooo  oooo  ooo. .oo.    .ooooo.       ooo. .oo.  .oo.    .ooooo.  ooo. .oo.  .oo.         888   .ooooo.   .oooo.    888  oooo
#  888' `88b `888""8P `888  `888  `888P"Y88b  d88' `88b      `888P"Y88bP"Y88b  d88' `88b `888P"Y88bP"Y88b        888  d88' `88b `P  )88b   888 .8P'
#  888   888  888      888   888   888   888  888ooo888       888   888   888  888ooo888  888   888   888        888  888ooo888  .oP"888   888888.
#  888   888  888      888   888   888   888  888    .o       888   888   888  888    .o  888   888   888        888  888    .o d8(  888   888 `88b.
#  888bod8P' d888b     `V88V"V8P' o888o o888o `Y8bod8P'      o888o o888o o888o `Y8bod8P' o888o o888o o888o      o888o `Y8bod8P' `Y888""8o o888o o888o
#  888
# o888o

class pruneMemLeak(Step):
	REQUIRE = 'projectInfo',

	DATA_PATH = os.path.abspath('data/memleak')

	def load(self):
		return False

	def generate(self):
		projects = self.flow.projectInfo.projects
		for project in projects:
			builds = self.flow.projectInfo.get_builds(project)
			if not builds: continue

			prune_files = set()
			max_file = None
			max_size = -1
			for build in builds:
				commit = build['commit']
				path = os.path.join(self.DATA_PATH, '%s_%s.json' % (project, commit))
				if not os.path.isfile(path): continue
				size = os.path.getsize(path)
				if size > max_size:
					if max_file:
						prune_files.add(max_file)
					max_file = path
					max_size = size
				else:
					prune_files.add(path)

			if prune_files:
				print prune_files
			for path in prune_files:
				os.unlink(path)

		return False


# ooooooo  ooooo
#  `8888    d8'
#    Y888..8P
#     `8888'
#    .8PY888.
#   d8'  `888b
# o888o  o88888o

# 根据项目的.travis.yml在travis docker中构建并运行测试
class coverageMemLeak_deprecated(Step):
	'Build and run project testing with .travis.yml in travis docker'

	REQUIRE = 'MemLeakStaticAnalyseProjects', 'MemLeakProjects', 'projectInfo', 'gitRepo', 'travis', 'travisYAML'

	DATA_PATH = os.path.abspath('data/memleak_coverage')

	def load(self):
		return False

	@classmethod
	def run(cls, cpu, project, commit, flow):
		repoDir = '/home/travis/git_repo'
		workDir = '/home/travis/build'
		yamlDir = '/home/travis/travisYAML'
		dataDir = '/home/travis/data'
		command = [
			'mkdir -p %s/%s' % (cls.__name__, project),
			'cd %s/%s' % (cls.__name__, project),
			'git clone %s . ' % repoDir,
			'git remote set-url origin https://github.com/%s/%s.git' % (cls.__name__, project),
			'git checkout %s',
			'cp %s/%%s .travis.yml' % yamlDir,
			'~/travis_compile | python ~/.properform/inject.py > ci.sh',
			'git remote set-url origin %s' % repoDir,
			'bash ci.sh',
		]
		command = '/bin/bash -lc "%s"' % ' && '.join(command)

		log_folder = 'data/log/%s' % cls.__name__
		not os.path.isdir(log_folder) and os.makedirs(log_folder)

		try:
			container = None
			log_path = os.path.join(log_folder, '%s_%s.txt' % (project, commit))
			data_path = os.path.join(cls.DATA_PATH, '%s_%s.cov' % (project, commit))
			git_path = flow.gitRepo.prepare(project)
			assert git_path
			builds = flow.projectInfo.get_builds(project)
			build = [b for b in builds if b['commit'] == commit].pop()
			travis_yml_root = flow.travisYAML.get_root(project)
			travis_yml_path = flow.travisYAML.get_path(build)
			with open(os.path.join(travis_yml_root, travis_yml_path), 'r') as f:
				line = f.readline()
				while line:
					m = runMemLeak.languageRe.match(line)
					if m:
						language = m.group('language')
						if language in flow.travis.TRAVIS_IMAGES:
							image = flow.travis.TRAVIS_IMAGES[language]
						else:
							image = flow.travis.TRAVIS_IMAGES['python']
						break
					line = f.readline()
				else:
					image = flow.travis.TRAVIS_IMAGES['default']

				cmd = command % (commit, travis_yml_path)
				container = flow.travis.client.containers.create(user = 'travis',
					name = '%s_%s' % (project, commit[:10]), cpuset_cpus = cpu,
					mem_limit = flow.MEM_LIMIT, image = image, command = cmd,
					tmpfs = {workDir: 'exec,uid=2000,gid=2000'}, working_dir = workDir,
					volumes = {
						git_path: {'bind': repoDir, 'mode': 'ro'},
						travis_yml_root: {'bind': yamlDir, 'mode': 'ro'},
						cls.DATA_PATH: {'bind': dataDir, 'mode': 'rw'},
					},
					environment = {
						'PROPERFORM_COVERAGE_PATH': '%s/%s_%s.cov' % (dataDir, project, commit),
					})
				container.start()

				logs = container.logs(stream = True)
				with open(log_path, 'w') as f:
					for log in logs:
						f.write(log)

				exit_status = container.wait()['StatusCode']
				print '    %s %s travis exit status:' % (project, commit), exit_status

				container.remove()
		except Exception as e:
			warnings.warn('Travis memory leak "%s" %s error:\n%s' % (project, commit, traceback.format_exc()), RuntimeWarning)
			container and container.remove()

		flow.CPU_LIST.add(cpu)
		flow.CPU_SEMA.release()

	def generate(self):
		for project in self.flow.MemLeakStaticAnalyseProjects.data:
			commit = self.flow.MemLeakProjects.data[project]['commit']
			path = os.path.join(self.DATA_PATH, '%s_%s.cov' % (project, commit))
			if not os.path.isfile(path):
				self.flow.CPU_SEMA.acquire()
				cpu = self.flow.CPU_LIST.pop()
				threading.Thread(target = coverageMemLeak.run, args = (cpu, project, commit, self.flow)).start()

		for _ in xrange(self.flow.CPU_COUNT):
			self.flow.CPU_SEMA.acquire()

		return False
