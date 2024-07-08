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

touch ${OUTPUT}

# 
# for (( index=0; index<${REPETITIONS}; index++ )); do
#     run_experiment ".venv/bin/python3.12 roberta_only_imports.py" "imports_only"
# done

for (( index=0; index<${REPETITIONS}; index++ )); do
    run_experiment "./fancy_sleep.sh" 'sleep' # well this is crazy, if we use single quotes, its always taken as a literal string
done

# for (( index=0; index<${REPETITIONS}; index++ )); do
#     rm -r roberta-data
#     rm -r checkpoints
#     run_experiment ".venv/bin/python3.12 roberta.py --no-resume_from_checkpoint" "roberta_full"
# done
# 
# # Run roberta.py partially, data is already downloaded and we have a first checkpoint to continue from
# for (( index=0; index<${REPETITIONS}; index++ )); do
#     rm -r "checkpoints"
#     mkdir "checkpoints"
#     cp -r checkpoints-saved/checkpoint-12 checkpoints
#     run_experiment ".venv/bin/python3.12 roberta.py --resume_from_checkpoint" "roberta_partial"
# done
# 
# # Overhead experiments
# STOP=2
# 
# for (( index=0; index<${REPETITIONS}; index++ )); do
#     rm -r roberta-data
#     rm -r checkpoints
#     run_experiment ".venv/bin/python3.12 roberta.py --stop_after_epoch ${STOP}" "roberta_stop_epoch_${STOP}"
# done
# 
# 
# for (( index=0; index<${REPETITIONS}; index++ )); do
#     rm -r roberta-data
#     rm -r checkpoints
#     run_experiment ".venv/bin/python3.12 roberta.py --stop_after_epochs_save ${STOP}" "roberta_stop_saved_${STOP}"
# done

cpupower frequency-set --min ${MINFREQ} &>/dev/null
cpupower frequency-set --max ${MAXFREQ} &>/dev/null

echo "Done!"