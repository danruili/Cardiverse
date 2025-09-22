from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from typing import List, Tuple
from GameplayAI.utils.extract import extract_from_language


# assemble prompt
system_prompt = """
Read the given game description and summarize all possible actions that a player can take in a single turn.

Example Output:
```markdown
1. Draw a card from the deck.
2. Play a card that has bigger value than the card on the top of the discard pile.
3. Ask the opponent if they have a card with the same value as the card on the top of the discard pile.
```
"""

def extract_action_from_desc(
        desc: str, llm_handler: LLMHandler
        ) -> str:
    chat_seq = ChatSequence()
    chat_seq.append(Message("system", system_prompt))
    chat_seq.append(Message("user", desc))
    actions = llm_handler.chat(chat_seq)
    actions = extract_from_language(actions, 'markdown')
    return actions