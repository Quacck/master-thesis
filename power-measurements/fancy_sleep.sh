#!/bin/bash

echo $(date +%s.%N), Start > events.csv
sleep 60
echo $(date +%s.%N), End >> events.csv
