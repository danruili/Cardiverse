from GameplayAI.agents import HeuristicEnsembleAgent
from GameEngine.utils.base_agents import RandomAgent
from typing import List, Literal, Union
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
These are Gameplay AI settings for our work and its ablations
- 'ours': our full method.
- 'NoRefl': our method without policy reflection
- 'NoOpt': No Optimization. It retains the full set of heuristics generated before the augmentation step but skips the optimization phase, using all heuristics equally without selection.
- 'NoEns': No Ensemble. It generates a single comprehensive heuristic function instead of ensembling multiple LLM-generated strategies.
- 'NoEns+': Concatenated Strategy. It creates a single heuristic function by concatenating all generated text policies.
"""

EnsembleSettings = Literal['ours', 'NoRefl', 'NoOpt']
NonEnsembleSettings = Literal['NoEns', 'NoEns+']
AgentSettings = Union[EnsembleSettings, NonEnsembleSettings]


def load_agent(
        game_directory: str,
        method: AgentSettings = 'ours',
        training_assistant: bool = False
    ) -> HeuristicEnsembleAgent:
    if method in ['ours', 'NoRefl', 'NoOpt']:
        policy_file_path = os.path.join(game_directory, "ai", "policy_text.json")
        return load_ensemble_agent(policy_file_path, method, training_assistant)
    elif method in ['NoEns', 'NoEns+']:
        return load_non_ensemble_agent(game_directory, method)
    else:
        raise ValueError(f"Invalid method: {method}")

def load_non_ensemble_agent(
        game_directory: str,
        method: NonEnsembleSettings = 'NoEns',
    ) -> HeuristicEnsembleAgent:

    if method == "NoEns":
        policy_file_path = os.path.join(game_directory, "ai", "policy_singular_fixed.json")
    elif method == "NoEns+":
        policy_file_path = os.path.join(game_directory, "ai", "policy_strategy_metric_one_code_fixed.json")
    else:
        raise ValueError(f"Invalid method: {method}")

    # Return RandomAgent if the policy file does not exist
    if not os.path.exists(policy_file_path):
        logger.warning(f"Policy file not found: {policy_file_path}, using RandomAgent instead.")
        return RandomAgent()
    
    with open(policy_file_path, 'r') as f:
        policy_json_object = json.loads(f.read())
    return HeuristicEnsembleAgent.from_json(
        {
            "game_description": policy_json_object["game_description"],
            "input_description": "",
            "policy_list": policy_json_object["policy_list"],
            "code": policy_json_object["code"],
            "flipped_indices": []
        },
    )


def load_ensemble_agent(
    policy_file_path: str,
    method: EnsembleSettings = 'ours',
    training_assistant: bool = False
) -> HeuristicEnsembleAgent:
    """
    Load a ternary agent from a policy file.
    
    Parameters:
    policy_file_path (str): The path to the policy file.
    method (ExpDesign): The method to use for loading the agent. Default is 'ours'.
                        Possible values are 'ours', 'NoOpt', 'NoRefl', and '-ensemble'.
    training_assistant (bool): If True, randomly select a configuration. Default is False.

    Returns:
    HeuristicEnsembleAgent: The loaded ternary agent. If the policy file path is invalid, returns a RandomAgent.
    """
    if not policy_file_path or not os.path.exists(policy_file_path):
        logger.warning(f"Policy file not found: {policy_file_path}, using RandomAgent instead.")
        return RandomAgent()
    
    with open(policy_file_path, 'r') as f:
        policy_json_object = json.loads(f.read())
    
    if "feature_selection" not in policy_json_object:
        logger.warning(f"'feature_selection' not found in {policy_file_path}, using RandomAgent instead.")
        return RandomAgent()
    
    # revert the elements in policy_json_object["feature_selection"]
    policy_json_object["feature_selection"] = policy_json_object["feature_selection"][::-1]

    # collect configs based on the method
    configs = []
    if method in ['ours', 'NoOpt']:
        configs.extend([config for config in policy_json_object["feature_selection"] if config["label"] == 'ours'])
    if method in ['NoRefl']:
        configs.extend([config for config in policy_json_object["feature_selection"] if config["label"] == 'NoRefl'])
        
    if not training_assistant:
        # select the first config (the latest one)
        config = configs[0]
    else:
        # randomly select a config
        import random
        config = random.choice(configs)

    # unpack the config
    model_paths = config["model_file_paths"]
    raw_flipped_indices = config["flipped_indices"]
    raw_selected_indices = config["final_selected_indices"]

    # read all code and policy lists from the model files
    all_codes = []
    all_policies = []
    policy_folder_path = os.path.dirname(policy_file_path)
    model_paths = [os.path.join(policy_folder_path, model_path) for model_path in model_paths]
    for model_file_path in model_paths:
        # replace \\ with / in the model file path
        model_file_path = model_file_path.replace("\\", "/")
        with open(model_file_path, 'r') as f:
            json_object = json.loads(f.read())
        all_codes.extend(json_object["code"])
        all_policies.extend(json_object["policy_list"])

    # extract code and policy lists for the selected features
    if method != "NoOpt":
        code = [all_codes[i] for i in raw_selected_indices]
        flipped_indices = [raw_selected_indices.index(i) for i in raw_flipped_indices if i in raw_selected_indices]
        policy_list = [all_policies[i] for i in raw_selected_indices]
    else:
        code = all_codes
        flipped_indices = raw_flipped_indices
        policy_list = all_policies
    
    return HeuristicEnsembleAgent.from_json(
        {
            "game_description": policy_json_object["game_description"],
            "input_description": "",
            "policy_list": policy_list,
            "code": code,
            "flipped_indices": flipped_indices
        },
    )