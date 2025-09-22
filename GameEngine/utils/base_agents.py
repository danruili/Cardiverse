from typing import Dict, Tuple
import json
import re
import numpy as np

class BaseAgent(object):

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.use_raw = True
        self.name = self.__class__.__name__
        self.llm_handler = None

    def step(self, state, **kwargs) -> Tuple[dict, Dict]:
        ''' Predict the action given the curent state in gerenerating training data.

        Args:
            state (dict): An dictionary that represents the current state

        Returns:
            action (dict): The action predicted by the agent
            info (dict): The extra information for training. (optional)
        '''
        return {}, {}

    def eval_step(self, state, **kwargs) -> Tuple[dict, Dict]:
        ''' Predict the action given the current state for evaluation.

        Args:
            state (dict): An dictionary that represents the current state

        Returns:
            action (dict): The action predicted by the agent
            info (dict): The extra information for training. (optional)
        '''
        return {}, {}
    
    def format_assertion(self, json_str, keys) -> bool:
        return all([key in json.loads(json_str) for key in keys])
    
    def key_range_assertion(self, json_str, key, min_val, max_val) -> bool:
        return min_val <= json.loads(json_str)[key] <= max_val
    
    def parse_action(self, response):
        if any(s in self.llm_handler.get_llm() for s in ['gpt', 'claude']):
            try:
                json_str = re.findall(r'```json' + r'\s+(.*?)\s+```', response, re.DOTALL)[-1]
            except:
                json_str = response
        else:
            try:
                json_str = re.findall(r'```(?:json)?\n(\{[^}]+\})', response, re.DOTALL)[-1]
            except:
                json_str = response

        return json_str

class HumanAgent(object):
    ''' A human agent. It can be used to play against trained models
    '''

    def __init__(self, hint_agent=None):
        ''' Initilize the human agent

        Args:
            num_actions (int): the size of the ouput action space
        '''
        self.use_raw = True
        self.hint_agent = hint_agent

    def step(self, state) -> int:
        ''' Human agent will display the state and make decisions through interfaces

        Args:
            state (dict): A dictionary that represents the current state

        Returns:
            action (int): The action decided by human
        '''
        return self.eval_step(state)[0]

    def eval_step(self, state) -> Tuple[int, Dict]:
        ''' Predict the action given the curent state for evaluation. The same to step here.

        Args:
            state (numpy.array): an numpy array that represents the current state

        Returns:
            action (int): the action predicted (randomly chosen) by the random agent
        '''
        if self.hint_agent:
            return self.hint_agent.eval_step(state)
        return 0, {}


class RandomAgent(BaseAgent):
    ''' A random agent. Random agents is for running toy examples on the card games
    '''

    @staticmethod
    def eval_step(state):
        info = {
            'probs': [1 / len(state['legal_actions'] ) for _ in state['legal_actions']],
            'legal_actions': state['legal_actions'],
            } 
        if len(state['legal_actions']) == 0:
            return None, info
        else:
            action = np.random.choice(list(state['legal_actions']))
            return action, info

    def step(self, state):
        return self.eval_step(state)
