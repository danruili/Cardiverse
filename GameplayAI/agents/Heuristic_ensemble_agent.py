import json
from typing import Union, Dict, Tuple
import numpy as np
import threading

from GameplayAI.utils.q_func_design import LLMQFunc
from GameEngine.utils.base_agents import BaseAgent
from Utils.LLMHandler import LLMHandler



def softmax_probs(values: list[float], temperature=1.0) -> np.array:
    """return the probabilities based on the softmax distribution of the values"""
    values = np.array(values)
    values = values / temperature
    values = np.exp(values)
    values = values / np.sum(values)
    return values


def argmax_choice(action_probs, temperature=0.1) -> int:
    """return the index of the chosen action based on the argmax of the values"""
    if np.random.random() < temperature:
        return np.random.choice(len(action_probs))
    else:
        # if there are multiple actions with the same highest score, choose one randomly
        return np.random.choice(np.flatnonzero(action_probs == np.max(action_probs)))



class HeuristicEnsembleAgent(BaseAgent):
    feature_num = 5
    policy_list = None
    feature_models = None
    train_step_temperture = 0.01

    def __init__(self,
                 game_description: str,
                 input_description: str,
                 policy_list: list[str],
                 code: list[str] = None, 
                 weights=None, 
                 flipped_indices: list[int] = None,
                 enable_fix: bool = False,
                 llm_handler: LLMHandler = None,
                 **kwargs):
        
        super().__init__()

        self.use_raw = True
        self.policy_list = policy_list
        self.feature_num = len(policy_list)
        self.llm_handler = llm_handler

        # initialize feature models
        if code is not None:
            self.feature_models = [
                LLMQFunc(game_description, policy, input_description, 
                        code_func, enable_fix, 
                        llm_handler=llm_handler) 
                for policy, code_func in zip(policy_list, code)
                ]
        else:
            def init_llmqfunc(game_description, policy, input_description, enable_fix, llm_handler, result, index):
                result[index] = LLMQFunc(game_description, policy, input_description, enable_fix=enable_fix, llm_handler=llm_handler)

            # initialize the feature models in parallel
            threads = []
            result = [None] * len(policy_list)
            for i, policy in enumerate(policy_list):
                thread = threading.Thread(target=init_llmqfunc, args=(game_description, policy, input_description, True, llm_handler, result, i))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()

            self.feature_models = result

        # initialize the weights
        if weights is not None:
            self.weights = weights
        else:
            self.weights = np.ones(self.feature_num) / self.feature_num

        if flipped_indices is not None:
            self.flip_weights(flipped_indices)


    def to_json(self) -> Union[str, None]:
        """
        Return the policy as a json object
        """
        if self.feature_models is None:
            return None
        else:
            features = [feature.code for feature in self.feature_models]
            json_dict = {
                "game_description": self.feature_models[0].game_description,
                "input_description": self.feature_models[0].input_description,
                "policy_list": self.policy_list,
                "code": features,
                # "included_indices": list(range(len(features)))
            }
            return json.dumps(json_dict, indent=4)
        
    def to_json_file(self, file_path: str):
        """
        Save the agent to a json file
        """
        with open(file_path, 'w') as f:
            f.write(self.to_json())
        
    @classmethod
    def from_json(cls, json_dict: Dict, **kwargs):
        """
        Load the policy from a json string or a json dict
        """
        return cls(**json_dict, **kwargs)
    
    @classmethod
    def from_json_file(cls, file_path: str, **kwargs):
        """
        Load the policy from a json file
        """
        with open(file_path, 'r') as f:
            return cls.from_json(json.loads(f.read()), **kwargs)
        
    def make_choice(self, action_probs, temperature=0.1) -> int:
        return argmax_choice(action_probs, temperature=temperature)

    def eval_step(self, state, temperature=None) -> Tuple[str, Dict]:

        if temperature is None:
            temperature = self.train_step_temperture

        # score each legal action
        legal_actions = state['legal_actions']

        scores: list[float] = []
        for action in legal_actions:
            score, features = self.score(state, action)
            scores.append(score)

        # choose an action using softmax
        action_probs = softmax_probs(scores, temperature=0.1)
        action = legal_actions[self.make_choice(np.array(action_probs), temperature)]

        info = {
            'probs': action_probs,
            'legal_actions': legal_actions,
            'scores': scores,
        }

        return action, info
    
    def score(self, state, action):
        """
        Return the score of the action
        Args:
            state (dict): Raw state from the game,
            action (str): The action to be evaluated. example: 'y-7' or 'draw'

        Returns:
            score (float): The score of the action
            features (np.ndarray): scores for each LLM component
        """
        features = np.array([policy_model(state, action) for policy_model in self.feature_models])
        score = np.dot(features, self.weights)
        return score, features

    def step(self, state) -> str:
        action, _ = self.eval_step(state, temperature=0.0)
        return action

    def flip_weights(self, flipped_indices: list[int]):
        for index in flipped_indices:
            self.weights[index] = -self.weights[index]

