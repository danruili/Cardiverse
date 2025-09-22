import traceback
import logging
import json
from typing import Union, Tuple
from retrying import retry

from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from GameEngine.env import LLMGameStateEncoder

general_system_message = "You are an action-value engineer trying to write action-value functions in python. Your goal is to write an action-value function that will help the agent decide actions in a card game."

func_template = """
# The game
{game_description}

# The policy
In this action-value function, you will focus on the following policy of the game:
{game_policy}

# The input
The function should be able to take a game state and a planned game action as input. The input should be as follows:
{input_description}

# The output
You should return a reward value ranging from 0 to 1. It is an estimate of the probability of winning the game. 
The closer the reward is to 1, the larger chance of winning we will have.
Try to make the output more continuous.
The reward should be calculated based on both the game state and the given game action.

# Response format
You should return a python function in this format:
```python
def score(state: dict, action: str) -> float:
    pass
    return result_score
```
"""

func_refine_template = """
Here are some criteria for the code review:
- No TODOs, pass, placeholders, or any incomplete code;
- Include all code in the score function. Don't create custom class or functions outside;
- the last line should be "return result_score", and the result_score should be a float;
- You can only use the following modules: math, numpy (as np), random;
- no potential bugs;

First, you should check the above criteria one by one and review the code in detail. Show your thinking process.
Then, if the codes are perfect, please end your response with the following sentence:
```
Result is good.
```

Otherwise, you should end your response with the full corrected function code. 
"""

bug_fix_template = """
Now please fix the bug in a card game code.

# Goal
The goal of this function is to calculate action-value function for a card game. The action-value function should focus on the following policy of the game:
```
{game_policy}
```

# Given Code
```python
{code}
```

# Given 'state' input
```
{state_input}
```

# Given 'action' input
```
{action_input}
```

# Error Message when running the code
```
{error_message}
```

Please fix the bug and end your response with the full corrected function code.
"""

test_refine_template = """
In the testing of this function, we found the winning rate is {winning_rate:.2f}%, while the winning rate of a random player is {random_winning_rate:.2f}%.

Please refine the function and end your response with the full corrected function code.

You can think in the following ways:
(1) If the winning rate is near random player, then you may rewrite the entire function;
(2) If the winning rate is higher than random player, then you may try re-weighing the parameters/factors in the function;
"""


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LLMQFunc:

    def __init__(self, game_description: str,
                 game_policy: str,
                 input_description: str,
                 code: str = None,
                 enable_fix: bool = True,
                 llm_handler: LLMHandler = None):
        """
        Given the game description, policy, and input description, generate the code of scoring function.
        :param game_description: describe the game
        :param game_policy: describe the policy
        :param input_description: describe the input
        :param code: the code of this feature, if not provided, the above three parameters are required.
        :param enable_fix: whether to enable the bug fix feature
        """
        self.code = None
        self.compiled_code = None
        self.game_description: str = game_description
        self.game_policy: str = game_policy
        self.input_description = input_description
        self.enable_fix: bool = enable_fix
        self.active: bool = True
        self.llm_handler = llm_handler

        # if code is provided, use the code directly. Otherwise, generate the code.
        if code is not None:
            self.code = code
            return
        else:
            self.code = self.create_code()

    def __call__(self, state: dict, action: str) -> float:
        return self.score(state, action)

    def __repr__(self):
        return self.code
    
    def deactivate(self):
        self.active = False
    
    @retry(stop_max_attempt_number=3)
    def create_code(self):
        logger.info("Generating code for the feature...")
        if self.llm_handler is None:
            self.llm_handler = LLMHandler()
        llm_handler = self.llm_handler

        # initial code
        prompt = func_template.replace("{game_description}", self.game_description) \
            .replace("{game_policy}", self.game_policy) \
            .replace("{input_description}", self.input_description)
        chat_seq = ChatSequence()
        chat_seq.append(Message(role="system", content=general_system_message))
        chat_seq.append(Message(role="user", content=prompt))
        result1 = llm_handler.chat(chat_seq)

        # refine the code 
        chat_seq.append(Message(role="assistant", content=result1))
        chat_seq.append(Message(role="user", content=func_refine_template))
        result2 = llm_handler.chat(chat_seq)

        # remove delimiters from the result
        code1 = self._sanitize_output(result1)
        code2 = self._sanitize_output(result2)

        if code1 != "" and code2 == "": # no need to refine
            return code1
        elif code1 != "" and code2 != "": # refined
            return code2
        else:
            raise Exception("No code is generated")

    @staticmethod
    def _sanitize_output(text: str) -> str:
        try:
            _, after = text.split("```python")
            result = after.split("```")[0]
            # insert a # before each print() statement
            result = result.replace("print(", "#print(")
            return result
        except ValueError:
            return ""

    @retry(stop_max_attempt_number=3)
    def score(self, state: dict, action: str) -> float:
        if self.code is None:
            raise Exception("No code generated")
        if not self.active:
            return 0
    
        # compile the code if not compiled
        if self.compiled_code is None:
            self.compiled_code, error_message = self.compile_code(self.code)

        # run the code
        if self.compiled_code is not None:
            result, error_message = self.run_code(self.compiled_code, state, action)
        else:
            result = None

        # if the result is None, try to fix the bug
        edit_count = 0
        while result is None and edit_count < 5:
            if not self.enable_fix:
                # deactivate the feature if the bug fix is disabled
                logger.warning("The feature is deactivated due to the bug.")
                self.deactivate()
                return 0
            self.code = self.fix_bug(state, action, error_message)
            self.compiled_code, error_message = self.compile_code(self.code)
            if self.compiled_code is not None:
                result, error_message = self.run_code(self.compiled_code, state, action)
            edit_count += 1
            logger.info(f"Bug fixed {edit_count} times.")
        if result is None:
            logger.warning("The feature is deactivated due to the bug is not fixed.")
            self.deactivate()
            return 0
        return result
    
    @staticmethod
    def compile_code(code: str):
        try:
            exec_code = code
            exec_code += "\nresult = score(state, action)\n"
            return compile(exec_code, "<string>", "exec"), None
        except Exception as e:
            error_traceback = traceback.format_exc()
            return None, error_traceback
    
    @staticmethod
    def run_code(compiled_code, state: dict, action: str) -> Tuple[Union[float, None], Union[str, None]]:
        local_vars = {"state": state, "action": action}
        exec_globals = {'math': __import__('math'), 'np': __import__('numpy'), 'random': __import__('random')}
        try:
            exec(compiled_code, exec_globals, local_vars)
            if local_vars["result"] is not None:
                return local_vars["result"], None
            else:
                return None, "None is returned. You should return a float value."
        except Exception as e:
            error_traceback = traceback.format_exc()
            return None, error_traceback
        
    @retry(stop_max_attempt_number=3)
    def fix_bug(self, state: dict, action: dict, error_message: str) -> str:
        if self.llm_handler is None:
            self.llm_handler = LLMHandler()
        llm_handler = self.llm_handler
        bug_fix_prompt = bug_fix_template \
            .replace("{game_policy}", self.game_policy) \
            .replace("{code}", self.code) \
            .replace("{state_input}", str(state)) \
            .replace("{action_input}", json.dumps(action, cls=LLMGameStateEncoder)) \
            .replace("{error_message}", error_message)

        chat_seq = ChatSequence()
        chat_seq.append(Message(role="system", content=general_system_message))
        chat_seq.append(Message(role="user", content=bug_fix_prompt))
        result = llm_handler.chat(chat_seq)
        code = self._sanitize_output(result)
        if code == "":
            raise Exception("No code is received")
        return code
