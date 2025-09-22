"""
This module contains the implementation of the complete game engine for game AI development and final game playing.
For game code generation, there is a simplified version that costs fewer tokens in in-context learning.
"""

"""Beginning of the game engine"""
import random
from typing import List, Dict, Tuple, Union, Any, Optional, OrderedDict, Type  # must keep this redundant import
from GameEngine.utils.env_logger import EnvLogger
from GameEngine.utils.base_message import ObservationMsg, PayoffMsg, TurnEndMsg
from GameEngine.utils.base_agents import BaseAgent, HumanAgent
from copy import deepcopy
import json
from itertools import combinations

class LLMCard:
    """
    The base class for cards in LLM games.
    Use this as reference only. You are not allowed to modify this class.
    You don't need to repeat this class definition in your response.
    """

    def __init__(self, field: dict):
        """
        Initialize the class of LLMCard.
        For each field in the dict, add it as an attribute to the class.
        Compulsory fields: name, id.
        """
        for k, v in field.items():
            setattr(self, k, v)
        self.field = field
        self.str = self.get_str()

    def get_str(self):
        """
        Get the string representation of card by concatenating all fields.
        """
        field_list = [field for field in self.field.values() if field is not None]
        return '-'.join([str(k) for k in field_list])

    def __str__(self):
        return self.get_str()

    def to_dict(self):
        return self.__json__()

    def __getitem__(self, key):
        return self.field[key]

    def __repr__(self) -> str:
        return self.get_str()
    
    def __json__(self):
        json_dict = {k: v for k, v in self.field.items() if v is not None}
        json_dict['is_card'] = True
        return json_dict
    
    def __html__(self):
        return self.__json__()

class LLMGameStateEncoder(json.JSONEncoder):
    def default(self, obj):
        # Whenever we try to serialize an object of type LLMCard,
        # we'll call its __json__ method, which returns a serializable dict
        if "LLMCard" in str(type(obj)):
            return obj.__json__()
        # For everything else, fall back on the default behavior
        return super().default(obj)

class DotDict(dict):
    """
    A dictionary subclass that supports attribute-style access
    for nested dictionaries.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            self[key] = self._convert_value(value)

    def _convert_value(self, value):
        if isinstance(value, dict) and 'is_card' in value.keys():
            value.pop('is_card')
            return LLMCard(value)
        elif isinstance(value, dict):
            return DotDict(value)
        elif isinstance(value, list):
            return [self._convert_value(item) for item in value]
        return value

    def __getattr__(self, item):
        if item in self:
            return self[item]
        raise AttributeError(f"'DotDict' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError(f"'DotDict' object has no attribute '{key}'")

    def __setitem__(self, key, value):
        super().__setitem__(key, self._convert_value(value))

def cards2list(cards: list[LLMCard]) -> list[str]:
    """ Get the corresponding string representation of cards"""
    cards_list = []
    for card in cards:
        cards_list.append(card.get_str())
    return cards_list

def get_observation(game_state: Dict) -> DotDict:
    """
    Make a copy of the game state and remove the hidden and private information.
    for common_facedown, only keep the number of cards for list[card] fields.
    """
    observation = deepcopy(game_state)
    current_player_index = observation['common']['current_player']
    if 'players' in observation:
        for i, player in enumerate(observation['players']):
            if i != current_player_index:
                if 'private' in player:
                    player.pop('private')
                if 'facedown_cards' in player and not observation['common']['is_over']:
                    player['facedown_cards'] = {f"{k}_size": len(v) for k, v in player['facedown_cards'].items()}
                if observation['common']['is_over']:
                    player['public']['final_showdown'] = True
            else:
                player['public']['current_player'] = True

    if 'facedown_cards' in observation['common']:
        result_dict = {}
        for k, v in observation['common']['facedown_cards'].items():
            if isinstance(v, list):
                result_dict[f"{k}_size"] = len(v)
            else:
                result_dict[k] = v
        observation['common']['facedown_cards'] = result_dict

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
    
    return DotDict(observation)

def create_display_json(game_state: Dict, legal_actions) -> Dict:
    play_json = get_observation(game_state)
    play_json['info'] = {"game": game_name}
    # add ids to legal actions
    for i, action in enumerate(legal_actions):
        action['id'] = i
    play_json['legal-actions'] = legal_actions
    return play_json
    
class LLMGame:
    """
    The base class for LLM games.
    Use this as reference only. You are not allowed to modify this class.
    You don't need to repeat this class definition in your response.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.logger = EnvLogger(config)
        self.agents: list[BaseAgent] = None
        self.show_action_hint = False
        self.num_players = recommended_num_players if 'game_num_players' not in config or config['game_num_players'] is None else config['game_num_players']
        assert self.num_players is not None, "Please specify the number of players in the config"
        
        # Set random seed, default is None
        if 'seed' in config:
            random.seed(config['seed'])
        else:
            random.seed(None)

    def set_agents(self, agents):
        '''
        Set the agents that will interact with the environment.
        This function must be called before `run`.

        Args:
            agents (list): List of Agent classes
        '''
        self.agents = agents

    def get_num_players(self) -> int:
        return self.num_players
    
    def reset(self) -> Tuple[Dict, Dict]:
        """ Reset the game to the initial state"""
        self.logger.reset()
        game_state = initiation(self.num_players, self.logger)
        game_state = DotDict(game_state)
        legal_actions = get_legal_actions(game_state)
        observation = get_observation(game_state)
        observation['legal_actions'] = legal_actions
        return game_state, observation
    
    def step(
            self, 
            game_state: Dict, 
            observation: Dict, 
            action: str=None
        ) -> Tuple[Dict, Dict, Dict]:
        """
        Proceed the game by one step. If the current player is human, the action
        is required. If the current player is non-human, the action will be decided.
        Args:
            - game_state (Dict): The current state of the game.
            - observation (Dict): The observation of the current player.
            - action (str, optional): The action taken by the current player. Defaults to None.
        Returns:
            - Tuple[Dict, Dict, Dict]: A tuple containing:
                - game_state (Dict): The new game state after the action.
                - observation (Dict): The observation of the current player.
                - display_info (Dict): The information for display.
        """
        self.logger.append(game_state)

        current_player = game_state['common']['current_player']
        self.logger.record(ObservationMsg(current_player, observation))

        if isinstance(self.agents[current_player], HumanAgent):
            # record human action
            self.logger.act(current_player, action)
        else:
            # let non-human agent decide the action     
            action, _  = self.agents[current_player].eval_step(observation)
            self.logger.act(current_player, action)
            
        # update game state
        game_state = proceed_round(action, game_state, self.logger)

        # get new legal actions and observation
        legal_actions = get_legal_actions(game_state)
        observation = get_observation(game_state)
        observation['recent_history'] = self.logger.get_history(game_state['common']['current_player'])  # new current player
        observation['legal_actions'] = legal_actions

        # record the end of the turn
        self.logger.record(TurnEndMsg(current_player))

        if game_state['common']['is_over']:
            # forcely set the current player to the last player for visualization (in our setting, human player is always the last player)
            game_state['common']['current_player'] = game_state['common']['num_players'] - 1

            # get display info
            display_info = create_display_json(game_state, legal_actions)

            # Calculate payoffs
            payoffs = get_payoffs(game_state, self.logger)
            if self.logger.enable_info:
                self.logger.info(f"Game over. Payoffs for each player: {payoffs}")
            else:
                self.logger.record(PayoffMsg(payoffs))

            # add payoffs to display info and game state
            display_info["payoffs"] = payoffs
            for idx, payoff in enumerate(payoffs):
                display_info['players'][idx]['public']['payoff'] = payoff
            game_state['payoffs'] = payoffs
            return game_state, observation, display_info
        else:
            display_info = create_display_json(game_state, legal_actions)
            return game_state, observation, display_info
    
    def auto_step(
            self, 
            game_state: Dict, 
            observation: Dict, 
            action: str=None
        ) -> Tuple[Dict, Dict, Dict]:
        """ Proceed the game until the next human agent's turn"""
        game_state, observation, display_info = self.step(game_state, observation, action)

        while (not game_state['common']['is_over']) and \
            (not isinstance(self.agents[game_state['common']['current_player']], HumanAgent)):
            game_state, observation, display_info = self.step(game_state, observation, action)

        if not game_state['common']['is_over'] \
            and isinstance(self.agents[game_state['common']['current_player']], HumanAgent)\
                and self.show_action_hint:
            action_hint, _  = self.agents[game_state['common']['current_player']].eval_step(observation)
            display_info['hint'] = action_hint

        display_info["msg"] = self.logger.get_history(game_state['common']['current_player'], for_display=True)

        return game_state, observation, display_info
