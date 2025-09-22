from retrying import retry
import os
import json

from GameEngine.utils.base_agents import BaseAgent
from GameEngine.utils.base_message import observation_to_str
from Utils.LLMHandler import LLMHandler

BELIEF_PROMPT = """
You are a player in a card game. Please do your best to beat the other players and win the game.

The card game description is as follows:
```
{game_description}
```

Previous observation of game history and your current state is as follows:
```
{observation}
```

Here is your previous reflection based on the game state is as follows:
```
{reflection}
```

Previous belief is as follows:
```
self-belief: {self_belief}
world-belief: {world_belief}
```


Please read the game decription and observation carefully.
Then you should analyze your own cards and your strategies in Self-belief and then analyze the opponents cards in World-belief.
Lastly, please select your action from:
```
{actions}
```

You MUST return the action index in the following format:
```json
{
    "self-belief": "I have a good hand", 
    "world-belief": "Dealer has a bad hand", 
    "action": 1
}
```
"""


class BeliefAgent(BaseAgent):

    def __init__(self, game_description: str, llm_handler: LLMHandler = None, reflection_path: str = None, training=False):
        super().__init__(game_description=game_description, llm_handler=llm_handler, reflection_path=reflection_path, training=training)
        self.game_description = game_description
        if llm_handler is not None:
            self.llm_handler = llm_handler
        else:
            self.llm_handler = LLMHandler()

        self.reflection_path = reflection_path
        if os.path.exists(self.reflection_path):
            with open(self.reflection_path, 'r') as f:
                self.reflection = f.read()
        else:
            self.reflection = ""
        self.self_belief = ""
        self.world_belief = ""


    @retry(stop_max_attempt_number=5)
    def eval_step(self, state):
        observation_str = observation_to_str(state)
        actions_str = "\n".join([f"{i}: {action}" for i, action in enumerate(state['legal_actions'])])

        format_assertion = False
        range_assertion = False

        while not (format_assertion and range_assertion):
        # while action_idx < 0 or action_idx >= len(state['legal_actions']):

            prompt = BELIEF_PROMPT.replace("{game_description}", self.game_description)\
                    .replace("{observation}", observation_str)\
                        .replace("{actions}", actions_str)\
                            .replace("{reflection}", self.reflection)\
                                .replace("{self_belief}", self.self_belief)\
                                    .replace("{world_belief}", self.world_belief)
            response = self.llm_handler.chat(prompt)
            json_str = self.parse_action(response)
            format_assertion = self.format_assertion(json_str, ['self-belief', 'world-belief', 'action'])

            if not format_assertion:
                range_assertion = False
            else:
                range_assertion = self.key_range_assertion(json_str, 'action', 0, len(state['legal_actions']) - 1)

            action_idx = json.loads(json_str)['action']

        action = state['legal_actions'][action_idx]
        
        return action, {}

    def step(self, state):
        return self.eval_step(state)