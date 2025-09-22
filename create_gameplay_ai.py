import argparse
import os
import json
from GameplayAI.create_agent import create_agent
from GameplayAI.optimize_agent import optimize_weights
from Utils.LLMHandler import LLMHandler
import logging
import json
import time


def main(folder_path, llm_handler: LLMHandler, policy_num=4):
    # specify gameplayai logger
    logger = logging.getLogger('GameplayAI')
    logger.setLevel(logging.INFO)

    # Iterate through all subfolders in the folder_path
    for game_name in os.listdir(folder_path):
        if os.path.isdir(os.path.join(folder_path, game_name)):
            # get time
            start_time = time.time()

            # Get the game description file path
            game_description_file_path = os.path.join(folder_path, game_name, f"{game_name}.md")
            game_code_file_path = os.path.join(folder_path, game_name, f"{game_name}.py")
            policy_folder_path = os.path.join(folder_path, game_name, "ai")
            policy_path = os.path.join(policy_folder_path, "policy_text.json")
            time_json_path = os.path.join(folder_path, game_name, "time.json")
            token_usage_json_path = os.path.join(folder_path, game_name, "usage.json")

            # If ai folder contains policy_reflect_fixed.json, skip the game
            if not os.path.exists(os.path.join(policy_folder_path, "policy_reflect_fixed.json")):
                # create agent
                logger.info(f"Creating agent for {game_name}")
                create_agent(
                    game_description_file_path,
                    game_code_file_path,
                    policy_folder_path,
                    llm_handler,
                    policy_num=policy_num,
                )
                # save token usage
                with open(token_usage_json_path, "w") as f:
                    f.write(json.dumps(llm_handler.get_usage()))
                # get time usage
                end_time = time.time()
                with open(time_json_path, "w") as f:
                    f.write(json.dumps({"propose_and_code": end_time - start_time}))
                start_time = time.time()


            # check if policy_path json contains "feature_selection"
            with open(policy_path, "r") as f:
                policy_json = f.read()
                policy_json = json.loads(policy_json)
            if "feature_selection" not in policy_json or len(policy_json.get("feature_selection", [])) == 0:
                logger.info(f"Optimizing weights for {game_name} Round 1")
                optimize_weights(
                    game_description_file_path,
                    game_code_file_path,
                    os.path.join(folder_path, game_name),
                    llm_handler
                )
                logger.info(f"Optimizing weights for {game_name} Round 2")
                optimize_weights(
                    game_description_file_path,
                    game_code_file_path,
                    os.path.join(folder_path, game_name),
                    llm_handler
                )
                # add time usage
                end_time = time.time()
                with open(time_json_path, "r") as f:
                    time_json = f.read()
                    time_json = json.loads(time_json)
                time_json["optimize"] = end_time - start_time
                logger.info(f"Time usage for {game_name}: {time_json}")
                with open(time_json_path, "w") as f:
                    f.write(json.dumps(time_json))


if __name__ == "__main__":

    # set logging level
    logging.basicConfig(level=logging.INFO)
    # suppress httpx info
    logging.getLogger('httpx').setLevel(logging.WARNING)

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Create Gameplay AI agents for games in a specified folder.")
    
    # Add arguments
    parser.add_argument("--folder_path", type=str, default="data/gameplay_ai_generation/examples", 
                        help="Path to the working folder")
    parser.add_argument("--policy_num", type=int, default=4,
                        help="Number of policies to create")

    # Parse the arguments
    args = parser.parse_args()
    folder_path = args.folder_path
    policy_num = args.policy_num

    llm_handler = LLMHandler(llm_model="gpt-4o")
    main(folder_path, llm_handler, policy_num=policy_num)
