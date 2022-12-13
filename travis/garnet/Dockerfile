# Copyright 2018-2020 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

# This is the default docker image of Travis CI, and also for go, jvm, node_js, php, python, ruby
FROM travisci/ci-garnet:packer-1515445631-7dfb2e1

# User for Travis CI
USER travis

RUN bash -lc "rvm use 2.3.4 --default"

# Build travis-build
RUN mkdir -p /home/travis/.travis
RUN git clone https://github.com/travis-ci/travis-build.git /home/travis/.travis/travis-build

WORKDIR /home/travis/.travis/travis-build

RUN bash -lc "bundle install"
RUN bash -lc "bundler add travis"
RUN bash -lc "bundler binstubs travis"

RUN echo "#!/bin/bash\n/home/travis/.travis/travis-build/bin/travis compile \$*" > /home/travis/travis_compile && chmod +x /home/travis/travis_compile

RUN mkdir /home/travis/.properform

COPY pytracemalloc /home/travis/.properform/pytracemalloc
COPY Python-2.7.14.tgz /home/travis/.properform/Python-2.7.14.tgz
COPY tracemalloc.2.7.14.patch /home/travis/.properform/tracemalloc.2.7.14.patch

RUN set -x \
 && cd /home/travis/.properform \
 && tar xzvf Python-2.7.14.tgz \
 && cd Python-2.7.14 \
 && patch -p 1 < ../tracemalloc.2.7.14.patch \
 && ./configure --prefix=/opt/python/2.7.14 --enable-unicode=ucs4 --with-ensurepip=install \
 && make \
 && make altinstall \
 && virtualenv -p /opt/python/2.7.14/bin/python /home/travis/virtualenv/python2.7.14 \
 && /home/travis/virtualenv/python2.7.14/bin/python -m pip install /home/travis/.properform/pytracemalloc

COPY properform /home/travis/.properform/properform
COPY inject_properform.py /home/travis/.properform/inject.py

USER root

RUN set -x \
 && rm -rf /home/travis/.properform/pytracemalloc \
 && rm /home/travis/.properform/Python-2.7.14.tgz \
 && rm /home/travis/.properform/tracemalloc.2.7.14.patch \
 && chown -R travis:travis /home/travis/.properform
