from retrying import retry
import logging
from typing import Dict
from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from GameCode.debug.ApplyEdits import apply_edits
from GameCode.debug.ProposeEdits import FORMAT_PYTHON
from GameCode.utils.formatting import unwrap_code
from GameCode.validation.parse_validation import extract_analysis_blocks, EMPTY_ANALYSIS
from GameCode.retrieval.retrieve_snippets import CodeSnippetRetriever
from typing import Tuple

VALIDATE_PROMPT = """
You are a card game programmer who verifies code for a card game. You are given a card game description and a part of game play log using the code.

# Task
- You should evaluate step by step to see if the game play log aligns with the rules in the game description.
- Also, examine if the legal action choices in each turn is correct and complete.
- If the game play aligns with the rules, simply return "pass" in the analysis summary.
- If the game play does not align with the rules, you should response in a two-part format: summary and quote(optional). Focus one issue at a time.

# Your game description
```
{game_description}
```

# Your game play log
Note: Only the last several turns of the play log is provided. But if the play log is too short or empty, there might be some errors in the game code.
```
{game_play_log}
```

# Output Format

If the game play log aligns with the rules:
```
***Step by step evaluation***
<your evaluation here>

***Analysis Summary***
```pass```
```

If you doubt the log is too short or empty because of some errors in the game code:
```
***Step by step evaluation***
<your evaluation here>

***Analysis Summary***
```log is too short or empty```
```

Otherwise:
```
***Step by step evaluation***
<your evaluation here>

***Analysis Summary***
Summary:
```text
<summarize the issue>
```
Quote (optional):
```markdown
<quote related game description segment if game play log does not align with the rules>
```
```
"""


CORRECT_PROMPT = """
Based on the analysis, you should correct the code to make the game play log align with the game description.

# Note
- If the player makes invalid moves, you should correct the get_legal_actions(), rather than throwing an error or logging a warning.

# Your code
```python
{code}
```

{additional_examples}

# Output Format
```python
<your code edit here>
```
```python
<there might be multiple edits>
```
...

# Code Edit Instruction
"""+ FORMAT_PYTHON

@retry(stop_max_attempt_number=3)
def validate_code(
    llm_handler: LLMHandler, 
    game_desc: str, 
    code: str, 
    game_play_log: str,
    config: Dict,
    code_retriever: CodeSnippetRetriever,
    last_k_turns: int = 6,
    ) -> Tuple[bool, str, Dict]:
    """
    Returns:
    - bool: whether the code is valid
    - str: the new code if the code is invalid
    - Dict: the analysis blocks extracted from the response
    """
    # unpack configurations
    coding_llm_model = config.get('coding_llm_model', llm_handler.llm_model)
    retrieval_method = config.get('retrieval', {}).get('method', 'none')

    # truncate the log to keep the last few turns
    delimeter = "----------"
    game_play_log = delimeter.join(game_play_log.split(delimeter)[-last_k_turns:])

    # only keep the core code, removing env code
    core_code = unwrap_code(code)

    propose_prompt = VALIDATE_PROMPT.replace('{game_description}', game_desc)\
                                  .replace('{code}', core_code)\
                                  .replace('{game_play_log}', game_play_log)
    raw_content = llm_handler.chat(propose_prompt)

    pass_identifier = """***Analysis Summary***\n```pass```"""
    # if the identifier is found, return the original code
    if pass_identifier in raw_content:
        return True, code, EMPTY_ANALYSIS
    
    # extract analysis blocks for future use
    block_dict = extract_analysis_blocks(raw_content)

    # get additional examples
    try:
        if retrieval_method == 'naive':
            additional_examples = code_retriever.retrieve_as_string(block_dict['markdown_blocks'][0])
        else:
            additional_examples = ""
    except Exception as e:
        logging.error(f"Failed to retrieve additional examples, skipping...{e}")
        additional_examples = ""

    # ask for code correction
    for _ in range(3):
        try:
            sequence = ChatSequence()
            sequence.append(Message("user", propose_prompt))
            sequence.append(Message("assistant", raw_content))
            correction_prompt = CORRECT_PROMPT.replace('{code}', code)\
                                            .replace('{additional_examples}', additional_examples)
            sequence.append(Message("user", correction_prompt))
            raw_correction_content = llm_handler.chat(sequence, model=coding_llm_model)

            # extract code blocks from the correction
            new_block_dict = extract_analysis_blocks(raw_correction_content)
            block_dict['code_blocks'] = new_block_dict['code_blocks']

            # try to apply the edits, if failed, retry
            new_code = apply_edits(raw_correction_content, code, "python")
            if new_code == code and len(block_dict['code_blocks']) > 0:
                raise Exception("Failed to apply the edits")
            else:
                return False, new_code, block_dict
        except Exception as e:
            logging.info("Failed to apply the edits, retrying...")
    
    logging.error("Failed to apply the edits after 3 attempts, assuming the code is correct.")
    return True, code, block_dict
