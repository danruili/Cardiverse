import json
import os
from typing import Dict, get_args
import logging

from GameplayAI.agents import HeuristicEnsembleAgent
from GameplayAI.utils.policy_design import LLMPolicy, PolicyMethod
from Utils.LLMHandler import LLMHandler
from GameplayAI.utils.get_obs_dict_explain import get_obs_dict_explain
from GameEngine.utils.game_run import make_env
from GameEngine.utils.base_agents import RandomAgent
from GameEngine.env import LLMGameStateEncoder


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_agent(
    game_description_file_path: str,
    game_code_file_path: str,
    policy_folder_path: str = None,
    llm_handler: LLMHandler = None,
    policy_num: int = 4,
) -> Dict[str, HeuristicEnsembleAgent]:
    """
    Create an AI player for a card game
    """
    # read game description
    if not os.path.exists(game_description_file_path):
        alt_ext = ".md" if game_description_file_path.endswith(".txt") else ".txt"
        game_description_file_path = os.path.splitext(game_description_file_path)[0] + alt_ext
        if not os.path.exists(game_description_file_path):
            raise ValueError("Game description file must be .txt or .md")
    with open(game_description_file_path, 'r', encoding='utf-8') as f:
        game_description = f.read()

    # create policy folder if not exists
    if not os.path.exists(policy_folder_path):
        os.makedirs(policy_folder_path)

    # propose policy
    if not os.path.exists(os.path.join(policy_folder_path, 'policy_text.json')):
        policy = LLMPolicy(game_description, item_num=policy_num, llm_handler=llm_handler)
        policy.design_policy()
        policy.save(os.path.join(policy_folder_path, 'policy_text.json'))
    else:
        policy = LLMPolicy.load(os.path.join(policy_folder_path, 'policy_text.json'))

    # create state dictionary explanation
    example_state_dict, state_dict_explanation = get_obs_dict_explain(game_code_file_path, llm_handler)
    input_description = f"Example: \n{json.dumps(example_state_dict, cls=LLMGameStateEncoder)}\n\nExplanation: \n{json.dumps(state_dict_explanation)}"
    
    # policy to code
    result = {}
    policy_method_list = list(get_args(PolicyMethod))
    for prompt_method in policy_method_list:
        policy_file_path = os.path.join(policy_folder_path, f'policy_{prompt_method}.json')

        # create one if not exists
        if not os.path.exists(policy_file_path):
            policy_list = policy.get_policy(prompt_method)
            agent = HeuristicEnsembleAgent(
                game_description, 
                input_description, 
                policy_list,
                llm_handler=llm_handler,
                enable_fix=True
                )
            agent.to_json_file(policy_file_path)
        else:
            agent = HeuristicEnsembleAgent.from_json_file(policy_file_path, enable_fix=True, llm_handler=llm_handler)

        # use self-play to test the agent, fix bugs if necessary
        fixed_policy_file_path = os.path.join(policy_folder_path, f'policy_{prompt_method}_fixed.json')
        if not os.path.exists(fixed_policy_file_path):
            logger.info(f"Testing and fixing the agent in {prompt_method} method...")
            agent = fix_by_playing(game_code_file_path, agent)
            agent.to_json_file(fixed_policy_file_path)
        else:
            agent = HeuristicEnsembleAgent.from_json_file(fixed_policy_file_path, enable_fix=True, llm_handler=llm_handler)
        result[prompt_method] = agent

    return result


def fix_by_playing(
    game_code_path: str, 
    agent: HeuristicEnsembleAgent,
    repetition: int = 10,
) -> HeuristicEnsembleAgent:
    """
    Refine the agent by playing against random agents
    """
    for _ in range(repetition):
        env = make_env(game_code_path)
        env.set_agents([RandomAgent() for _ in range(env.num_players-1)] + [agent])
        game_state, observation = env.reset()
        game_state, observation, _ = env.step(game_state, observation, None)

        while (not game_state['common']['is_over']):
            game_state, observation, _ = env.step(game_state, observation, None)

    return agent

