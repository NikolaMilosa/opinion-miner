import subprocess
import requests
from threading import Thread, Event
import time
import sys
import logging
import json
import matplotlib.pyplot as plt
from queue import Queue
import signal
import communicator
import argparse

def parse():
    parser = argparse.ArgumentParser(description="Script that wraps around local LLM run and a rust binary for fetching blogs")
    parser.add_argument("term", help="The term to search for in scraped blogs")
    parser.add_argument("--model", help="The model to run. The list of supported models can be found on on modelz-llm github: https://github.com/tensorchord/modelz-llm", default="bigscience/bloomz-560m", dest="model")
    parser.add_argument("--bin-path", help="The path to a scraper binary. The default is considered to be the output of cargo build", dest="bin_path", default="./target/debug/opinion-miner")
    parser.add_argument("--use-cpu", help="Wether to use the cpu. Should follow the recommended setting on modelz github", dest="use_cpu", default=False, action='store_true')

    return parser.parse_args()

def get_logger():
    FORMAT = "[%(asctime)s] %(levelname)-8s %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    return logging.getLogger("opinion-logger")

def ignore_sigint():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def run_subprocess(command):
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=sys.stderr, text=True, preexec_fn=ignore_sigint)

def run_api(stop_event, model, use_cpu):
    try:
        command = [ "poetry", "run", "modelz-llm", "-m", model ]
        if use_cpu:
            command += ["--device", "cpu"]
        process = run_subprocess(command)
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        process.terminate()
        process.wait()

def run_cli(stop_event, queue, term):
    command = [ "./target/debug/opinion-miner", "--term", term ]
    process = run_subprocess(command)
    
    # Counter for testing purposes should be removed...
    counter = 10
    while True:
        line = process.stdout.readline()
        if line:
            queue.put(line)
            counter -= 1
        if stop_event.is_set() or counter == 0:
            break
    process.terminate()
    process.wait()


def process_line(line, memory, term, bar, figure, axes, logger):
    parsed = json.loads(line)
    output = communicator.find_sentiment(term, parsed['body_html'])
    decided = 'neutral'
    for sentiment in memory:
        if sentiment in output:
            decided = sentiment
            break
    
    logger.info("Completion returned '%s' and we categorize it as '%s'", output, decided)

    memory[decided] += 1
    for b, count in zip(bar, memory.values()):
        b.set_height(count)

    plt.draw()
    plt.pause(1)

def check_or_build(path, logger):
    try:
        f = open(path)
        logger.info("Found built binary")
        return True
    except FileNotFoundError:
        logger.warning("Binary not found at path. Building...")
        build = subprocess.Popen(["cargo", "build"], stderr=sys.stderr, stdout=subprocess.PIPE)
        if build.wait() != 0:
            logger.error("Build failed...")
            return False
    logger.info("Build success...")
    return True


def main():
    args = parse()
    logger = get_logger()
    if not check_or_build(args.bin_path, logger):
        logger.error("Couldn't build project, exiting...")
        exit(1)

    stop_event = Event()
    logger.info("Spawning api thread with model '%s'...", args.model)
    api_thread = Thread(target=run_api, args=(stop_event, args.model, args.use_cpu))
    api_thread.start()

    # Wait for the API to start
    while True:
        logger.info("Waiting for api to start...")
        time.sleep(1)
        try:
            response = requests.get("http://localhost:8000")
            if response.status_code == 200:
                logger.info("API started!")
                break
        except Exception:
            continue
    
    logger.info("Configuring plot...")
    memory = {
        "really positive": 0,
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "really regative": 0
    }
    colors = ['darkgreen', 'lightgreen', 'gray', 'lightcoral', 'darkred']
    figure, axes = plt.subplots()
    bar = axes.bar(memory.keys(), [0] * len(memory.keys()), color=colors)
    axes.set_title('Sentiment Distribution')
    axes.set_xlabel('Sentiment')
    axes.set_ylabel('Count')

    expected_height = 20

    plt.ylim(0, expected_height)
    plt.yticks(range(0, expected_height + 1, 4))
    plt.ion()
    plt.show()
    plt.draw()
    plt.pause(0.001)

    queue = Queue()

    logger.info("Spawning thread to scrape blogs for search term '%s'...", args.term)
    scrape_thread = Thread(target=run_cli, args=(stop_event, queue, args.term))
    scrape_thread.start()

    while True:
        try:
            line = queue.get()
            process_line(line, memory, args.term, bar, figure, axes, logger)
        except KeyboardInterrupt:
            logger.info("Received interupt...")
            plt.ioff()
            plt.close('all')
            plt.pause(0.01)
            break
    
    logger.info("Stopping threads...")
    stop_event.set()

    api_thread.join()
    scrape_thread.join()
    logger.info("Threads stopped")

if __name__ == "__main__":
    main()
