from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from typing import List, Tuple
import json
from retrying import retry
from GameplayAI.utils.extract import extract_from_language


# assemble prompt
system_prompt = """
Read the given game description or code to answer the following question: In this game, winners shall maximize or minimize the payoff in payoff calculation?
Be careful with the minus signs in the payoff calculation. In some games, winner get zero payoff and losers get negative payoff. In such cases, the winners shall maximize the payoff.

Example Output, you shall return the following JSON object, where the value of "maximize" is either true or false:
```json
{
    "maximize": true
}
```
"""

user_prompt = """

# Game Code
{code}
"""

@retry(wait_fixed=2000, stop_max_attempt_number=3)
def max_or_min(
        desc: str, code:str, llm_handler: LLMHandler
        ) -> bool:
    chat_seq = ChatSequence()
    chat_seq.append(Message("system", system_prompt))
    chat_seq.append(Message("user", user_prompt.replace("{code}", code)))
    actions = llm_handler.chat(chat_seq)
    actions = extract_from_language(actions, 'json')
    actions = json.loads(actions)
    is_max = actions["maximize"]
    return is_max

def max_or_min_by_file_paths(
        desc_file_path: str, code_file_path: str, llm_handler: LLMHandler
        ) -> bool:
    with open(desc_file_path, 'r', encoding='utf-8') as f:
        desc = f.read()
    with open(code_file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    return max_or_min(desc, code, llm_handler)


if __name__ == "__main__":
    llm_handler = LLMHandler()
    import os

    folder_path = r"GameLib\gen-best-0-60"

    # iterate over all subfolders
    for subfolder in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder)
        if os.path.isdir(subfolder_path):
            desc_file_path = os.path.join(subfolder_path, f"{subfolder}.txt")
            code_file_path = os.path.join(subfolder_path, f"{subfolder}.py")
            is_max = max_or_min_by_file_paths(desc_file_path, code_file_path, llm_handler)
            print(subfolder, is_max)