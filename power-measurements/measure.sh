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
    $PINPOINT -c -e MCP2 -o $O -- $@ | while IFS= read -r line; do
        timestamp=$(date +%s.%N)
        echo "$timestamp, $line, $@" >> $OUTPUT
    done
}

print_header() {
    # do not care about aliases
    (echo "time"; echo "power"; echo "program") | tr '\n' ',' > $OUTPUT
    echo "" >> $OUTPUT
}

# check wether the MCP device is there
if $PINPOINT -l | grep -q MCP2; then
    echo "MCP is connected"
else 
    echo "MCP is not connected, I am giving up. Are you using sudo?"
    exit 1
fi


# for (( index=0; index<=10; index++ )); do
#         output_file="measurements_sleep_${index}.csv"
#         start=$(date +%s.%N)
#         $PINPOINT -c -e MCP2 -o $output_file -- sleep 60
#         end=$(date +%s.%N)
# 
#         echo "$start" >> $output_file
#         echo "$end" >> $output_file
# done

for (( index=0; index<=3; index++ )); do
        output_file="measurements_fmnist_${index}_new.csv"
        rm -r data-new # make the job download the data before, otherwise the experiment would be less repeatable

        start=$(date +%s.%N)
        $PINPOINT -c -e MCP2 -o $output_file -- .venv/bin/python3.12 fmnist.py
        end=$(date +%s.%N)

        echo "$start" >> $output_file
        echo "$end" >> $output_file

        sleep 30
done

#print_header
# measure_over_time sleep 10
#measure_over_time .venv/bin/python3.12 fmnist.py
# measure_over_time sleep 10

echo "Done!"