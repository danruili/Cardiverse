from importlib import import_module
import traceback
from typing import List, Tuple
import os
import threading
import logging
from GameEngine.utils.base_agents import RandomAgent
import random

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

def test_env_worker(module_path: str,
                    error_log_path: str,
                    game_log_path: str,
                    seed: int,
                    num_players: int,
                    result,
                    enable_info: bool = True
                    ) -> None:
    """
    Worker function to run the test environment in a separate thread.
    """
    if seed is None:
        seed = random.randint(0, 1000)
    class_name = "LLMGame"

    # clear the game log file content
    with open(game_log_path, 'w') as game_log_file:
        pass

    try:
        # Dynamically load the environment class
        envClass = getattr(import_module(module_path), class_name)
        env = envClass({'game_num_players': num_players,
                        'seed': seed, 'log_path': game_log_path, 'enable_info': enable_info})
        num_players = env.num_players # use the number of players from the environment since input can be None
        env.set_agents([RandomAgent() for _ in range(num_players)])
        env.run()
        logging.info(f"Testing passed {module_path}.")

        # Clear the error file content (can be done once at the start of your program)
        with open(error_log_path, 'w'):
            pass  # Just open and close the file to clear contents

        result.append(True)
    except Exception as e:
        logging.error(f"Error occurred during testing the environment {module_path}.")

        # Get the formatted exception traceback
        exception_trace = traceback.format_exc()

        # Write the traceback to the error log file safely
        with open(error_log_path, 'w') as error_file:
            error_file.write(exception_trace)

        result.append(False)

def test_env(module_path: str, 
             bug_log_path: str, 
             game_log_path: str, 
             seed: int = 42,
             timeout: int = 10,
             num_players: int = None,
             enable_info: bool = True
             ) -> bool:
    """
    Test the environment with a random agent.
    Test will be considered failed if the environment throws an exception or times out.
    """
    result = []
    worker_thread = StoppableThread(
        target=test_env_worker, 
        args=(module_path, bug_log_path, game_log_path, seed, num_players, result, enable_info))
    worker_thread.start()
    worker_thread.join(timeout=timeout)

    # remove all handlers in this logger
    logger_name = game_log_path.split('/')[-1].split('.')[0]
    logger = logging.getLogger(logger_name)
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)

    # If the thread is still alive, it means it timed out
    if worker_thread.is_alive():
        # terminate the thread
        worker_thread.stop()
        logging.error(f"Execution timed out for {module_path}.")
        # try read game log file
        with open(game_log_path, 'r', encoding='utf-8') as game_log_file:
            game_log = game_log_file.read()
            game_log_items = game_log.split('\n')
            character_limit = 6000
            last_n_logs = []
            # repeat adding the last element to the front until the total character length of the last_n_logs is more than 1000 or game log items are exhausted
            while len(''.join(last_n_logs)) < character_limit and game_log_items:
                last_n_logs.insert(0, game_log_items.pop())
            with open(bug_log_path, 'w', encoding='utf-8') as error_file:
                error_msg = f"Execution timed out. Probably an infinite loop, infinite reshuffling the deck, or lack of game ending condition. Please infer from the last few turns of game play (if successfully generated) below:\n```\n{'\n'.join(last_n_logs)}\n```"
                error_file.write(error_msg)
        return False
    else:
        # end the thread
        worker_thread.join()
        return result[0] if result else False
    

def test_with_repetition(
        temp_dir: str,
        game_name: str,
        temp_id: str = "",
        repetition: int = 5,
        num_players: int = None,
        timeout: int = 10,
        enable_info: bool = True,
        ) -> Tuple[bool, List[str], float, int]:
    """
    Test the game code with multiple repetitions.
    Args:
        temp_dir (str): The directory where temporary files will be stored.
        game_name (str): The name of the game to be tested.
        temp_id (str): A temporary identifier for the test run.
        repetition (int, optional): The number of times to repeat the test. Defaults to 5.
        num_players (int, optional): The number of players in the game. Defaults to 2.
    Returns:
        Tuple[bool, List[str], float, int]: A tuple containing:
            - A boolean indicating if the test was successful.
            - A list of paths to the gameplay log files.
            - A list of paths to the error log files.
            - An integer representing the number of repetitions completed.
    """
    temp_module_prefix = temp_dir.replace('/', '.').replace('\\', '.')
    gameplay_log_files = []
    error_log_files = []
    for i in range(repetition):
        play_log_path = os.path.join(temp_dir, f"{game_name}_{temp_id}_{i}.log")
        error_log_path = os.path.join(temp_dir, f"{game_name}_{temp_id}_{i}_error.log")
        gameplay_log_files.append(play_log_path)
        error_log_files.append(error_log_path)
        module_path = f"{temp_module_prefix}.{game_name}_{temp_id}" if temp_id != "" else f"{temp_module_prefix}.{game_name}"
        is_success = test_env(
            module_path, 
            error_log_path,
            play_log_path,
            seed=random.randint(0, 1000),
            num_players=num_players,
            timeout=timeout,
            enable_info=enable_info
            )
        if not is_success:
            break
    return is_success, gameplay_log_files, error_log_files, len(gameplay_log_files) 
    
