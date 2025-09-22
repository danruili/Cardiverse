from Utils.LLMHandler import LLMHandler
import json
from GameplayAI.utils.extract import extract_from_language
from retrying import retry
from GameEngine.utils.game_run import make_env
from GameEngine.utils.base_agents import RandomAgent
from typing import Any
from GameEngine.env import LLMCard, LLMGameStateEncoder

dict_explain_prompt = """
You are a computer game programmer that explains the meaning of a game state dictionary.

# Game code
```python
{code_placeholder}
```

# Game state dictionary
```json
{state_placeholder}
```

Please explain the meaning of each field in the dictionary. You should respond with a JSON object as below. You can skip the fields that are too duplicative.

Example Output:
```json
{
    "<field1 name>": "the meaning and format of field1.",
    "<field2 name>": "the meaning and format of field2.",
    ...
}
```
"""

@retry(stop_max_attempt_number=3)
def explain_obs_dict(game_code: str, state: dict, llm_handler: LLMHandler) -> dict:
    """
    Explain the meaning of a game state dictionary
    """
    prompt = dict_explain_prompt.replace("{code_placeholder}", game_code) \
        .replace("{state_placeholder}", json.dumps(state, indent=4, cls=LLMGameStateEncoder))
    # print(prompt)
    result = llm_handler.chat(prompt)
    json_result = extract_from_language(result, 'json')
    return json.loads(json_result)

def get_example_dict(
    game_code_path: str, 
) -> dict:
    """
    Set up the environment and extract the observation dictionary at 5th step
    """
    env = make_env(game_code_path)
    env.set_agents([RandomAgent() for _ in range(env.num_players)])
    game_state, observation = env.reset()
    game_state, observation, _ = env.step(game_state, observation, None)
    round_num = 0

    while (not game_state['common']['is_over']) and \
        (round_num < 5):
        game_state, observation, _ = env.step(game_state, observation, None)
        round_num += 1

    # go through the observation and convert LLMCard objects to dictionaries
    def convert_to_dict(obj: Any) -> Any:
        if isinstance(obj, LLMCard):
            return obj.__json__()
        if isinstance(obj, list):
            return [convert_to_dict(item) for item in obj]
        if isinstance(obj, dict):
            return {k: convert_to_dict(v) for k, v in obj.items()}
        return obj
    
    # go through the observation and convert set objects to lists
    def convert_set_to_list(obj: Any) -> Any:
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, list):
            return [convert_set_to_list(item) for item in obj]
        if isinstance(obj, dict):
            return {k: convert_set_to_list(v) for k, v in obj.items()}
        return obj
    
    observation = convert_set_to_list(observation)
    observation = convert_to_dict(observation)
    
    return observation

def get_obs_dict_explain(
        game_code_path: str,
        llm_handler: LLMHandler,
) -> tuple[dict, dict]:
    """
    Get the explanation of the observation dictionary
    """
    example_dict = get_example_dict(game_code_path)
    with open(game_code_path, 'r', encoding='utf-8') as f:
        game_code = f.read()
    return example_dict, explain_obs_dict(game_code, example_dict, llm_handler)


# Example usage
if __name__ == "__main__":
    llm_handler = LLMHandler()
    game_code_path = "GameLib/manual-0-30/boat-house-rum.py"
    example_dict, explanation = get_obs_dict_explain(game_code_path, llm_handler)
    print(json.dumps(example_dict, indent=4))
    print(json.dumps(explanation, indent=4))
        