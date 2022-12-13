#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils
import subprocess
import time
import copy
import json
import os
import re

GROUP = 'Preparation'


#                            .   oooo                                     .oooooo.     o8o      .   oooo                     .o8
#                          .o8   `888                                    d8P'  `Y8b    `"'    .o8   `888                    "888
# oo.ooooo.  oooo    ooo .o888oo  888 .oo.    .ooooo.  ooo. .oo.        888           oooo  .o888oo  888 .oo.   oooo  oooo   888oooo.
#  888' `88b  `88.  .8'    888    888P"Y88b  d88' `88b `888P"Y88b       888           `888    888    888P"Y88b  `888  `888   d88' `88b
#  888   888   `88..8'     888    888   888  888   888  888   888       888     ooooo  888    888    888   888   888   888   888   888
#  888   888    `888'      888 .  888   888  888   888  888   888       `88.    .88'   888    888 .  888   888   888   888   888   888
#  888bod8P'     .8'       "888" o888o o888o `Y8bod8P' o888o o888o       `Y8bood8P'   o888o   "888" o888o o888o  `V88V"V8P'  `Y8bod8P'
#  888       .o..P'
# o888o      `Y8P'

class pythonGithub(Step):
	'download all python projects form google bigquery, which commit count more than 3000'

	REQUIRE = ()

	PREFIX = 'https://api.github.com/repos/'
	PRELEN = len(PREFIX)

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		data = [json.loads(line) for line in open(path)]
		self.data = [d['url'][self.PRELEN:] for d in data if 'url' in d and d['url'].startswith(self.PREFIX)]
		return True

	def generate(self):
		raise RuntimeError, 'All the data should be download from google bigquery by yourself!'


#                                   o8o                         .        ooooo              .o88o.                  .o
#                                   `"'                       .o8        `888'              888 `"                o888
# oo.ooooo.  oooo d8b  .ooooo.     oooo  .ooooo.   .ooooo.  .o888oo       888  ooo. .oo.   o888oo   .ooooo.        888
#  888' `88b `888""8P d88' `88b    `888 d88' `88b d88' `"Y8   888         888  `888P"Y88b   888    d88' `88b       888
#  888   888  888     888   888     888 888ooo888 888         888         888   888   888   888    888   888       888
#  888   888  888     888   888     888 888    .o 888   .o8   888 .       888   888   888   888    888   888       888
#  888bod8P' d888b    `Y8bod8P'     888 `Y8bod8P' `Y8bod8P'   "888"      o888o o888o o888o o888o   `Y8bod8P'      o888o
#  888                              888
# o888o                         .o. 88P
#                               `Y888P

