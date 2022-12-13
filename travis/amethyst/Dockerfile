# Copyright 2018-2020 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

# This is the docker image of Travis CI for android, erlang, haskell and perl
FROM travisci/ci-amethyst:packer-1513010293-3f2fb39

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
