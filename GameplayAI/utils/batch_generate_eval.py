import os
import argparse
from pathlib import Path


def generate_evaluation_script(folder_path: list, defense_agents: list, attack_agents: list, run_num: int, output_csv: str, llm_model: str):
    script = f"#!/bin/bash"

    for path in folder_path:
        game_path = Path(path)
        game_name = game_path.name
        script += f"""
# Start new tmux session detached
tmux new-session -d -s {game_name}-e
"""
        window_idx = 0

        for defense_agent in defense_agents:
            for attack_agent in attack_agents:
                sub_script = f"""

# Rename first window and run command
tmux new-window -a -t {game_name}-e -n '{game_name}_evaluation_{defense_agent}_vs_{attack_agent}'
tmux send-keys -t {game_name}-e:'{game_name}_evaluation_{defense_agent}_vs_{attack_agent}' 'source source .venv/bin/activate' C-m
tmux send-keys -t {game_name}-e:'{game_name}_evaluation_{defense_agent}_vs_{attack_agent}' 'python -m GameplayAI.run_game --game {game_name} --dir {path} --defense_agent {defense_agent} --attack_agent {attack_agent} --run_num {run_num} --output_csv {output_csv} --llm_model {llm_model}' C-m
# kill the window after the command is done
tmux send-keys -t {game_name}-e:'{game_name}_evaluation_{defense_agent}_vs_{attack_agent}' 'exit' C-m
"""
                script += sub_script
                window_idx += 1
    return script


def generate_kill_script(folder_path: list):
    script = f"#!/bin/bash"

    for path in folder_path:
        game_path = Path(path)
        game_name = game_path.name
        script += f"""
# Kill tmux session
tmux kill-sess -t {game_name}-e
"""
    return script


def main(root_path, exclude_games, script_path, defense_agents, attack_agents, run_num, output_csv, llm_model):
    # load game folder paths from GameLib/gen-best-0-60
    folder_paths = os.listdir(root_path)
    print(f"All games found: {folder_paths}")
    folder_paths = [os.path.join(root_path, folder) for folder in folder_paths if os.path.isdir(os.path.join(root_path, folder))]
    folder_paths.sort()

    # Exclude specific games
    folder_paths = [path for path in folder_paths if Path(path).name not in exclude_games]
    print(f"Found {len(folder_paths)} games for evaluation.")
    
    # Define parameters
    config = {
        'folder_path': folder_paths,
        'defense_agents': defense_agents,
        'attack_agents': attack_agents,
        'run_num': run_num,
        'output_csv': output_csv,
        'llm_model': llm_model
    }

    # Generate bash script
    script_content = generate_evaluation_script(**config)
    
    # Write bash script to file
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # kill_script_content = generate_kill_script(folder_paths)
    # kill_script_path = 'kill_session_eval_novel.sh'
    # with open(kill_script_path, 'w') as f:
    #     f.write(kill_script_content)
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    # os.chmod(kill_script_path, 0o755)
    
    print(f"Generated evaluation script: {script_path}")
    # print(f"Generated evaluation script: {kill_script_path}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Generate batch evaluation script')
    parser.add_argument('--root_path', type=str, default='data/gameplay_ai_generation/examples', help='Root path of the game folder', required=True)
    parser.add_argument('--exclude_games', nargs='+', default=[], help='Games to exclude', required=False)
    parser.add_argument('--script_path', type=str, default='batch_eval.sh', help='Script path', required=False)
    parser.add_argument('--defense_agents', nargs='+', default=['RandomAgent'], help='Defense agents', required=True)
    parser.add_argument('--attack_agents', nargs='+', default=['RandomAgent', 'ReActAgent'], help='Attack agents', required=True)
    parser.add_argument('--run_num', type=int, default=50, help='Run number', required=False)
    parser.add_argument('--output_csv', type=str, default='eval.csv', help='Output csv', required=False)
    parser.add_argument('--llm_model', type=str, default='gpt-4o-mini', help='LLM model', required=False)
    args = parser.parse_args()

    root_path = args.root_path
    exclude_games = args.exclude_games
    script_path = args.script_path
    defense_agents = args.defense_agents
    attack_agents = args.attack_agents
    run_num = args.run_num
    output_csv = args.output_csv
    llm_model = args.llm_model

    main(root_path, exclude_games, script_path, defense_agents, attack_agents, run_num, output_csv, llm_model)