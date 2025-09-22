from pydantic import BaseModel
import logging
import json
from retrying import retry
from typing import Literal

from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from GameplayAI.utils.extract import extract_from_language
from GameplayAI.utils.get_action_desc import extract_action_from_desc
import threading

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

general_system_template = '''
You are a powerful assistant who designs an AI player for a card game.
'''

singular_strategy_template = '''
You are a powerful assistant who designs an AI player for a card game.

# Game rules
{game_description}

# Game state
The AI player knows all cards in its hands, all game play history. But it does not know the content of other players' hands.

# Potential actions
{game_actions}

# Task
Please think in steps to provide me a useful and comprehensive strategy to win the game.
Please describe its definition and how it relates to the game state and a potential action.

# Response format
Please respond in the following JSON format:
{format_instructions}
'''

strategy_template = '''
You are a powerful assistant who designs an AI player for a card game.

# Game rules
{game_description}

# Game state
The AI player knows all cards in its hands, all game play history. But it does not know the content of other players' hands.

# Potential actions
{game_actions}

# Task
Please think in steps to provide me {item_num} useful strategies to win the game.
For each strategy, please describe its definition and how it relates to the game state and a potential action.

# Response format
Please respond in the following JSON format:
{format_instructions}
'''

metric_template = '''
You are a powerful assistant who designs an AI player for a card game.

# Game rules
{game_description}

# Game state
The AI player knows all cards in its hands, all game play history. But it does not know the content of other players' hands.

# Potential actions
{game_actions}

# Task
To design a good game play policy, we need to design some game state metrics that constitute a reward function.
Now please think in steps to tell me what useful metric can we derive from a game state?
The metric should be correlated with both the game state and the potential action. Provide me with {item_num} metrics.

# Response format
Please respond in the following JSON format:
{format_instructions}
'''

reflection_template = '''
You are a powerful assistant who designs an AI player for a card game.

# Game rules
{game_description}

# Game state
The AI player knows all cards in its hands, all game play history. But it does not know the content of other players' hands.

# Potential actions
{game_actions}

# Task
Given the following strategy of the game:
```json
{game_strategy}
```

Please think in steps to refine the strategy using the following criteria:
(1) If the strategy has anything obscure, for example, if it mentions "strategically use" or "use at critical moments" without specifying what the critical moments are, please clarify what the critical moments are.
(2) If the strategy is conditioned on a game state metric, please describe how such a strategy will be conditioned on the game state. Here are some hints of the game state:
```json
{game_metrics}
```

# Response format
Please respond in the following JSON format:
{format_instructions}
'''


class Strategy(BaseModel):
    name: str
    description: str
    reason: str

class Strategies(BaseModel):
    items: list[Strategy]

class Metric(BaseModel):
    name: str
    description: str

class Metrics(BaseModel):
    items: list[Metric]

class Reflection(BaseModel):
    name: str
    reflection: str
    content: str

PolicyMethod = Literal["singular", "strategy", "metric", "reflect", "strategy_metric_one_code"]

