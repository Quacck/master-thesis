#!/bin/bash

PINPOINT_PATH=$(realpath "./pinpoint/build/pinpoint")
PROGRAM_PATH=$(realpath ".venv/bin/python3.12 roberta.py")

# check wether the MCP device is there
if $PINPOINT_PATH -l | grep -q MCP2; then
    echo "MCP is connected"
else 
    echo "MCP is not connected, I am giving up. Are you using sudo?"
    exit 1
fi

OUTPUT="measurements.csv"
REPETITIONS=2

touch ${OUTPUT}
#
# # Run roberta.py completly, downloading all data and doing the whole training from scratch
# for (( index=0; index<${REPETITIONS}; index++ )); do
#     rm -r roberta-data # make the job download the data before, otherwise the experiment would be less repeatable
#     rm -r checkpoints
# 
#     start=$(date +%s.%N)
#     $PINPOINT_PATH -c -e MCP2 -o ${OUTPUT} -- .venv/bin/python3.12 roberta.py --no-resume_from_checkpoint && sleep 10
#     end=$(date +%s.%N)
# 
#     echo "$start" >> ${OUTPUT}
#     echo "$end" >> ${OUTPUT}
# 
#     OUTPUT_DIRECTORY="measurements_roberta_full_$(date +%m%d%H%M%S)"
# 
#     mkdir ${OUTPUT_DIRECTORY}
# 
#     mv ${OUTPUT} ${OUTPUT_DIRECTORY}
#     mv "events.csv" ${OUTPUT_DIRECTORY}
# 
#     sleep 60
# done
# 
# # Run roberta.py partially, data is already downloaded and we have a single checkpoint to continue from
# for (( index=0; index<${REPETITIONS}; index++ )); do
# 
#     rm -r "checkpoints"
#     mkdir "checkpoints"
# 
#     cp -r checkpoints-saved/checkpoint-12 checkpoints
# 
#     start=$(date +%s.%N)
#     $PINPOINT_PATH -c -e MCP2 -o ${OUTPUT} -- .venv/bin/python3.12 roberta.py --resume_from_checkpoint && sleep 10
#     end=$(date +%s.%N)
# 
#     echo "$start" >> ${OUTPUT}
#     echo "$end" >> ${OUTPUT}
# 
#     OUTPUT_DIRECTORY="measurements_roberta_partial_$(date +%m%d%H%M%S)"
# 
#     mkdir ${OUTPUT_DIRECTORY}
# 
#     mv ${OUTPUT} ${OUTPUT_DIRECTORY}
#     mv "events.csv" ${OUTPUT_DIRECTORY}
# 
#     sleep 60
# done

# Overhead experiments

STOP=2

# Run roberta.py completly, downloading all data and doing the whole training from scratch
for (( index=0; index<${REPETITIONS}; index++ )); do
    rm -r roberta-data # make the job download the data before, otherwise the experiment would be less repeatable
    rm -r checkpoints

    start=$(date +%s.%N)
    $PINPOINT_PATH -c -e MCP2 -o ${OUTPUT} -- sleep 30 && .venv/bin/python3.12 roberta.py --stop_after_epoch ${STOP} && sleep 30
    end=$(date +%s.%N)

    echo "$start" >> ${OUTPUT}
    echo "$end" >> ${OUTPUT}

    OUTPUT_DIRECTORY=measurements_roberta_stop_epoch_${STOP}_$(date +%m%d%H%M%S)

    mkdir ${OUTPUT_DIRECTORY}

    mv ${OUTPUT} ${OUTPUT_DIRECTORY}
    mv "events.csv" ${OUTPUT_DIRECTORY}

    sleep 60
done

# Run roberta.py completly, downloading all data and doing the whole training from scratch
for (( index=0; index<${REPETITIONS}; index++ )); do
    rm -r roberta-data # make the job download the data before, otherwise the experiment would be less repeatable
    rm -r checkpoints

    start=$(date +%s.%N)
    $PINPOINT_PATH -c -e MCP2 -o ${OUTPUT} -- sleep 30 && .venv/bin/python3.12 roberta.py --stop_after_epochs_save ${STOP} && sleep 30
    end=$(date +%s.%N)

    echo "$start" >> ${OUTPUT}
    echo "$end" >> ${OUTPUT}

    OUTPUT_DIRECTORY=measurements_roberta_stop_save_${STOP}_$(date +%m%d%H%M%S)

    mkdir ${OUTPUT_DIRECTORY}

    mv ${OUTPUT} ${OUTPUT_DIRECTORY}
    mv "events.csv" ${OUTPUT_DIRECTORY}

    sleep 60
done

echo "Done!"