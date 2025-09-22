import os
import time
import argparse
import pandas as pd
from tqdm import tqdm
from typing import Union
from pathlib import Path
from GameEngine.utils.base_agents import BaseAgent, RandomAgent, HumanAgent
from GameplayAI.agents import (CoTAgent, ReActAgent, ReflexionAgent,  
    UnoRuleAgent, LeducHoldemRuleAgent, GinRummyRuleAgent)

from GameEngine.utils.game_run import make_env, tournament
from GameEngine.utils.base_message import observation_to_str, history_to_str
from GameplayAI.utils.load_agent import load_agent
from Utils.LLMHandler import LLMHandler


def run_one_game(
        game_code_path: str, 
        game_log_path: Union[str, None],
        defense_agent: BaseAgent, 
        attack_agent: Union[BaseAgent, HumanAgent],
        seed: int = None,
        training: bool = False,
        show_hint: bool = True
        ):

    # load environment
    env = make_env(game_code_path, game_log_path, seed=seed)
    env.show_action_hint = show_hint
    num_players = env.get_num_players()

    # Set up agents
    env.set_agents([defense_agent for _ in range(num_players-1)] + [attack_agent])

    # run the tournament
    if isinstance(attack_agent, HumanAgent):
        game_state, observation = env.reset()
        game_state, observation, display_info = env.auto_step(game_state, observation)
        while (not game_state['common']['is_over']):
            # show obeservation to terminal
            print(observation_to_str(observation))

            # show hint
            if 'hint' in display_info:
                print(f"Hint: {display_info['hint']}")

            # receive action
            action_idx = int(input('>> You choose action (integer): '))
            while action_idx < 0 or action_idx >= len(observation['legal_actions']):
                print('Action illegal...')
                action_idx = int(input('>> Re-choose action (integer): '))
            action = observation['legal_actions'][action_idx]

            # step with action
            game_state, observation, display_info = env.auto_step(game_state, observation, action)

        # get the history since last human decision
        recent_history = env.logger.get_history(env.num_players-1)
        print(history_to_str(recent_history))

        # final payoffs
        payoffs = game_state['payoffs']

    else:
        payoffs = tournament(env, 1)

    # update reflexion agent
    if training:
        for idx, agent in enumerate(env.agents):
            if isinstance(agent, ReflexionAgent):
                agent.reflect(payoffs, idx)
    
    return payoffs