class LLMPolicy:
    """
    Design a policy for a game. The policy is a list of strategies in string format.
    """

    def __init__(self, game_description: str = None,
                 item_num: int = None,
                 llm_handler: LLMHandler = None
                 ):

        if llm_handler is not None:
            self.llm = llm_handler
        else:
            self.llm = LLMHandler()
        self.game_description = game_description
        self.game_actions = None
        self.item_num = item_num

        # intermediate results
        self.singular_strategy: Strategy = None
        self.strategies: Strategies = None
        self.metrics: Metrics = None
        self.reflections_dict: dict[str, Reflection] = {}

    def design_policy(self):
        logger.info("extracting game actions...")
        self.game_actions = extract_action_from_desc(self.game_description, self.llm)

        # design strategies and metrics in parallel
        logger.info("designing strategies and metrics...")
        singular_thread = threading.Thread(target=self.design_singlular_strategy)
        strategy_thread = threading.Thread(target=self.design_strategy)
        metric_thread = threading.Thread(target=self.design_metric)
        singular_thread.start()
        strategy_thread.start()
        metric_thread.start()
        singular_thread.join()
        strategy_thread.join()
        metric_thread.join()

        logger.info("reflecting strategy...")
        self.reflect_strategies()

    def get_policy(self, key: PolicyMethod = "reflect") -> list[str]:
        result = []
        if key == "strategy":
            for strategy in self.strategies.items:
                result.append(f"**{strategy.name}**\n{strategy.description}")
        elif key == "reflect":
            for reflection in self.reflections_dict.values():
                result.append(f"**{reflection.name}**\n{reflection.content}")
        elif key == "metric":
            for metric in self.metrics.items:
                result.append(f"**{metric.name}**\n{metric.description}")
        elif key == "singular":
            result.append(f"**{self.singular_strategy.name}**\n{self.singular_strategy.description}")
        elif key == "strategy_metric_one_code":
            # concat all metrics and strategies
            concat = []
            for metric in self.metrics.items:
                concat.append(f"**{metric.name}**\n{metric.description}")
            for strategy in self.strategies.items:
                concat.append(f"**{strategy.name}**\n{strategy.description}")
            result.append("\n".join(concat))
        return result
    
    @retry(stop_max_attempt_number=5)
    def design_singlular_strategy(self) -> Strategy:
        singular_strategy_prompt = singular_strategy_template.replace("{game_description}", self.game_description)\
            .replace("{game_actions}", self.game_actions)\
            .replace("{format_instructions}", json.dumps(Strategy.model_json_schema()))
        
        chat_sequence = ChatSequence()
        chat_sequence.append(Message(role="system", content=general_system_template))
        chat_sequence.append(Message(role="user", content=singular_strategy_prompt))

        result_json = self.chat_and_parse_json(chat_sequence)
        try:
            self.singular_strategy = Strategy.model_validate_json(result_json)
        except Exception as e:
            # print(result_json)
            raise e
        return self.singular_strategy

    @retry(stop_max_attempt_number=5)
    def design_strategy(self) -> Strategies:
        strategy_prompt = strategy_template.replace("{game_description}", self.game_description)\
            .replace("{game_actions}", self.game_actions)\
            .replace("{item_num}", str(self.item_num))\
            .replace("{format_instructions}", json.dumps(Strategies.model_json_schema()))
        
        chat_sequence = ChatSequence()
        chat_sequence.append(Message(role="system", content=general_system_template))
        chat_sequence.append(Message(role="user", content=strategy_prompt))

        result_json = self.chat_and_parse_json(chat_sequence)
        try:
            self.strategies = Strategies.model_validate_json(result_json)
        except Exception as e:
            # print(result_json)
            raise e
        return self.strategies

    @retry(stop_max_attempt_number=5)
    def design_metric(self) -> Metrics:
        metric_prompt = metric_template.replace("{game_description}", self.game_description)\
            .replace("{game_actions}", self.game_actions)\
            .replace("{item_num}", str(self.item_num))\
            .replace("{format_instructions}", json.dumps(Metrics.model_json_schema()))
        
        chat_sequence = ChatSequence()
        chat_sequence.append(Message(role="system", content=general_system_template))
        chat_sequence.append(Message(role="user", content=metric_prompt))
                             
        result_json = self.chat_and_parse_json(chat_sequence)
        try:
            self.metrics = Metrics.model_validate_json(result_json)
        except Exception as e:
            # print(result_json)
            raise e
        return self.metrics

    @retry(stop_max_attempt_number=5)
    def reflect_strategy(self, game_strategy: Strategy, game_metrics: Metrics) -> Reflection:
        reflection_prompt = reflection_template.replace("{game_description}", self.game_description)\
            .replace("{game_actions}", self.game_actions)\
            .replace("{game_strategy}", game_strategy.model_dump_json())\
            .replace("{game_metrics}", game_metrics.model_dump_json())\
            .replace("{format_instructions}", json.dumps(Reflection.model_json_schema()))
        
        chat_sequence = ChatSequence()
        chat_sequence.append(Message(role="system", content=general_system_template))
        chat_sequence.append(Message(role="user", content=reflection_prompt))

        try:
            result_json = self.chat_and_parse_json(chat_sequence)
            return Reflection.model_validate_json(result_json)
        except Exception as e:
            # print(result_json)
            raise e
    
    @retry(stop_max_attempt_number=3)
    def chat_and_parse_json(self, chat_seq: ChatSequence) -> dict:
        result = self.llm.chat(chat_seq)
        result_json = extract_from_language(result, 'json')
        return result_json

    def reflect_strategies(self) -> dict[str, Reflection]:
        for strategy in self.strategies.items:
            reflections = self.reflect_strategy(strategy, self.metrics)
            self.reflections_dict[strategy.name] = reflections
        return self.reflections_dict
    
    def to_json(self) -> dict:
        return {
            "game_description": self.game_description,
            "game_actions": self.game_actions,
            "singular_strategy": self.singular_strategy.model_dump_json(),
            "strategies": self.strategies.model_dump_json(),
            "metrics": self.metrics.model_dump_json(),
            "reflections": {k: v.model_dump_json() for k, v in self.reflections_dict.items()}
        }
    
    @staticmethod
    def from_json(json_data: dict):
        policy = LLMPolicy()
        policy.singular_strategy = Strategy.model_validate(json.loads(json_data["singular_strategy"]))
        policy.strategies = Strategies.model_validate(json.loads(json_data["strategies"]))
        policy.metrics = Metrics.model_validate(json.loads(json_data["metrics"]))
        policy.reflections_dict = {k: Reflection.model_validate(json.loads(v)) for k, v in json_data["reflections"].items()}
        policy.game_description = json_data["game_description"]
        policy.game_actions = json_data["game_actions"]
        policy.item_num = len(policy.strategies.items)
        return policy
    
    def save(self, file_path: str):
        with open(file_path, 'w') as f:
            json.dump(self.to_json(), f, indent=4)

    @staticmethod
    def load(file_path: str):
        with open(file_path, 'r') as f:
            json_data = json.load(f)
        return LLMPolicy.from_json(json_data)


if __name__ == "__main__":
    game_description = "A card game where players need to play cards in a sequence."
    item_num = 8
    policy = LLMPolicy(game_description=game_description, item_num=item_num)
    policy.design_policy()
    policy.save("policy.json")