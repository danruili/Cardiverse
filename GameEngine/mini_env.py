"""Beginning of the game engine"""
import random
from typing import List, Dict, Tuple, Union, Any, Optional, OrderedDict, Type
from GameEngine.utils.env_logger import EnvLogger
from GameEngine.utils.base_message import ObservationMsg, PayoffMsg, TurnEndMsg
from copy import deepcopy
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

    def __getitem__(self, key):
        return self.field[key]

    def __repr__(self) -> str:
        return self.get_str()

class DotDict(dict):
    """
    A dictionary subclass that supports attribute-style access
    for nested dictionaries.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = DotDict(value)

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
        if isinstance(value, dict):
            value = DotDict(value)
        super().__setitem__(key, value)

    # def __deepcopy__(self, memo):
    #     return DotDict(deepcopy(dict(self)))

def cards2list(cards: list[LLMCard]) -> list[str]:
    """ Get the corresponding string representation of cards"""
    cards_list = []
    for card in cards:
        cards_list.append(card.get_str())
    return cards_list

def get_observation(game_state: Dict) -> Dict:
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
                if 'facedown_cards' in player:
                    player['facedown_cards'] = {f"{k}_size": len(v) for k, v in player['facedown_cards'].items()}
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
    return observation
    
class LLMGame:
    """
    The base class for LLM games.
    Use this as reference only. You are not allowed to modify this class.
    You don't need to repeat this class definition in your response.
    """

    def __init__(self, config: Dict):
        self.logger = EnvLogger(config)
        self.agents = None
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

    def reset(self) -> Tuple[Dict]:
        """ Reset the game to the initial state"""
        game_state = initiation(self.num_players, self.logger)
        return game_state

    def get_num_players(self) -> int:
        return self.num_players
    
    def run(self):
        game_state = self.reset()
        legal_actions = get_legal_actions(game_state)
        observation = get_observation(game_state)
        observation['legal_actions'] = legal_actions

        while not game_state['common']['is_over']:
            self.logger.append(game_state)

            current_player = game_state.common['current_player']
            self.logger.record(ObservationMsg(current_player, observation))
            
            action, _  = self.agents[current_player].eval_step(observation)
            self.logger.act(current_player, action)

            game_state = proceed_round(action, game_state, self.logger)
            legal_actions = get_legal_actions(game_state)
            observation = get_observation(game_state)
            observation['legal_actions'] = legal_actions
            self.logger.record(TurnEndMsg(current_player))
        
        payoffs = get_payoffs(game_state, self.logger)
        if self.logger.enable_info:
            self.logger.info(f"Game over. Payoffs for each player: {payoffs}")
        else:
            self.logger.record(PayoffMsg(payoffs))
        return payoffs
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
    Don't use logger in this function, game_state shall be the ONLY input.
    Avoid returning None or empty list or a list with None.

    Returns:
        (list): A list of legal actions, each action is a dict with a mandatory field 'action' and optional fields in 'args'.
    """
    # TODO: get legal actions
    # you should write an assert to make sure the return result is not None or empty
    pass


def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """ Return the payoffs for each player."""
    # TODO: get payoffs at the end of the game
    pass

"""End of the code template"""