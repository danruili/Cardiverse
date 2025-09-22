from retrying import retry
import os
import json

from GameEngine.utils.base_agents import BaseAgent
from GameEngine.utils.base_message import observation_to_str
from Utils.LLMHandler import LLMHandler

REFLEXION_PROMPT = """
You are a player in a card game. Please do your best to beat the other players and win the game.

The card game is as follows:
```
{game_description}
```

Previous observation of game history and your current state is as follows:
```
{observation}
```

Your available legal actions are as follows:
```
{actions}
```

Your previous reflection based on the game state is as follows:
```
{reflection}
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
You MUST return the action index in the following format:

```json
{
    "thought": "Your detailed reasoning about what to do next",
    "action": 0
}
```
"""

REFLECTION = """
You are a player in a card game. The card game is as follows:
```
{game_description}
```
This is the payoffs for the game:
```
[{payoffs}], you are player {idx} (list index starting from 0).
```
Here is the previous reflections based on the game results:
```
{reflection}
```

The game is over. Please reflect on the game and provide a detailed summarization for WINNING the game including strategies used, reasoning for actions, and any other relevant information.
You should return a string with your reflection on the game, including strategies used, reasoning for actions, and any other relevant information.
Each reflection item should be precised and concise, NEVER repeat the same reflection twice.
You MUST return the reflection in the following format and ONLY add at most 2 most important new summarization to the previous reflection:
```json
{
    "reflection": "1: strategy 1; 2: strategy 2; ..."
}
```
"""

class ReflexionAgent(BaseAgent):

    def __init__(self, game_description: str, llm_handler: LLMHandler = None, reflection_path: str = None, training=False):
        super().__init__(game_description=game_description, llm_handler=llm_handler, reflection_path=reflection_path, training=training)
        self.game_description = game_description
        if llm_handler is not None:
            self.llm_handler = llm_handler
        else:
            self.llm_handler = LLMHandler()

        self.traing = training
        self.reflection_path = reflection_path
        if os.path.exists(self.reflection_path):
            with open(self.reflection_path, 'r') as f:
                self.reflection = f.read()
        else:
            self.reflection = ""


    @retry(stop_max_attempt_number=5)
    def eval_step(self, state):
        observation_str = observation_to_str(state)
        actions_str = "\n".join([f"{i}: {action}" for i, action in enumerate(state['legal_actions'])])

        format_assertion = False
        range_assertion = False

        while not (format_assertion and range_assertion):
            prompt = REFLEXION_PROMPT.replace("{game_description}", self.game_description).replace("{observation}", observation_str).replace("{actions}", actions_str).replace("{reflection}", self.reflection)
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
    
    @retry(stop_max_attempt_number=5)
    def reflect(self, payoffs, idx):
        format_assertion = False
        while not format_assertion:

            prompt = REFLECTION.replace("{game_description}", self.game_description).replace("{payoffs}", ", ".join(map(str, payoffs))).replace("{idx}", str(idx)).replace("{reflection}", self.reflection)
            response = self.llm_handler.chat(prompt)
            json_str = self.parse_action(response)
            format_assertion = self.format_assertion(json_str, ['reflection']) 
        self.reflection = json.loads(json_str)['reflection']
    
    def save_reflection(self, epoch):
        print(self.reflection_path)
        if 'reflection_' in self.reflection_path:
            self.reflection_path = '_'.join(self.reflection_path.split('_')[:-1]) + f"_{epoch}.json"
        else:
            self.reflection_path = self.reflection_path.replace('.json', f"_{epoch}.json")
        with open(self.reflection_path, 'w') as f:
            json.dump(self.reflection, f)