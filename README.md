## Opinion miner based on dev.to

A project in the early stages that uses self-hosted LLM's with [modelz-llm](https://github.com/tensorchord/modelz-llm) and dev.to blogs to mine for opinions about user provided terms.

### Requirements:
1. Rust (and cargo)
2. Python

### Running 
To display help menu 
```bash
python opinion-miner.py --help
```

Basic configuration
```bash
python opinion-miner.py --use-cpu testing --model bigscience/bloomz-1b7
```