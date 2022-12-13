@ECHO OFF
SET PYTHONPATH=%~dp0;%~dp0\..\webserver\properform\python

CALL python -B -m stepflow -s MemLeakStaticCircles

PAUSE
