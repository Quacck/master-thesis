#!/bin/bash

PINPOINT_PATH=$(realpath "./pinpoint/build/pinpoint")
PROGRAM_PATH=$(realpath ".venv/bin/python3.12 fmnist.py")

# check wether the MCP device is there
if $PINPOINT_PATH -l | grep -q MCP2; then
    echo "MCP is connected"
else 
    echo "MCP is not connected, I am giving up. Are you using sudo?"
    exit 1
fi

OUTPUT="measurements.csv"
touch $OUTPUT

# Run fmnist.py completly, downloading all data and doing the whole training from scratch
for (( index=0; index<=10; index++ )); do
    rm -r data-new # make the job download the data before, otherwise the experiment would be less repeatable

    start=$(date +%s.%N)
    $PINPOINT_PATH -c -e MCP2 -o $OUTPUT -- $PROGRAM_PATH
    end=$(date +%s.%N)

    echo "$start" >> $OUTPUT
    echo "$end" >> $OUTPUT

    OUTPUT_DIRECTORY="measurements_fmnist_full_$(date +%m%d%H%M%S)"

    mkdir $OUTPUT_DIRECTORY

    mv $OUTPUT $OUTPUT_DIRECTORY
    mv "events.csv" $OUTPUT_DIRECTORY

    sleep 60
done

echo "Done!"