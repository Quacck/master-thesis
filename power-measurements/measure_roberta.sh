#!/bin/bash

PINPOINT_PATH=$(realpath "./pinpoint/build/pinpoint")
PROGRAM_PATH=$(realpath ".venv/bin/python3.12 roberta.py")
MINFREQ=$(cpupower frequency-info --hwlimits | sed -n '1d;p' | awk '{print $1}')
MAXFREQ=$(cpupower frequency-info --hwlimits | sed -n '1d;p' | awk '{print $1}')

# check wether the MCP device is there
if $PINPOINT_PATH -l | grep -q MCP2; then
    echo "MCP is connected"
else 
    echo "MCP is not connected, I am giving up. Are you using sudo?"
    exit 1
fi

run_experiment() {
    sleep 10 # hope this returns environment to average state

    start=$(date +%s.%N)
    echo $1
    $PINPOINT_PATH -c -e MCP2 -o ${OUTPUT} -b 30000 -a 30000 -- $1 # Continuously measure, also measure before and after
    end=$(date +%s.%N)

    echo "$start" >> ${OUTPUT}
    echo "$end" >> ${OUTPUT}

    OUTPUT_DIRECTORY=measurements_${2}_$(date +%m%d%H%M%S)

    mkdir ${OUTPUT_DIRECTORY}

    mv ${OUTPUT} ${OUTPUT_DIRECTORY}
    mv "events.csv" ${OUTPUT_DIRECTORY}

    echo Saved to ${OUTPUT_DIRECTORY}
}

OUTPUT="measurements.csv"
REPETITIONS=10

cpupower frequency-set --min ${MAXFREQ} &>/dev/null
cpupower frequency-set --max ${MAXFREQ} &>/dev/null

# We would like to set the clock rates of our gpus: (because otherwise we might be stuck on
# a higher clock rate after executing the program)
# https://developer.nvidia.com/blog/advanced-api-performance-setstablepowerstate/#recommended
# nvidia-smi --query-supported-clocks=timestamp,gpu_name,gpu_uuid,memory,graphics --format=csv
# says I run run my NVIDIA GeForce GTX 1070's Memory @4104, 3902, 810 and 405 MHz
# the compute units can be run fairly freely between 2037 MHz and 140 Mhz
# we WOULD set the clock rates now, if it worked
# "Setting applications clocks is not supported for GPU 00000000:0B:00.0."
# There seems to be an issue in the drivers right now:
# https://github.com/NVIDIA/open-gpu-kernel-modules/issues/483
# as this isn't the focus, we'll skip this step and remember to discuss it later

touch ${OUTPUT}

for (( index=0; index<${REPETITIONS}; index++ )); do
    run_experiment "./fancy_sleep.sh" 'sleep' # well this is crazy, if we use single quotes, its always taken as a literal string
done

# This would be the baseline energy need if we do not stop+resume the ML training
for (( index=0; index<${REPETITIONS}; index++ )); do
    rm -r roberta-data
    rm -r checkpoints
    run_experiment ".venv/bin/python3.12 roberta.py --no-resume_from_checkpoint" "roberta_full"
done

STOP=2

# Measure a stop + resume strategy
for (( index=0; index<${REPETITIONS}; index++ )); do
    rm -r roberta-data
    rm -r checkpoints
    run_experiment ".venv/bin/python3.12 roberta.py --stop_after_epochs_save ${STOP}" "roberta_stop_after_saving_epoch_${STOP}_${index}"

    sleep 120

    run_experiment ".venv/bin/python3.12 roberta.py --resume_from_checkpoint" "roberta_continue_after_saving_${STOP}_${index}"

    sleep 120
done

# Lets also run an experiment where we don't save and then resume, this can probably be derive from the previous experiment, but lets double check that
for (( index=0; index<${REPETITIONS}; index++ )); do
    rm -r roberta-data
    rm -r checkpoints
    run_experiment ".venv/bin/python3.12 roberta.py --stop_after_epoch ${STOP}" "roberta_stop_without_saving_epoch_${STOP}_${index}"

    sleep 120

    run_experiment ".venv/bin/python3.12 roberta.py --resume_from_checkpoint" "roberta_continue_after_not_saving_${STOP}_${index}"

    sleep 120
done

rm -r roberta-data
rm -r checkpoints

# This is just for interest, importing all the modules seems to take quite some time and energy too
# we could use this to later validate the other runs 
for (( index=0; index<${REPETITIONS}; index++ )); do
    run_experiment ".venv/bin/python3.12 roberta_only_imports.py" "imports_only"
done

cpupower frequency-set --min ${MINFREQ} &>/dev/null
cpupower frequency-set --max ${MAXFREQ} &>/dev/null

echo "Done!"