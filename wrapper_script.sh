#!/bin/bash

# Start the first process
python3 main.py &

export LONG_TASK=YES

# Start the second process
python3 main.py task &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?