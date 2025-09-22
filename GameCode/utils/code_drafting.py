from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from GameCode.utils.formatting import extract_from_python, wrap_code, replace_print_with_pass
from typing import List, Tuple

INIT_PROMPT = """
You are a card game programmer tasked with implementing a card game based on the given description. Using the provided class templates, your goal is to write only the necessary child classes and implement only the methods indicated with `TODO` comments.

**Instructions:**
- Include only the methods you need to override from the provided class templates.
- Respond with complete, runnable Python code.
- Do **not** include TODOs, placeholders, or explanations; output only the final code.

**Code Environment:**
- These code belongs to a larger game framework. Use them as reference only. Don't include them in your response.
```
{environment_code}
```

**Code Template:**
- Only modify or implement the methods specified with `TODO` comments to complete the game logic.
```
{python_classes}
```

**Examples for Reference:**  
Use these examples as a guide for response format and method implementation.
{examples}

---

### Your Task
Based on the following game description, implement the required classes and methods:

**Game Description:**
```
{game_description}
```

### Note:
- Do **not** raise exceptions (e.g., `ValueError`) when parsing action strings. Instead, ensure the legal action space and action string format are appropriately structured.
"""

def code_drafting(
        llm_handler: LLMHandler, 
        game_description: str,
        examples_str: str,
        game_engine_code: str,
        code_template: str,
        llm_model_for_init_draft: str = None,
        refine_num: int = 2
    ) -> Tuple[str, str, List[str]]:
    """
    Create a card game environment using the game description
    Returns the game code and the structured game description
    """

    if not llm_model_for_init_draft:
        llm_model_for_init_draft = llm_handler.llm_model
    
    # include examples in prompt
    prompt = INIT_PROMPT.replace('{examples}', examples_str)\
        .replace('{python_classes}', code_template)\
        .replace('{environment_code}', game_engine_code)\
        .replace('{game_description}', game_description)
   
    # get the first draft
    response = llm_handler.chat(prompt, model=llm_model_for_init_draft)

    # refine the code
    code = naive_refine(prompt, response, llm_handler, refine_num)

    # wrap the code
    code = wrap_code(code)

    # replace print statements with pass to avoid unwanted printing during tests
    code = replace_print_with_pass(code)
    return code


REFINE_PROMPT_NAIVE = """
Refine your code output
- You should complete any missing methods in the code draft
- fix any potential bugs. Check if empty deck will cause any issue, or recycling cards from the discard pile will cause infinite loops. If so, you should probably decide the winner/loser when the deck is empty.
- Add more logger.info() in the code to act as a game commentator. Remember to only log public information. Don't log in get_legal_actions() methods.
"""


def naive_refine(prompt: str, 
                 response: str,
                 llm_handler: LLMHandler, 
                 refine_num: int = 2
                 ) -> str:
    # refine the code
    sequence = ChatSequence()
    sequence.append(Message('user', prompt))
    sequence.append(Message('assistant', response))
    sequence.append(Message('user', REFINE_PROMPT_NAIVE))
    for _ in range(refine_num):
        response = llm_handler.chat(sequence)
        sequence.append(Message('assistant', response))
        sequence.append(Message('user', REFINE_PROMPT_NAIVE))
    return extract_from_python(response)
