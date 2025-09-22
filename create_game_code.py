"""
Game Code Creation Pipeline Script

This script processes game descriptions to generate corresponding game code.

Installation:
```bash
pip install openai retrying scipy anthropic json5 numpy scikit-learn python-dotenv
```

Usage:
    python code_gen.py --configs <path_to_config_file> [--test_run]

Arguments:
    --configs: Path to the configuration file (required).
    --test_run: If set, only the first task will be executed for testing (optional).

"""

from GameCode.pipeline import create_with_repetition
import os
import logging
import argparse
import yaml
from typing import List, Dict
from itertools import zip_longest
from multiprocessing import Process, Queue

def tasks_for_external_data(
        game_desc_dir: str,
        game_code_dir: str,
        temp_dir: str,
        configs: Dict,
    ) -> List[Dict]:  

    tasks = []

    # find all game descriptions in the directory
    for game_desc_file in os.listdir(game_desc_dir):
        game_desc_file_path = os.path.join(game_desc_dir, game_desc_file)
        game_name = game_desc_file.split('.')[0]
        game_code_path = os.path.join(game_code_dir, f"{game_name}.py")
        if os.path.exists(game_code_path):
            continue
        with open(game_desc_file_path, 'r', encoding="utf-8") as f:
            game_description = f.read()

        tasks.append({
            "game_name": game_name,
            "game_description_or_file_path": game_description,
            "game_code_path": game_code_path,
            "temp_dir": temp_dir,
            "configs": configs
        })
    return tasks

def worker_process(task: Dict, result_queue: Queue):
    """Worker process that handles a single task"""
    try:
        is_success, code, performance = create_with_repetition(task)
        logging.info(f"Game code creation for {performance['game_name']} finished successfully")
        logging.info(f"Performance Info: {performance}")
        result_queue.put({
            'success': is_success,
            'game_name': performance['game_name'],
            'performance': performance
        })
    except Exception as e:
        logging.error(f"Failed to create game {task['game_name']}: {str(e)}")
        result_queue.put({
            'success': False,
            'game_name': task['game_name'],
            'error': str(e)
        })

def process_batch(tasks: List[Dict], timeout: int) -> None:
    """Process a batch of tasks in parallel"""
    if not tasks:
        return
    
    # Filter out None values that might come from zip_longest
    tasks = [t for t in tasks if t is not None]
    
    processes = []
    result_queue = Queue()
    
    # Start a process for each task in the batch
    for task in tasks:
        p = Process(target=worker_process, args=(task, result_queue))
        p.start()
        processes.append((p, task['game_name']))
        
    # Wait for all processes to complete or timeout
    results = []
    for _ in range(len(tasks)):
        try:
            result = result_queue.get(timeout=timeout)
            results.append(result)
        except Exception as e:
            logging.error(f"Error getting result: {str(e)}")
    
    # Cleanup processes
    for p, game_name in processes:
        if p.is_alive():
            p.terminate()
            p.join(timeout=1)
            if p.is_alive():
                p.kill()
                logging.error(f"Had to forcefully terminate process for game {game_name}")
        p.join()
        p.close()
    
    # Clean up the queue
    result_queue.close()
    result_queue.join_thread()

def grouper(iterable, n):
    """Group iterable into batches of size n"""
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=None)

def setup_logging(log_file_path: str):
    """Setup logging configuration"""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("root").setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger("root")
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run game code creation pipeline.')
    parser.add_argument('--configs', type=str, help='Path to the configuration file')
    parser.add_argument('--test_run', action='store_true', help='Whether to only run the first task for testing')
    args = parser.parse_args()

    # Load configuration from yaml file
    with open(args.configs, 'r') as f:
        config = yaml.safe_load(f)

    # Parse configuration
    output_dir = config.get('output_dir', os.path.dirname(args.configs)) # use the parent directory of config file as the working directory
    game_desc_dir = config.get('game_desc_dir', None)
    if game_desc_dir is None:
        raise ValueError("game_desc_dir are required in the configuration")

    temp_dir = config.get('temp_dir', None)
    log_file_path = config.get('log_file_path', None)
    if temp_dir is None or temp_dir == 'default':
        temp_dir = os.path.join(output_dir, 'temp')
        config['temp_dir'] = temp_dir
    if log_file_path is None or log_file_path == 'default':
        log_file_path = os.path.join(output_dir, f"process.log")
        config['log_file_path'] = log_file_path

    batch_size = config.get('batch_size', 1)
    timeout = config.get('timeout', 3600)
    game_code_dir = os.path.join(output_dir, 'game')

    # make directories if not exist
    if not os.path.exists(game_code_dir):
        os.makedirs(game_code_dir)
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Setup logging
    setup_logging(log_file_path)

    # Create tasks
    tasks = tasks_for_external_data(
        game_desc_dir,
        game_code_dir,
        temp_dir,
        configs=config.get('pipeline', {})
    )

    # Run only first batch if test run
    if args.test_run:
        task = tasks[0]
        logging.info("Running in test mode, only the first task will be executed.")
        create_with_repetition(task)

    else:
        # Group tasks into batches
        batches = list(grouper(tasks, batch_size))
        # Process each batch
        for i, batch in enumerate(batches, 1):
            logging.info(f"Processing batch {i} of {len(batches)}")
            process_batch(batch, timeout)
            logging.info(f"Completed batch {i}")