if '__main__' == __name__:
    
    parser = argparse.ArgumentParser(description='Run one game evaluation with Gameplay agents')
    parser.add_argument('--game', type=str, default='uno', help='Name of the game', required=True)
    parser.add_argument('--dir', type=str, default='data/gameplay_ai_generation/examples', help='Path to game directory', required=False)
    parser.add_argument(
        '--defense_agent',
        type=str,
        default='RandomAgent',
        choices=['RandomAgent', 'CoTAgent', 'ReActAgent', 'ReflexionAgent', 
                 'HEAgent', 'RuleAgent', 'HEA-NoOpt', 'HEA-NoEns'],
        help='Name of the defense agent',
        required=True
    )
    parser.add_argument(
        '--attack_agent', 
        type=str, 
        default='HumanAgent',
        choices=['RandomAgent', 'HumanAgent', 'HEAgent', 'HEA-NoOpt', 'HEA-NoEns', 
                 'CoTAgent', 'ReActAgent', 'ReflexionAgent', 'RuleAgent'],
        help='Name of the attack agent',
        required=True
    )
    parser.add_argument('--llm_model', type=str, default='gpt-4o-mini', help='LLM choice', required=False)
    parser.add_argument('--run_num', type=int, default=1, help='Run rounds', required=False)
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility', required=False)
    parser.add_argument('--log', action='store_true', help='Whether to save the game log', required=False)
    parser.add_argument('--log_path', type=str, default=None, help='Path to save the game log, default to game_play_<timestamp>.log', required=False)
    parser.add_argument('--training', action='store_true', help='Whether to enable training mode', required=False)
    parser.add_argument('--output_csv', type=str, default=None, help='Append game results to csv file', required=False)
    
    args = parser.parse_args()

    game_name = args.game
    folder_path = args.dir
    defense_agent_name = args.defense_agent
    attack_agent_name = args.attack_agent
    seed = args.seed
    output_csv = Path(args.output_csv) if args.output_csv is not None else None
    run_num = args.run_num
    llm_model = args.llm_model
    if args.log:
        log_path = args.log_path if args.log_path is not None else f"{game_name}_play_{int(time.time())}.log"
    else:
        log_path = None

    print(f"Game: {game_name}")
    print(f"Folder: {folder_path}")
    print(f"Defense agent: {defense_agent_name}")
    print(f"Attack agent: {attack_agent_name}")

    game_code_path = os.path.join(folder_path, game_name, f"{game_name}.py")
    game_description_path = os.path.join(folder_path, game_name, f"{game_name}.md")
    if not os.path.exists(game_description_path):
        game_description_path = os.path.join(folder_path, game_name, f"{game_name}.txt")
    game_dir_path = os.path.join(folder_path, game_name)

    # prepare LLM-based agents
    llm_handler = LLMHandler(llm_model) 
    with open(game_description_path, 'r', encoding='utf-8') as f:
        game_description = f.read()

    # Configure attack agent
    if attack_agent_name == 'HumanAgent':
        hint_agent = load_agent(game_dir_path, method='ours')
        show_hint = True if not isinstance(hint_agent, RandomAgent) else False
        hint_agent = hint_agent if show_hint else None
        attack_agent = HumanAgent(hint_agent=hint_agent)
    elif attack_agent_name == 'HEAgent':
        attack_agent = load_agent(game_dir_path, method='ours')
    elif attack_agent_name == 'HEA-NoOpt':
        attack_agent = load_agent(game_dir_path, method='NoOpt')
    elif attack_agent_name == 'HEA-NoEns':
        attack_agent = load_agent(game_dir_path, method='NoEns')
    elif attack_agent_name == 'CoTAgent':
        attack_agent = CoTAgent(game_description, llm_handler)
    elif attack_agent_name == 'ReActAgent':
        attack_agent = ReActAgent(game_description, llm_handler)
    elif attack_agent_name == 'ReflexionAgent':
        attack_agent = ReflexionAgent(game_description, llm_handler)
    elif attack_agent_name == 'RuleAgent':
        if game_name == 'gin_rummy':
            attack_agent = GinRummyRuleAgent()
        elif game_name == 'uno':
            attack_agent = UnoRuleAgent()
        elif game_name == 'leduc_holdem':
            attack_agent = LeducHoldemRuleAgent()
        else:
            raise ValueError(f"Rule agent not implemented for game: {game_name}")
    else:
        attack_agent = RandomAgent()
        
    # Configure defense agent
    if defense_agent_name == 'CoTAgent':
        defense_agent = CoTAgent(game_description, llm_handler)
    elif defense_agent_name == 'ReActAgent':
        defense_agent = ReActAgent(game_description, llm_handler)
    elif defense_agent_name == 'ReflexionAgent':
        defense_agent = ReflexionAgent(game_description, llm_handler)
    elif defense_agent_name == 'HEAgent':
        defense_agent = load_agent(game_dir_path, method='ours')
    elif defense_agent_name == 'HEA-NoOpt':
        defense_agent = load_agent(game_dir_path, method='NoOpt')
    elif defense_agent_name == 'HEA-NoEns':
        defense_agent = load_agent(game_dir_path, method='NoEns')
    elif defense_agent_name == 'RuleAgent':
        if game_name == 'gin_rummy':
            defense_agent = GinRummyRuleAgent()
        elif game_name == 'uno':
            defense_agent = UnoRuleAgent()
        elif game_name == 'leduc_holdem':
            defense_agent = LeducHoldemRuleAgent()
        else:
            raise ValueError(f"Rule agent not implemented for game: {game_name}")
    else:
        defense_agent = RandomAgent()

    for i in tqdm(range(run_num)):
        start_time = time.time()
        payoffs = run_one_game(game_code_path, log_path, defense_agent, attack_agent, seed, training=args.training)
        end_time = time.time()

        if output_csv:
            round_time = end_time - start_time
            if not os.path.exists(output_csv):
                output_csv.parent.mkdir(parents=True, exist_ok=True)
                df = pd.DataFrame({
                    'Game': [game_name], 
                    'Attack': [attack_agent_name], 
                    'Defense': [defense_agent_name], 
                    'Payoffs': [payoffs], 
                    'Run_time': [round_time],
                    'Timestamp': [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())]
                    })
                df.to_csv(output_csv, index=False)
            else:
                df = pd.read_csv(output_csv)
                new_row = pd.DataFrame({
                    'Game': [game_name], 
                    'Attack': [attack_agent_name], 
                    'Defense': [defense_agent_name], 
                    'Payoffs': [payoffs], 
                    'Run_time': [round_time],
                    'Timestamp': [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())]
                    })
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(output_csv, index=False)
