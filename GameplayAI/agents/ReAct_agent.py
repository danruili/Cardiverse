from retrying import retry
import json

from GameEngine.utils.base_agents import BaseAgent
from GameEngine.utils.base_message import observation_to_str
from Utils.LLMHandler import LLMHandler

REACT_PROMPT = """
You are a player in a card game. Please do your best to beat the other players and win the game.

The card game is as follows:
```
{game_description}
```

Previous observation of game history and your current state is as follows:
```
{observation}
```

Your available actions are as follows:
```
{actions}
```

Please think in steps and make a decision based on the current state of the game.
You should return an index of the action you want to take from the list of legal actions.

Instructions:
1. Analyze the query, previous reasoning steps, and observations.
2. Decide on the next action: choose an action or provide a final answer.
3. Respond in the following JSON format:

Remember:
- Be thorough in your reasoning.
- Choose actions when you need more information.
- Always base your reasoning on the actual observations from chosen action.

If you have enough information to answer the query, wrap your response in a dictionary with the key 'action' and the value as the index of the action you want to take.
for example (You MUST return the action index in the following format):

```json
{
    "thought": "Your detailed reasoning about what to do next",
    "action": 0
}
```
"""

class ReActAgent(BaseAgent):

    def __init__(self, game_description: str, llm_handler: LLMHandler = None):
        super().__init__(game_description=game_description, llm_handler=llm_handler)
        self.game_description = game_description
        if llm_handler is not None:
            self.llm_handler = llm_handler
        else:
            self.llm_handler = LLMHandler()

    @retry(stop_max_attempt_number=5)
    def eval_step(self, state):
        observation_str = observation_to_str(state)

        actions_str = "\n".join([f"{i}: {action}" for i, action in enumerate(state['legal_actions'])])

        format_assertion = False
        range_assertion = False

        while not (format_assertion and range_assertion):
            prompt = REACT_PROMPT.replace("{game_description}", self.game_description).replace("{observation}", observation_str).replace("{actions}", actions_str)
            response = self.llm_handler.chat(prompt)
            json_str = self.parse_action(response)
            format_assertion = self.format_assertion(json_str, ['action'])
            if not format_assertion:
                range_assertion = False
            else:
                range_assertion = self.key_range_assertion(json_str, 'action', 0, len(state['legal_actions']) - 1)

        action_idx = json.loads(json_str)['action']
        action = state['legal_actions'][action_idx]
        
        return action, {}

    def step(self, state):
        return self.eval_step(state)
