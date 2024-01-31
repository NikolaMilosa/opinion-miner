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

def get_logger():
    FORMAT = "[%(asctime)s] %(levelname)-8s %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    return logging.getLogger("opinion-logger")

def ignore_sigint():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def run_subprocess(command):
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=sys.stderr, text=True, preexec_fn=ignore_sigint)

def run_api(stop_event):
    try:
        command = [ "poetry", "run", "modelz-llm", "-m", "bigscience/bloomz-3b", "--device", "cpu" ]
        process = run_subprocess(command)
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        process.terminate()
        process.wait()

def run_cli(stop_event, queue):
    try:
        command = [ "./target/debug/opinion-miner", "--term", "test" ]
        process = run_subprocess(command)
    
        while True:
            line = process.stdout.readline()
            if line:
                queue.put(line)
            if stop_event.is_set():
                break
    except KeyboardInterrupt:
        process.terminate()
        process.wait()


def process_line(line, memory, term, bar, figure, axes):
    parsed = json.loads(line)
    output = communicator.find_sentiment(term, parsed['body_html'])
    memory[output.lower()] += 1
    for b, count in zip(bar, memory.values()):
        b.set_hight(count)

    figure.canvas.draw_idle()
    plt.pause(0.001)

def main():
    # Missing argparse
    # Missing checking if the binary is built and building if needed

    stop_event = Event()
    logger = get_logger()
    logger.info("Spawning api thread...")
    api_thread = Thread(target=run_api, args=(stop_event,))
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
    plt.ion()
    plt.show()
    plt.draw()

    queue = Queue()

    scrape_thread = Thread(target=run_cli, args=(stop_event, queue))
    scrape_thread.start()

    while True:
        try:
            line = queue.get()
            process_line(line, memory, 'test', bar, figure, axes)
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
