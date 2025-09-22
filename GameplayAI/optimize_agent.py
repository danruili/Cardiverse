import json
import os
import numpy as np
from GameplayAI.agents import HeuristicEnsembleAgent
from GameplayAI.utils.max_or_min import max_or_min_by_file_paths
from GameEngine.utils.game_run import make_env, tournament
from Utils.LLMHandler import LLMHandler
from GameplayAI.utils.load_agent import load_ensemble_agent
import multiprocessing as mp
import logging
import argparse


def optimize_weights(
        game_description_path: str,
        game_code_path: str,
        folder_path: str,
        llm_handler: LLMHandler,
        optimize_ablation: bool = False,
    ):
    policy_path = os.path.join(folder_path, "ai", "policy_text.json")

    # our method
    model_file_paths = [os.path.join(folder_path, "ai", "policy_reflect_fixed.json"),
                        os.path.join(folder_path, "ai", "policy_strategy_fixed.json"),
                        os.path.join(folder_path, "ai", "policy_metric_fixed.json")]

    # ablation: no reflection
    model_file_paths2 = [os.path.join(folder_path, "ai", "policy_strategy_fixed.json"),
                         os.path.join(folder_path, "ai", "policy_metric_fixed.json")]

    # min or max
    # is_max = max_or_min_by_file_paths(game_description_path, game_code_path, llm_handler)
    # print(f"winners shall maximize the payoff?: {is_max}")

    is_max = True  # always maximize the payoff

    _optimize_heuristic_selection(game_code_path, policy_path, model_file_paths, label="ours", maximize_obj_func=is_max)
    if optimize_ablation:
        _optimize_heuristic_selection(game_code_path, policy_path, model_file_paths2, label="-reflection", maximize_obj_func=is_max)


def _optimize_heuristic_selection(
        game_code_path,
        policy_path: str, 
        model_file_paths: list[str], 
        test_repeat: int = 400,
        label: str = "",
        maximize_obj_func: bool = True
        ):
    logger = logging.getLogger("optimize_weights")
    logger.info(f"select model feature for {game_code_path} with policy {policy_path}")

    # load policy json object
    with open(policy_path, 'r') as f:
        policy_json_object = json.loads(f.read())

    # load game ai features from all file paths
    feature_list = []
    policy_list = []
    for model_file_path in model_file_paths:
        with open(model_file_path, 'r') as f:
            json_object = json.loads(f.read())
        feature_list.extend(json_object["code"])
        policy_list.extend(json_object["policy_list"])

    # step-wise feature inclusion
    metric_history = []
    best_metric = -1000
    best_config = {"sublist": [], "flipped_indices": []}
    config_history = []
    stop_flag = False
    while not stop_flag:

        configs = []
        included_feature_indices = best_config["sublist"]
        flipped_indices = best_config["flipped_indices"]

        # iterate through all non-included features
        for feature_index, _ in enumerate(feature_list):
            if feature_index in included_feature_indices:
                continue
            sublist = included_feature_indices + [feature_index]
            configs.append({"sublist": sublist, "flipped_indices": flipped_indices})
            configs.append({"sublist": sublist, "flipped_indices": flipped_indices + [feature_index]})
        logger.info(f"Comparing {len(configs)} configurations...")

        with mp.Pool(processes=min(10, mp.cpu_count(), len(configs))) as pool:
            current_metrics = pool.map(
                _worker,
                [{"game_code_path": game_code_path, "policy_path": policy_path, 
                  "model_file_paths": model_file_paths, "config": config, 
                  "test_repeat": test_repeat, "maximize_obj_func": maximize_obj_func} for config in configs]
            )
        
        # find the best config
        current_best_metric = max(current_metrics)
        if current_best_metric > best_metric:
            best_metric = current_best_metric
            best_config = configs[current_metrics.index(current_best_metric)]
            metric_history.append(best_metric)
            config_history.append(best_config)
            logger.info(f"new best metric: {best_metric} for config: {best_config}")
        else:
            stop_flag = True


    # print the feature inclusion history
    logger.info("feature inclusion history:")
    for metric, config in zip(metric_history, config_history):
        logger.info(f"metric: {metric}, config: {config}")

    # update and save the json file
    included_feature_indices = best_config["sublist"]
    flipped_indices = best_config["flipped_indices"]
    if "feature_selection" not in policy_json_object:
        policy_json_object["feature_selection"] = []
    policy_json_object["feature_selection"].append({
        "model_file_paths": [os.path.basename(p) for p in model_file_paths],
        "final_selected_indices": included_feature_indices,
        "metric_history": metric_history,
        "label": label,
        "flipped_indices": flipped_indices,
    })
    with open(policy_path, 'w') as f:
        json.dump(policy_json_object, f, indent=4)


