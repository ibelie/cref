#-*- coding: utf-8 -*-
# Copyright 2017-2018 ibelie, Chen Jie, Joungtao. All rights reserved.
# Use of this source code is governed by The MIT License
# that can be found in the LICENSE file.

from step import MetaStep
from flow import run
from python import EXT
import common

# Parse command line arguments
import argparse

parser = argparse.ArgumentParser(description = 'performance step flow')

parser.add_argument('-s', dest = 'step', type = str, choices = MetaStep.Steps.keys(), help = 'step name')
parser.add_argument('-p', dest = 'project', type = str, help = 'project name')

args = parser.parse_args()
# print(args)
run(EXT, args.step, args.project)
