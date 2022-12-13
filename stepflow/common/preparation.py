#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from stepflow.step import Step
from stepflow import utils
from ruamel import yaml
import shutil
import json
import time
import os

GROUP = 'Preparation'


#  .o88o.  o8o  oooo      .
#  888 `"  `"'  `888    .o8
# o888oo  oooo   888  .o888oo  .ooooo.  oooo d8b
#  888    `888   888    888   d88' `88b `888""8P
#  888     888   888    888   888ooo888  888
#  888     888   888    888 . 888    .o  888
# o888o   o888o o888o   "888" `Y8bod8P' d888b

# 不保存数据，仅提供过滤github项目的方法
class filter(Step):
	'filter github projects'

	REQUIRE = ()

	def load(self): return True

	def generate(self): return True

	@staticmethod
	def LanguageRate(projects, language, rate):
		result = []
		print '- Filtering %d projects with %s rate > %s...' % (len(projects), language, rate)
		for i, p in enumerate(projects):
			url = "https://api.github.com/repos/%s/languages?access_token=b2706f7f013684027c42808422053d28cba74264" % p
			languageRate = utils.readURL('LanguageRate/%s' % p.replace('/', '_'), url)
			languageRate = languageRate and json.loads(languageRate)
			if not languageRate:
				print '    %d/%d loading data from %s: no language rate' % (len(result), i + 1, url)
				continue
			if language not in languageRate:
				print '    %d/%d filter language rate from %s: no "%s" in %s' % (len(result), i + 1, url, language, languageRate)
				continue
			t = sum(languageRate.itervalues())
			if t <= 0:
				print '    %d/%d filter language rate from %s: total %s of %s' % (len(result), i + 1, url, t, languageRate)
				continue
			r = float(languageRate[language]) / t
			if r < rate:
				print '    %d/%d filter language rate from %s: %s rate %s < %s' % (len(result), i + 1, url, language, r, rate)
			else:
				result.append(p)
				print '    %d/%d filter language rate from %s: %s rate %s > %s' % (len(result), i + 1, url, language, r, rate)

		print '  Get %d projects with %s rate > %s' % (len(result), language, rate)
		return result

	@staticmethod
	def General(projects, stargazers, updated):
		result = []
		UTC_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
		updated_str = time.strftime(UTC_FORMAT, time.localtime(updated))
		print '- Filtering %d projects with stargazers > %s and updated after %s...' % (len(projects), stargazers, updated_str)
		for i, p in enumerate(projects):
			url = "https://api.github.com/search/repositories?q=repo:%s&access_token=b2706f7f013684027c42808422053d28cba74264" % p
			general = utils.readURL('General/%s' % p.replace('/', '_'), url)
			general = general and json.loads(general)
			if not general or 'errors' in general:
				print '    %d/%d loading data from %s: no general information' % (len(result), i + 1, url)
				continue
			if not general.get('items') or general.get('total_count') != 1:
				print '    %d/%d filter general information from %s: total %s != 1 of %s' % (len(result), i + 1, url, general.get('total_count'), general)
				continue
			general = general['items'][0]
			if general['full_name'] != p:
				print '    %d/%d filter general information from %s: full name "%s" != "%s" of %s' % (len(result), i + 1, url, general['full_name'], p, general)
				continue
			if general['stargazers_count'] < stargazers:
				print '    %d/%d filter general information from %s: stargazers_count %s < %s' % (len(result), i + 1, url, general['stargazers_count'], stargazers)
				continue
			updated_timestamp = time.mktime(time.strptime(general['updated_at'], UTC_FORMAT))
			if updated_timestamp < updated:
				print '    %d/%d filter general information from %s: update at %s before %s' % (len(result), i + 1, url, general['updated_at'], updated_str)
			else:
				result.append(p)
				print '    %d/%d filter general information from %s: update at %s after %s' % (len(result), i + 1, url, general['updated_at'], updated_str)

		print '  Get %d projects with stargazers > %s and updated after %s' % (len(result), stargazers, updated_str)
		return result

	@staticmethod
	def TravisCI(projects):
		result = []
		print '- Filtering %d projects with Travis-CI...' % len(projects)
		for i, p in enumerate(projects):
			url = "https://api.travis-ci.org/repos/%s" % p
			content = utils.readURL('TravisCI/%s' % p.replace('/', '_'), url)
			if content:
				json.loads(content)
				result.append(p)
				print '    %d/%d loading data from %s: true' % (len(result), i + 1, url)
			else:
				print '    %d/%d loading data from %s: false' % (len(result), i + 1, url)

		print '  Get %d projects with Travis-CI' % len(result)
		return result

	@staticmethod
	def TravisYAML(projects, filter = None):
		result = []
		print '- Filtering %d projects with .travis.yml ...' % len(projects)
		for i, p in enumerate(projects):
			url = "https://raw.githubusercontent.com/%s/master/.travis.yml" % p
			travisYAML = utils.readURL('TravisYAML/%s' % p.replace('/', '_'), url)
			if not travisYAML or "404: Not Found" in travisYAML:
				print '    %d/%d loading data from %s: not found' % (len(result), i + 1, url)
			elif filter and not filter(p, travisYAML):
				print '    %d/%d filter .travis.yml from %s: false' % (len(result), i + 1, url)
			else:
				result.append(p)
				print '    %d/%d filter .travis.yml from %s: true' % (len(result), i + 1, url)

		print '  Get %d projects with .travis.yml' % len(result)
		return result

	@staticmethod
	def _LoadTravisYAML(project, builds):
		p_ = project.replace('/', '_')
		path = 'data/cache/PrepareTravis/%s/index.json' % p_
		if not os.path.isfile(path):
			return None, None

		indexContent = utils.readData(path)
		if set(indexContent) != set((b['commit'] for b in builds)):
			return None, None

		cacheContent = {}
		for cmt in set(indexContent.itervalues()):
			path = 'data/cache/PrepareTravis/%s/%s.travis.yml' % (p_, cmt)
			if not cmt:
				continue
			elif not os.path.isfile(path):
				return None, None
			with open(path, 'r') as f:
				cacheContent[cmt] = f.read()

		return indexContent, cacheContent

	@staticmethod
	def _FetchTravisYAML(project, builds):
		p_ = project.partition('/')[0]
		path = 'data/gitRepo/%s' % p_
		cmd = 'git clone https://github.com/%s.git %s' % (project, path)
		dirname = os.path.dirname(path)
		not os.path.isdir(dirname) and os.mkdir(dirname)
		if os.path.isfile(path):
			os.remove(path)
		elif os.path.isdir(path):
			shutil.rmtree(path)
		assert os.system(cmd) == 0

		logs = set()
		with os.popen('git --git-dir=%s/.git log --pretty=format:"%%H"' % path) as proc:
			line = proc.readline()
			while line:
				logs.add(line.strip())
				line = proc.readline()

		indexContent = {}
		cacheContent = {}
		for i, build in enumerate(builds):
			commit = build['commit']
			if commit not in logs:
				indexContent[commit] = None
				print '        %d/%d fetch no git log of %s[%s]' % (len(indexContent), i + 1, project, commit)
				continue

			with os.popen('git --git-dir=%s/.git show %s:.travis.yml' % (path, commit)) as proc:
				content = proc.read().strip()
				while content and '\n' not in content and ':' not in content:
					if 'not exist' in content:
						content = None
						break
					with os.popen('git --git-dir=%s/.git show %s:%s' % (path, commit, content.strip())) as proc:
						content = proc.read().strip()

				if not content:
					indexContent[commit] = None
					print '        %d/%d fetch no .travis.yml of %s[%s]' % (len(indexContent), i + 1, project, commit)
				elif content in cacheContent:
					cmt = cacheContent[content]
					indexContent[commit] = cmt
					print '        %d/%d fetch same .travis.yml of %s[%s] with %s' % (len(indexContent), i + 1, project, commit, cmt)
				else:
					cmt = commit[:10]
					indexContent[commit] = cmt
					cacheContent[content] = cmt
					print '        %d/%d fetch new .travis.yml of %s[%s]' % (len(indexContent), i + 1, project, commit)

		path = 'data/cache/PrepareTravis/%s' % p_
		not os.path.isdir(path) and os.makedirs(path)
		for content, commit in cacheContent.iteritems():
			path = 'data/cache/PrepareTravis/%s/%s.travis.yml' % (p_, commit)
			with open(path, 'w') as f:
				f.write(content)
		cacheContent = {v: k for k, v in cacheContent.iteritems()}

		path = 'data/cache/PrepareTravis/%s/index.json' % p_
		utils.saveData(path, indexContent)

		return indexContent, cacheContent

	@staticmethod
	def PrepareTravis(project, builds, prepare, filter):
		cls = globals()['filter']
		commits = {b['commit']: b for b in builds}
		assert len(set(b['commit'][:10] for b in builds)) == len(commits)
		indexContent, cacheContent = cls._LoadTravisYAML(project, builds)
		if not indexContent:
			indexContent, cacheContent = cls._FetchTravisYAML(project, builds)

		indexYAML = 0
		buildYAML = {}
		cacheYAML = []
		map(lambda build: build.pop('travis_yml', None), builds)
		for i, (commit, cmt) in enumerate(sorted(indexContent.iteritems())):
			if not cmt:
				print '        %d/%d prepare no .travis.yml of %s[%s]' % (indexYAML, i + 1, project, commit)
				continue

			build = commits[commit]
			content = cacheContent[cmt]
			if filter and not filter(project, content):
				print '        %d/%d prepare filter .travis.yml of %s[%s]' % (indexYAML, i + 1, project, commit)
				continue

			try:
				config = yaml.load(content, Loader = yaml.RoundTripLoader)
			except:
				if commit[:10] == cmt:
					print '        %d/%d prepare .travis.yml parse error of %s[%s]' % (indexYAML, i + 1, project, commit)
				continue

			if prepare:
				for c, y in cacheYAML:
					if y == config:
						cache = c
						break
				else:
					cache = None
				prepared = prepare(project, build, config, cache)
				if not prepared:
					print '        %d/%d prepare ignore .travis.yml of %s[%s]' % (indexYAML, i + 1, project, commit)
					continue
				elif prepared != cache:
					cacheYAML.append((prepared, config))
				prepared, config = prepared
			else:
				prepared = True

			for c, (p, y) in buildYAML.iteritems():
				if p == prepared and y == config:
					indexYAML += 1
					build['travis_yml'] = (p, c)
					print '        %d/%d prepare same .travis.yml of %s with %s[%s]' % (indexYAML, i + 1, commit, project, c)
					break
			else:
				indexYAML += 1
				buildYAML[commit] = (prepared, config)
				build['travis_yml'] = (prepared, commit)
				print '        %d/%d prepare new .travis.yml of %s[%s]' % (indexYAML, i + 1, project, commit)

		path = 'data/prepare/%s' % project.rpartition('/')[-1]
		not os.path.isdir(path) and os.makedirs(path)
		for commit, (_, config) in buildYAML.iteritems():
			with open('%s/%s.travis.yml' % (path, commit[:10]), 'w') as f:
				yaml.dump(config, f, Dumper = yaml.RoundTripDumper)

		return [b for b in builds if 'travis_yml' in b]

	@staticmethod
	def TravisBuild(projects, prepare = None, filterYAML = None, filterBuilds = None):
		cls = globals()['filter']
		result = []
		print '- Filtering %d projects with successful builds and prepare .travis.yml ...' % len(projects)
		for i, p in enumerate(projects):
			urlBase = "https://api.travis-ci.org/repos/%s/builds" % p
			page = utils.readURL('TravisBuild/%s_0' % p.replace('/', '_'), urlBase)
			page = page and json.loads(page)
			if not page:
				print '    %d/%d loading data from %s: no page' % (len(result), i + 1, urlBase)
				continue

			builds = []
			head = page[0]['number']
			tail = page[-1]['number']
			while head != tail:
				builds.extend(page)
				url = "%s?after_number=%s" % (urlBase, tail)
				page = utils.readURL('TravisBuild/%s_%s' % (p.replace('/', '_'), tail), url)
				page = page and json.loads(page)
				if not page: break
				head, tail = tail, page[-1]['number']

			if not builds:
				print '    %d/%d loading data from %s: no builds' % (len(result), i + 1, urlBase)
				continue

			builds = [b for b in builds if b['result'] == 0 and b['branch'] == 'master']
			if not builds:
				print '    %d/%d filter builds of %s: no successful builds' % (len(result), i + 1, p)
				continue

			if prepare:
				print '    %d/%d preparing builds of %s ...' % (len(result), i + 1, p)
				builds = cls.PrepareTravis(p, builds, prepare, filterYAML)
			if not builds:
				print '    %d/%d prepare builds of %s: no available builds' % (len(result), i + 1, p)
				continue

			if filterBuilds:
				builds = filterBuilds(p, builds)
			if not builds:
				print '    %d/%d filter builds of %s: false' % (len(result), i + 1, p)
				continue

			result.append(p)
			print '    %d/%d filter %d builds of %s: true' % (len(result), i + 1, len(builds), p)

		print '  Prepare %d projects with successful builds' % len(result)
		return result
