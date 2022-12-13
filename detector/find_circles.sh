DETECTOR_PATH=$(cd `dirname $0`; pwd)
export PYTHONPATH="$DETECTOR_PATH"

$1 -B $DETECTOR_PATH/find_circles.py $2 $3 $4 $5 $6 $7