# 过滤travis build成功并使用了nosetests的项目
class projectInfo_1(Step):
	'gether project information'

	REQUIRE = 'pythonGithub', 'filter'

	TRAVIS_BUILD_PATH = 'travisBuild'

	nosetestsRe = re.compile(r'^nosetests\b', re.I)
	pipUseMirrorsRe = re.compile(r'\bpip\s+install\b.*--use-mirrors\b', re.I)

	def _load(self):
		module = self.__module__.rpartition('.')[-1]
		self.data = self.projects[self.flow.project]
		self.builds = utils.readData('data/%s/%s/%s.json' % (module, self.TRAVIS_BUILD_PATH, self.flow.project))
		self.git = 'https://github.com/%s/%s.git' % (self.data['author'], self.flow.project)

	def load(self):
		module = self.__module__.rpartition('.')[-1]
		path = 'data/%s/pythonProjects.json' % module
		self.projects = utils.readData(path)
		self.flow.project and self._load()
		return True

	def _filterTravisYAML(self, project, travisYAML):
		return 'nosetests' in travisYAML

	def _filterTravisBuild(self, project, builds):
		self.buildsNum[project] = len(builds)
		if len(builds) < 0: return None
		path = 'data/%s/%s/%s.json' % (self.__module__.rpartition('.')[-1], self.TRAVIS_BUILD_PATH, project.rpartition('/')[-1])
		utils.saveData(path, builds)
		return builds

	def _prepareTravis(self, project, build, config, cache):
		if cache:
			return cache

		config = copy.deepcopy(config)

		if config.get('language', 'python') != 'python':
			# print project, build['commit'], '.travis.yml language error:', config['language']
			return None
		config['language'] = 'python'

		if 'python' not in config:
			config['python'] = '2.7'
		elif not isinstance(config['python'], list):
			p = str(config['python'])
			if not p.startswith('2.') and not p.startswith('3.'):
				print project, build['commit'], '.travis.yml python config error:', config['python']
				config['python'] = '2.7'
		else:
			ps2_7 = [p for p in config['python'] if str(p).startswith('2.7')]
			ps2 = [p for p in config['python'] if str(p).startswith('2.')]
			ps3 = [p for p in config['python'] if str(p).startswith('3.')]
			if ps2_7:
				config['python'] = ps2_7[0]
			elif ps2:
				config['python'] = ps2[0]
			elif ps3:
				config['python'] = ps3[0]
			else:
				print project, build['commit'], '.travis.yml python config error:', config['python']
				config['python'] = '2.7'

		if 'os' in config and config['os'] != 'linux' \
			and (not isinstance(config['os'], list) or 'linux' not in config['os']):
			print project, build['commit'], '.travis.yml os config error:', config['os']
		config['os'] = 'linux'

		if 'dist' in config and config['dist'] != 'trusty' \
			and (not isinstance(config['dist'], list) or 'trusty' not in config['dist']):
			print project, build['commit'], '.travis.yml dist config error:', config['dist']
		config['dist'] = 'trusty'

		config.pop('sudo', None)
		config.pop('branches', None)
		config.pop('notifications', None)
		config.pop('before_cache', None)
		config.pop('cache', None)
		config.pop('after_success', None)
		config.pop('after_failure', None)
		config.pop('before_deploy', None)
		config.pop('deploy', None)
		config.pop('after_deploy', None)
		config.pop('after_script', None)

		def _checkListConfig(name):
			if name not in config or config[name] is None:
				config[name] = []
			elif isinstance(config[name], basestring):
				config[name] = [config[name]]
			elif not isinstance(config[name], list):
				print project, build['commit'], '.travis.yml %s config error:' % name, config[name]
				config[name] = []

		_checkListConfig('before_install')
		config['before_install'].append('sudo add-apt-repository -y ppa:ubuntu-toolchain-r/test')
		config['before_install'].append('sudo apt-get update -qq')

		_checkListConfig('install')
		for i, s in enumerate(config['install']):
			if self.pipUseMirrorsRe.search(s):
				config['install'][i] = s.replace('--use-mirrors', '')
		config['install'].append('sudo apt-get install -qq g++-4.8')
		config['install'].append('export CXX="g++-4.8"')
		config['install'].append('pip install nose-cprof')
		config['install'].append('pip install properform')

		_checkListConfig('script')
		for i, s in enumerate(config['script']):
			if self.nosetestsRe.search(s):
				prepared = True
				config['script'][i] += ' --with-cprofile --cprofile-stats-erase --cprofile-stats-file=$PROFILE_PATH/python_profile'
				break
		else:
			prepared = False
			config['script'].append('echo TODO: Cannot find nosetests.')

		if prepared:
			_checkListConfig('after_success')
			config['after_success'].append('python -m properform Push $HOST_IP:15554 $PROFILE_KEY $PROFILE_PATH/python_profile')

		return prepared, config

	def generate(self):
		self.buildsNum = {}
		projects = self.flow.pythonGithub.data
		projects = self.flow.filter.LanguageRate(projects, 'Python', 0.8)
		projects = self.flow.filter.TravisCI(projects)
		projects = self.flow.filter.TravisYAML(projects,
			filter = self._filterTravisYAML)
		projects = self.flow.filter.TravisBuild(projects,
			prepare = self._prepareTravis,
			filterYAML = self._filterTravisYAML,
			filterBuilds = self._filterTravisBuild)
		self.projects = {p: {'author': a} for a, _, p in set((p.rpartition('/') for p in projects))}
		assert len(self.projects) == len(projects)

		print "the mean value of builds numbers", sum(self.buildsNum.itervalues()) / len(self.buildsNum)
		print "the median value of builds number", sorted(self.buildsNum.itervalues())[len(self.buildsNum) / 2]

		path = 'data/%s/pythonProjects.json' % self.__module__.rpartition('.')[-1]
		utils.saveData(path, self.projects)
		self.flow.project and self._load()

		return True