"""End of the game engine"""
"""Beginning of the code template"""
game_name = None # TODO: specify the game name
recommended_num_players: int = None  # TODO: specify the recommended number of players
num_players_range: List[int] = None # TODO: specify the range of number of players

def initiation(num_players, logger) -> DotDict:
    """
    Initialize the game state. The game state contains all information of the game.
    """
    # TODO: initialize the game state
    game_state = DotDict({
        'common':  # mandatory field, store non-player-related information
        {
            'num_players': num_players,
            'current_player': 0,  # mandatory field
            'direction': 1,
            'winner': None,  # mandatory field
            'is_over': False,  # mandatory field
            'facedown_cards':  # facedown cards such as deck go here
            {
                'deck': [], 
            },
            'faceup_cards':  # faceup cards such as played cards go here
            {
                'played_cards': [],
                'target_card': None,
            },
        },
        'players': [  # mandatory field
            DotDict({
                'public': {}, # mandatory field, card-related fields shall not be included here
                'private': {},  # private information of the player
                'facedown_cards': { 
                    'hand': [],
                },
                'faceup_cards': {  
                    # cards in the faceup are visible to all players
                },
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return DotDict(game_state)


def init_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    # TODO: initialize the deck
    return game_state

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    # TODO: deal cards to players
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Process the action, update the state: the played cards, target, current player, direction, is_over, winner.
    Remember to check if the game is over.
    Args:
        action (dict): action is a dict with a mandatory field 'action' and optional fields in 'args'.
        game_state (dict): the current game state
    Returns:
        new_game_state (dict): the new game state after the action
    """
    # TODO: process the action, update the state, check if the game is over
    pass

def get_legal_actions(game_state: Dict) -> list[dict]:
    """
    Get all legal actions given the current state.
    Don't use logger in this function.

    Returns:
        (list): A list of legal actions, each action is a dict with a mandatory field 'action' and optional fields in 'args'.
    """
    # TODO: get legal actions
    pass


def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """ Return the payoffs for each player."""
    # TODO: get payoffs at the end of the game
    pass

"""End of the code template"""