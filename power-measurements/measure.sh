#!/bin/bash

OUTPUT="measurements.csv"
PINPOINT="./pinpoint/build/pinpoint"

print_measurements() {
    # Das -- ist nach Pinpoint wichtig, da sonst --dry-run alles zu kaputt macht!
    #                                                           rapl                                   time                      sonst nichts
    ($PINPOINT_PATH -r -c -- $@  2>&1 >>output.txt | awk '{ if (/rapl:|mcp:/){print $1, "," , $6} else if (/time/) {print $1, "," , $7} else next}'; echo $@) | tr '\n' ',' >> $OUTPUT
    echo "" >> $OUTPUT
}

measure_over_time() {
    rm -r data-new # make the job download the data before, otherwise the experiment would be less repeatable
    $PINPOINT -c -e MCP2 -- $@ 2>&1 | while IFS= read -r line; do
        timestamp=$(date +%s.%N)
        echo "$timestamp $line" >> $OUTPUT
    done
}

print_header() {
    # do not care about aliases
    ($PINPOINT_PATH -l | grep -v "\->" | awk '/rapl:|mcp:/{print $1,",σ("$1")"}'; echo "time"; echo "σ(time)"; echo "program") | tr '\n' ',' > $OUTPUT
    echo "" >> $OUTPUT
}

# check wether the MCP device is there
if $PINPOINT -l | grep -q MCP2; then
    echo "MCP is connected"
else 
    echo "MCP is not connected, I am giving up. Are you using sudo?"
    exit 1
fi


measure_over_time sleep 10
# measure_over_time .venv/bin/python3.12 fmnist.py
# print_measurements python3 ./python/simulation.py ./input/readinput.txt ./input/writeinput.txt --dry-run
# print_measurements python3 ./python/simulation.py ./input/readinput.txt ./input/writeinput.txt
# print_measurements sleep 1
# print_measurements ./C/Main ./input/readinput.txt ./input/writeinput.txt
# print_measurements ./C/Main ./input/readinput.txt ./input/writeinput.txt --dry-run

echo "Done!"