#                                   o8o                         .        ooooo              .o88o.                  .oooo.
#                                   `"'                       .o8        `888'              888 `"                .dP""Y88b
# oo.ooooo.  oooo d8b  .ooooo.     oooo  .ooooo.   .ooooo.  .o888oo       888  ooo. .oo.   o888oo   .ooooo.             ]8P'
#  888' `88b `888""8P d88' `88b    `888 d88' `88b d88' `"Y8   888         888  `888P"Y88b   888    d88' `88b          .d8P'
#  888   888  888     888   888     888 888ooo888 888         888         888   888   888   888    888   888        .dP'
#  888   888  888     888   888     888 888    .o 888   .o8   888 .       888   888   888   888    888   888      .oP     .o
#  888bod8P' d888b    `Y8bod8P'     888 `Y8bod8P' `Y8bod8P'   "888"      o888o o888o o888o o888o   `Y8bod8P'      8888888888
#  888                              888
# o888o                         .o. 88P
#                               `Y888P

# 过滤travis build成功的项目，给内存泄露分析用
class projectInfo(Step):
	'gether project information for memory leak'

	REQUIRE = 'pythonGithub', 'filter'

	TRAVIS_BUILD_PATH = 'travisBuild2'

	def get_repo(self, project):
		data = self.projects[project]
		return 'https://github.com/%s/%s.git' % (data['author'], project)

	def get_builds_path(self, project):
		module = self.__module__.rpartition('.')[-1]
		return 'data/%s/%s/%s.json' % (module, self.TRAVIS_BUILD_PATH, project)

	def get_builds(self, project):
		data = self.projects[project]
		path = self.get_builds_path(project)
		builds = utils.readData(path)
		if [b for b in builds if 'travis_yml' not in b]:
			builds = self.flow.filter.PrepareTravis('%s/%s' % (data['author'], project), builds, self._prepareTravis, None)
			utils.saveData(path, builds)
		# else: return ()
		return builds

	def _load(self):
		self.data = self.projects[self.flow.project]
		self.builds = self.get_builds(self.flow.project)
		self.git = self.get_repo(self.flow.project)

	def load(self):
		module = self.__module__.rpartition('.')[-1]
		path = 'data/%s/pythonProjects2.json' % module
		self.projects = utils.readData(path)
		self.flow.project and self._load()
		return True

	def _filterTravisBuild(self, project, builds):
		self.buildsNum[project] = len(builds)
		if len(builds) < 0: return None
		path = self.get_builds_path(project.rpartition('/')[-1])
		utils.saveData(path, builds)
		return builds

	def _prepareTravis(self, project, build, config, cache):
		if cache:
			return cache

		config = copy.deepcopy(config)

		if config.get('language', 'python') != 'python':
			# print project, build['commit'], '.travis.yml language error:', config['language']
			return None
		config['language'] = 'python'

		if 'python' not in config:
			config['python'] = '3.6'
		elif not isinstance(config['python'], list):
			p = str(config['python'])
			if not p.startswith('2.') and not p.startswith('3.'):
				print project, build['commit'], '.travis.yml python config error:', config['python']
				config['python'] = '3.6'
		else:
			ps3_6 = [p for p in config['python'] if str(p).startswith('3.6')]
			ps3 = [p for p in config['python'] if str(p).startswith('3.')]
			ps2_7 = [p for p in config['python'] if str(p).startswith('2.7')]
			ps2 = [p for p in config['python'] if str(p).startswith('2.')]
			if ps3_6:
				config['python'] = '3.6'
			elif ps2_7:
				config['python'] = '2.7'
			elif ps3:
				config['python'] = ps3[0]
			elif ps2:
				print project, build['commit'], '.travis.yml python use 2.7 instead of:', config['python']
				config['python'] = '2.7'
			else:
				print project, build['commit'], '.travis.yml python config error:', config['python']
				config['python'] = '3.6'

		if 'os' in config and config['os'] != 'linux' \
			and (not isinstance(config['os'], list) or 'linux' not in config['os']):
			print project, build['commit'], '.travis.yml os config error:', config['os']
		config['os'] = 'linux'

		if 'dist' in config and config['dist'] == 'xenial':
			pass
		else:
			if 'dist' in config and config['dist'] != 'trusty' \
				and (not isinstance(config['dist'], list) or 'trusty' not in config['dist']):
				print project, build['commit'], '.travis.yml dist config error:', config['dist']
			config['dist'] = 'trusty'

		config.pop('sudo', None)
		config.pop('branches', None)
		config.pop('notifications', None)
		config.pop('before_cache', None)
		config.pop('cache', None)
		config.pop('after_success', None)
		config.pop('after_failure', None)
		config.pop('before_deploy', None)
		config.pop('deploy', None)
		config.pop('after_deploy', None)
		config.pop('after_script', None)

		return True, config

	def generate(self):
		self.buildsNum = {}
		projects = self.flow.pythonGithub.data
		projects = self.flow.filter.LanguageRate(projects, 'Python', 0.8)
		projects = self.flow.filter.TravisCI(projects)
		projects = self.flow.filter.TravisYAML(projects)
		projects = self.flow.filter.TravisBuild(projects, filterBuilds = self._filterTravisBuild)
		self.projects = {p: {'author': a} for a, _, p in set((p.rpartition('/') for p in projects))}

		print "the mean value of builds numbers", sum(self.buildsNum.itervalues()) / len(self.buildsNum)
		print "the median value of builds number", sorted(self.buildsNum.itervalues())[len(self.buildsNum) / 2]

		path = 'data/%s/pythonProjects2.json' % self.__module__.rpartition('.')[-1]
		utils.saveData(path, self.projects)
		self.flow.project and self._load()

		return True


