import logging.handlers
from transformers import AutoModel
from datasets import load_dataset
import torch
from transformers import AutoTokenizer
from typing import Dict, Any
from datasets import Dataset
import evaluate
import numpy as np
from transformers import EvalPrediction
from transformers import AutoModelForSequenceClassification, AutoConfig, TrainerCallback, TrainerState, TrainerControl
from transformers import TrainingArguments, Trainer
import logging
import argparse
import os

def exit_elegantly():
    logging.info(f"Exit")
    logging.shutdown()
    os._exit(0)

class LogEpochCallback(TrainerCallback):
    def on_epoch_end(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        logging.info(f"Epoch {state.epoch} ended. Steps: {state.global_step}")
        if (state.epoch == parser_args.stop_after_epoch):
            exit_elegantly()

    def on_save(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        logging.info(f"Epoch {state.epoch}. Saved. Steps: {state.global_step}")
        if (state.epoch == parser_args.stop_after_epochs_save):
            exit_elegantly()

    def on_train_begin(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        logging.info('Start training')
    
    def on_train_end(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        logging.info('End training')

    def on_evaluate(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        logging.info('Evaluate')


parser = argparse.ArgumentParser(description="Sample ML Program")
parser.add_argument('--resume_from_checkpoint', action=argparse.BooleanOptionalAction, help='Resume from checkpoints')
parser.add_argument('--stop_after_epoch', help='Number of epochs to stop after. Set to (default) of -1 to not stop', type=int, default=-1)
parser.add_argument('--stop_after_epochs_save', help='Stop after some epoch was saved. Set to (default) of -1 to not stop', type=int, default=-1)

parser_args = parser.parse_args()

SEED = 42

logging.basicConfig(filename='events.csv', level=logging.INFO, format='%(created)f, %(message)s')

logging.info('start program')

dataset = load_dataset("ag_news", cache_dir="./roberta-data")

logging.info('after load data')

dataset = dataset.shuffle(SEED)

dataset["train"] = dataset["train"].select(range(400))

subset = dataset["train"].shuffle(SEED).train_test_split(0.1, seed=SEED)
dataset["train"] = subset["train"]
dataset["val"] = subset["test"]

num_labels = len(torch.unique(torch.as_tensor([k["label"] for k in dataset["train"]])))

tokenizer = AutoTokenizer.from_pretrained("distilroberta-base")


def preprocess_function(sample: Dict[str, Any], seq_len: int):
    """
    Function applied to all the examples in the Dataset (individually or in batches).
    It accepts as input a sample as a dictionary and return a new dictionary with the BERT tokens for that sample
    """
    t = tokenizer(
        sample["text"], padding="max_length", truncation=True, max_length=seq_len
    )
    return t


encoded_ds = dataset.map(preprocess_function, fn_kwargs={"seq_len": 256})

BATCH_SIZE = 32
LR = 2e-5
EPOCHS = 5

args = TrainingArguments(
    output_dir="checkpoints",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    learning_rate=LR,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    num_train_epochs=EPOCHS,
)

config = AutoConfig.from_pretrained("distilroberta-base", num_labels=num_labels)
model = AutoModelForSequenceClassification.from_pretrained(
    "distilroberta-base", config=config
)

def compute_metrics(eval_pred: EvalPrediction):
    """Compute metrics at evaluation, return a dictionary string to metric values."""
    import evaluate

    accuracy = evaluate.load("accuracy")
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    return accuracy.compute(predictions=predictions, references=labels)


model = model.to("cuda:0" if torch.cuda.is_available() else "cpu")

trainer = Trainer(
    model,
    args,
    train_dataset=encoded_ds["train"],
    eval_dataset=encoded_ds["val"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[LogEpochCallback()]
)
trainer.train(resume_from_checkpoint=parser_args.resume_from_checkpoint)
trainer.evaluate()

logging.info(f"Exit")