def _test_with_config(
        game_code_path: str,
        policy_path: str, 
        heuristic_paths: list[str], 
        heuristic_selection_config: dict,
        num_test_runs: int = 100,
        maximize_obj_func: bool = True
    ) -> float:
    """
    Tests an ensemble agent configuration in a game environment and returns its win rate.
    This function sets up a game environment, loads policy and heuristic models, constructs an ensemble agent
    based on the provided selection configuration, and evaluates its performance against other agents in a tournament.
    The win rate (or loss rate, if maximize_obj_func is False) of the ensemble agent is returned as the metric.
    Args:
        game_code_path (str): Path to the game code for environment setup.
        policy_path (str): Path to the policy JSON file for the agent.
        heuristic_paths (list[str]): List of file paths to heuristic model JSON files.
        heuristic_selection_config (dict): Configuration dict specifying which heuristics to use and which weights to flip.
            Should contain keys:
                - "sublist": List of indices selecting heuristics.
                - "flipped_indices": List of indices whose weights should be flipped.
        num_test_runs (int, optional): Number of tournament runs to perform. Defaults to 100.
        maximize_obj_func (bool, optional): If True, maximizes win rate; if False, minimizes (for loss rate). Defaults to True.
    Returns:
        float: The win rate (or loss rate) of the ensemble agent over the tournament runs.
    """

    # load environment
    learning_env = make_env(game_code_path)

    # load policy json object
    with open(policy_path, 'r') as f:
        policy_json_object = json.loads(f.read())
    game_description = policy_json_object["game_description"]
    input_description = ""  # TODO: add input description

    # load game ai features from all file paths
    feature_list = []
    policy_list = []
    for model_file_path in heuristic_paths:
        with open(model_file_path, 'r') as f:
            json_object = json.loads(f.read())
        feature_list.extend(json_object["code"])
        policy_list.extend(json_object["policy_list"])

    # unpack config
    sublist = heuristic_selection_config["sublist"]
    flipped_indices = heuristic_selection_config["flipped_indices"]

    # set agent
    ensemble_agent = HeuristicEnsembleAgent(
        code=[feature_list[i] for i in sublist], 
        policy_list=[policy_list[i] for i in sublist],
        game_description=game_description, 
        input_description=input_description,
        enable_fix=False
        )
    # find the items in sublist that are in flipped_indices
    flipped_indices_in_sublist = [i for i in sublist if i in flipped_indices]
    # find the indices of the items in flipped_indices_in_sublist in sublist
    flipped_indices_in_sublist_indices = [sublist.index(i) for i in flipped_indices_in_sublist]
    # flip the weights of the agent
    ensemble_agent.flip_weights(flipped_indices_in_sublist_indices)

    # Set up agents
    learner_index = -1
    learning_env.set_agents(
        [load_ensemble_agent(policy_path, training_assistant=True) for _ in range(learning_env.num_players-1)]
           + [ensemble_agent])

    # run the tournament
    rewards = tournament(learning_env, num_test_runs)  # shape: (num_run, num_players)

    # convert the biggest number in each row to 1, others to 0
    if maximize_obj_func:
        wins = (rewards == rewards.max(axis=1)[:, None]).astype(int)
    else:
        wins = (rewards == rewards.min(axis=1)[:, None]).astype(int)

    # get the win rate means as the metric
    win_means = np.mean(wins, axis=0)
    current_metric = win_means[learner_index]

    # log the results
    logger = logging.getLogger("optimize_weights_runner")
    logger.info(f"feature {sublist} flip {flipped_indices} (win rate): {current_metric}")
    logger.info(f"feature {sublist} flip {flipped_indices} (reward): {np.mean(rewards, axis=0)}")

    return current_metric

# test all configs
def _worker(config_pack: dict):
    return _test_with_config(
        game_code_path=config_pack["game_code_path"],
        policy_path=config_pack["policy_path"],
        heuristic_paths=config_pack["model_file_paths"],
        heuristic_selection_config=config_pack["config"],
        num_test_runs=config_pack["test_repeat"],
        maximize_obj_func=config_pack["maximize_obj_func"]
    )



def main():
    parser = argparse.ArgumentParser(description="Optimize heuristic selection for a given gameplay AI.")
    parser.add_argument("--game", type=str, required=True, help="Name of the game")
    parser.add_argument("--dir", type=str, required=True, help="Working directory")
    parser.add_argument("--optimize_ablation", action="store_true", help="Run ablation optimization")
    args = parser.parse_args()

    game_code_file_path = os.path.join(args.dir, args.game, f"{args.game}.py")
    game_description_file_path = os.path.join(args.dir, args.game, f"{args.game}.md")
    optimize_weights(
        game_description_file_path,
        game_code_file_path,
        os.path.join(args.dir, args.game),
        LLMHandler(),
        optimize_ablation=args.optimize_ablation
    )

if __name__ == "__main__":
    main()