#          oooo                                        ooooooooo.                          o8o                         .        ooooo              .o88o.
#          `888                                        `888   `Y88.                        `"'                       .o8        `888'              888 `"
#  .oooo.o  888 .oo.    .ooooo.  oooo oooo    ooo       888   .d88' oooo d8b  .ooooo.     oooo  .ooooo.   .ooooo.  .o888oo       888  ooo. .oo.   o888oo   .ooooo.
# d88(  "8  888P"Y88b  d88' `88b  `88. `88.  .8'        888ooo88P'  `888""8P d88' `88b    `888 d88' `88b d88' `"Y8   888         888  `888P"Y88b   888    d88' `88b
# `"Y88b.   888   888  888   888   `88..]88..8'         888          888     888   888     888 888ooo888 888         888         888   888   888   888    888   888
# o.  )88b  888   888  888   888    `888'`888'          888          888     888   888     888 888    .o 888   .o8   888 .       888   888   888   888    888   888
# 8""888P' o888o o888o `Y8bod8P'     `8'  `8'          o888o        d888b    `Y8bod8P'     888 `Y8bod8P' `Y8bod8P'   "888"      o888o o888o o888o o888o   `Y8bod8P'
#                                                                                          888
#                                                                                      .o. 88P
#                                                                                      `Y888P

# 显示项目信息
class showProjectInfo(Step):
	'show project information'

	REQUIRE = 'projectInfo',

	def load(self):
		return False

	def generate(self):
		if self.flow.project:
			travis_yml = set((tuple(b['travis_yml']) for b in self.flow.projectInfo.builds))
			print 'Project:', self.flow.project
			print 'Git:', self.flow.projectInfo.git
			print 'Build:', len(self.flow.projectInfo.builds)
			print '.travis.yml:', len(travis_yml), len(filter(lambda (t, _): t, travis_yml))
		else:
			module = self.__module__.rpartition('.')[-1]
			projects = []
			for project, data in self.flow.projectInfo.projects.iteritems():
				builds = utils.readData('data/%s/%s/%s.json' % (module, self.flow.projectInfo.TRAVIS_BUILD_PATH, project))
				travis_yml = set((tuple(b['travis_yml']) for b in builds))
				travis_ok = len(filter(lambda (t, _): t, travis_yml))
				if len(travis_yml) != travis_ok:
					continue
				projects.append((
					project,
					'https://github.com/%s/%s.git' % (data['author'], project),
					len(builds),
					(len(travis_yml), travis_ok),
				))

			projects.sort(key = lambda (_, __, builds, ___): builds)
			for i, (project, git, builds, travis_yml) in enumerate(projects):
				print i + 1, project, git, builds, travis_yml

			print 'mean:', reduce(lambda s, p: s + p[2], projects[:-1], 0) / (len(projects) - 1)
			print 'media:', projects[len(projects) / 2][2]

		return False



#     .                                oooo
#   .o8                                `888
# .o888oo oooo d8b  .oooo.    .ooooo.   888  oooo   .oooo.o
#   888   `888""8P `P  )88b  d88' `"Y8  888 .8P'   d88(  "8
#   888    888      .oP"888  888        888888.    `"Y88b.
#   888 .  888     d8(  888  888   .o8  888 `88b.  o.  )88b
#   "888" d888b    `Y888""8o `Y8bod8P' o888o o888o 8""888P'

