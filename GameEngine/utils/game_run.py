from importlib import import_module
from GameEngine.env import LLMGame
import numpy as np
from tqdm import tqdm
import os
from GameEngine.utils.code import wrap_env_code
import uuid


def make_env(
        game_code_path: str, 
        game_log_path: str = None,
        seed: int = None,
        uuid_str: str = None,
        ) -> LLMGame:
    # assign an uuid to the game if not provided
    if uuid_str is None:
        uuid_str = str(uuid.uuid4())
    
    # read the game code
    with open(game_code_path, 'r', encoding='utf-8') as f:
        game_code = f.read()

    # attach the engine code to the game code
    game_code = wrap_env_code(game_code)

    # write the game code to a temp file
    temp_folder = 'temp'
    temp_python_path = os.path.join(temp_folder, f"temp_{uuid_str}.py")
    os.makedirs(os.path.dirname(temp_python_path), exist_ok=True)
    with open(temp_python_path, 'w', encoding='utf-8') as f:
        f.write(game_code)

    temp_folder_dot_path = temp_folder.replace("\\", ".").replace("/", ".")
    module_path = f"{temp_folder_dot_path}.temp_{uuid_str}"

    class_name = "LLMGame"
    envClass = getattr(import_module(module_path), class_name)
    if game_log_path is None:
        env: LLMGame = envClass({'seed': seed})
    else:
        env: LLMGame = envClass({'seed': seed, 'log_path': game_log_path})

    # delete the temp file
    os.remove(temp_python_path)

    return env


def tournament(
        env:LLMGame,
        repeat: int = 1000,
    ) -> np.array:
    payoffs = None
    for i in range(repeat):
        game_state, observation = env.reset()
        try:
            game_state, observation, _ = env.step(game_state, observation, None)
            while (not game_state['common']['is_over']):
                game_state, observation, _ = env.step(game_state, observation, None)
            _payoffs = game_state['payoffs']
            if payoffs is None:
                payoffs = _payoffs
            else:
                payoffs = np.vstack((payoffs, _payoffs))
        except Exception as e:
            # print(e)
            pass
    return payoffs


