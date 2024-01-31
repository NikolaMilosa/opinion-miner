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


def process_line(line, bar, ax, fig):
    parsed = json.loads(line)
    ax.set_title(f"Live update: {parsed['id']}")
    plt.draw()
    plt.pause(0.01)

def main():
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
    fig, ax = plt.subplots()
    bar = ax.bar(0,0)
    ax.set_ylim(0, 10)
    ax.set_xlim(-1,1)
    ax.set_title('Live Update: 0')
    plt.ion()
    plt.show()
    plt.draw()

    queue = Queue()

    scrape_thread = Thread(target=run_cli, args=(stop_event, queue))
    scrape_thread.start()

    while True:
        try:
            line = queue.get()
            process_line(line, bar, ax, fig)
        except KeyboardInterrupt:
            logger.info("Received interupt...")
            plt.ioff()
            plt.close('all')
            plt.pause(0.001)
            break
    
    logger.info("Stopping threads...")
    stop_event.set()

    api_thread.join()
    scrape_thread.join()
    logger.info("Threads stopped")

if __name__ == "__main__":
    main()