class tracks(Step):
	'run properform on localhost and extract profile files'

	REQUIRE = ()

	def load(self):
		with os.popen('python -m properform Touch 127.0.0.1:15554') as proc:
			if proc.read().strip() == 'OK':
				return True
		return False

	def generate(self):
		raise RuntimeError, 'The properform service on 127.0.0.1:15554 should be run by yourself!'

	def exist(self, profileKey):
		path = 'data/%s/profile/%s.prof' % (self.flow.project, profileKey)
		return os.path.isfile(path)

	def extract(self, profileKey):
		path = 'data/%s/profile' % self.flow.project
		not os.path.isdir(path) and os.makedirs(path)
		cmd = 'python -m properform Pull 127.0.0.1:15554 %s data/%s/profile/%s.prof' % (profileKey, self.flow.project, profileKey)
		assert os.system(cmd) == 0


#  .o8                    o8o  oooo        .o8       ooooo   ooooo  o8o               .
# "888                    `"'  `888       "888       `888'   `888'  `"'             .o8
#  888oooo.  oooo  oooo  oooo   888   .oooo888        888     888  oooo   .oooo.o .o888oo  .ooooo.  oooo d8b oooo    ooo
#  d88' `88b `888  `888  `888   888  d88' `888        888ooooo888  `888  d88(  "8   888   d88' `88b `888""8P  `88.  .8'
#  888   888  888   888   888   888  888   888        888     888   888  `"Y88b.    888   888   888  888       `88..8'
#  888   888  888   888   888   888  888   888        888     888   888  o.  )88b   888 . 888   888  888        `888'
#  `Y8bod8P'  `V88V"V8P' o888o o888o `Y8bod88P"      o888o   o888o o888o 8""888P'   "888" `Y8bod8P' d888b        .8'
#                                                                                                            .o..P'
#                                                                                                            `Y8P'

# 下载project中每个build的profile数据，每个build有5个profile
# 只保留有profile的记录在buildHistory中
class buildHistory(Step):
	'download profile of build history'

	REQUIRE = 'projectInfo',

	def load(self):
		data = {}
		for build in self.flow.projectInfo.builds:
			path = "data/%s/profile/%s_%s_%%d.prof" % (self.flow.project, self.flow.project, build["commit"][:10])
			for index in xrange(self.flow.REPEAT_TEST):
				profileFile = path % index
				if utils.getFileSize(profileFile) > 10:
					data[build['commit']] = build
					break
		if data:
			self.data = data
			return True
		return False

	def generate(self):
		return False


#                                                    oooo                      oooo                                               o8o                         .
#                                                    `888                      `888                                               `"'                       .o8
# ooo. .oo.  .oo.    .ooooo.  ooo. .oo.  .oo.         888   .ooooo.   .oooo.    888  oooo       oo.ooooo.  oooo d8b  .ooooo.     oooo  .ooooo.   .ooooo.  .o888oo  .oooo.o
# `888P"Y88bP"Y88b  d88' `88b `888P"Y88bP"Y88b        888  d88' `88b `P  )88b   888 .8P'         888' `88b `888""8P d88' `88b    `888 d88' `88b d88' `"Y8   888   d88(  "8
#  888   888   888  888ooo888  888   888   888        888  888ooo888  .oP"888   888888.          888   888  888     888   888     888 888ooo888 888         888   `"Y88b.
#  888   888   888  888    .o  888   888   888        888  888    .o d8(  888   888 `88b.        888   888  888     888   888     888 888    .o 888   .o8   888 . o.  )88b
# o888o o888o o888o `Y8bod8P' o888o o888o o888o      o888o `Y8bod8P' `Y888""8o o888o o888o       888bod8P' d888b    `Y8bod8P'     888 `Y8bod8P' `Y8bod8P'   "888" 8""888P'
#                                                                                                888                              888
#                                                                                               o888o                         .o. 88P
#                                                                                                                             `Y888P

