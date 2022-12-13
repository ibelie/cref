export PYTHONPATH=$(cd `dirname $0`; pwd)
# nohup python2 -B -m stepflow -s MemLeakStatistic </dev/null >log.txt 2>&1 &
# nohup python2 -B -m stepflow -s MemLeakStatistic > log.txt 2>&1 &
python2 -B -m stepflow -s MemLeakStatisticS