class MemLeakProjects(Step):
	'memory leak projects'

	REQUIRE = 'projectInfo',

	LOG_PATH = os.path.abspath('data/log/runMemLeak')
	DATA_PATH = os.path.abspath('data/memleak')

	exitRe = re.compile(r'.*Done\. Your build exited with (?P<code>[^\.]+)\..*', re.S)

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		self.data = utils.readData(path)
		return True

	def get_path(self, project):
		return os.path.join(self.DATA_PATH, '%s_%s.json' % (project, self.data[project]['commit']))

	def iter_projects(self):
		for project in self.data:
			item = self.data[project]
			yield project, item['size'], os.path.join(self.DATA_PATH, '%s_%s.json' % (project, item['commit'])), item['status']

	def generate(self):
		data = {}

		for project in self.flow.projectInfo.projects:
			builds = self.flow.projectInfo.get_builds(project)
			if not builds: continue

			success_builds = set()
			for build in builds:
				commit = build['commit']
				log_path = os.path.join(self.LOG_PATH, '%s_%s.txt' % (project, commit))
				while os.path.isfile(log_path):
					log = subprocess.check_output(('tail', log_path)).strip()
					if log.endswith('Your build has been stopped.'):
						status = ['failed', 'Your build has been stopped.']
						break
					m = self.exitRe.match(log)
					if m:
						status = ['exit', m.group('code')]
						break
					status = ['failed', [l.strip() for l in log.split('\n') if l.strip()][-1]]
					break

				if status == ['exit', '0']:
					success_builds.add(commit)

				path = os.path.join(self.DATA_PATH, '%s_%s.json' % (project, commit))
				if os.path.isfile(path):
					assert project not in data
					data[project] = {
						'size': os.path.getsize(path),
						'commit': commit,
						'status': status,
					}

			if project not in data and success_builds:
				data[project] = {
					'size': 0,
					'commit': None,
					'status': ['exit', '0'],
				}

		cls = self.__class__
		path = 'data/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		utils.saveData(path, data)
		self.data = data

		return True


# oooooooooooo ooooooo  ooooo ooooooooooooo ooooooooo.         .o.            ooooo ooooo      ooo oooooooooooo   .oooooo.
# `888'     `8  `8888    d8'  8'   888   `8 `888   `Y88.      .888.           `888' `888b.     `8' `888'     `8  d8P'  `Y8b
#  888            Y888..8P         888       888   .d88'     .8"888.           888   8 `88b.    8   888         888      888
#  888oooo8        `8888'          888       888ooo88P'     .8' `888.          888   8   `88b.  8   888oooo8    888      888
#  888    "       .8PY888.         888       888`88b.      .88ooo8888.         888   8     `88b.8   888    "    888      888
#  888       o   d8'  `888b        888       888  `88b.   .8'     `888.        888   8       `888   888         `88b    d88'
# o888ooooood8 o888o  o88888o     o888o     o888o  o888o o88o     o8888o      o888o o8o        `8  o888o         `Y8bood8P'

class ProjectsExtraInfo(Step):
	'projects extra info'

	REQUIRE = 'projectInfo',

	def load(self):
		cls = self.__class__
		path = 'data/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		self.data = utils.readData(path)
		return True

	def generate(self):
		data = {}
		projects = self.flow.projectInfo.projects
		print '- Fetching %d projects extra info...' % len(projects)
		for project in projects:
			author = projects[project]['author']
			url = "https://api.github.com/repos/%s/%s?access_token=b2706f7f013684027c42808422053d28cba74264" % (author, project)
			project_info = utils.readURL('ProjectInfo/%s_%s' % (author, project), url)
			project_info = project_info and json.loads(project_info)
			if not project_info:
				print '    %d/%d loading data from %s: no project info' % (len(data), len(projects), url)
				continue
			if 'stargazers_count' not in project_info:
				print '    %d/%d extra info error %s: no "stargazers_count" in %s' % (len(data), len(projects), url, project_info)
				continue
			if 'created_at' not in project_info:
				print '    %d/%d extra info error %s: no "created_at" in %s' % (len(data), len(projects), url, project_info)
				continue
			if 'updated_at' not in project_info and 'pushed_at' not in project_info:
				print '    %d/%d extra info error %s: no "updated_at" or "pushed_at" in %s' % (len(data), len(projects), url, project_info)
				continue

			UTC_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
			start_time = time.mktime(time.strptime(project_info['created_at'], UTC_FORMAT))
			if 'updated_at' in project_info:
				end_time = time.mktime(time.strptime(project_info['updated_at'], UTC_FORMAT))
			else:
				end_time = 0
			if 'pushed_at' in project_info:
				push_time = time.mktime(time.strptime(project_info['pushed_at'], UTC_FORMAT))
				if push_time > end_time:
					end_time = push_time
			age = float(end_time - start_time) / 3600 / 24 / 365

			print '    %d/%d fetch %s/%s stars(%s) age(%.1f year)' % (len(data), len(projects), author, project, project_info['stargazers_count'], age)
			data[project] = {
				'stars': project_info['stargazers_count'],
				'age': age,
			}

		assert len(data) == len(projects)

		cls = self.__class__
		path = 'data/%s/%s.json' % (cls.__module__.rpartition('.')[-1], cls.__name__)
		utils.saveData(path, data)
		self.data = data

		return True
