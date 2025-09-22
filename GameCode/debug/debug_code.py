from retrying import retry
from GameCode.debug.ApplyEdits import apply_edits
from GameCode.debug.ProposeEdits import propose_edits
from GameCode.utils.formatting import unwrap_code, wrap_code

    
DEBUG_NOTES = """
- If you encouter NoneType error, ValueError or any other exceptions when parsing the action string, you shall carefully examine and design the legal action space and the action string format. Don't raise exceptions or skip the error when parsing the action string. 
- Verify the legalness of the action in get_legal_actions() functions. Don't re-validate the action anywhere else.
"""

@retry(stop_max_attempt_number=3)
def debug_code(llm_handler, game_code, error, game_desc, example_code, game_engine_code):
    if isinstance(example_code, str):
        example_core_code = unwrap_code(example_code)
    else:
        example_core_code = [unwrap_code(code) for code in example_code]
    core_code = unwrap_code(game_code)
    proposed_edits = propose_edits(
        llm_handler, core_code, error, 
        example_code=example_core_code,
        engine_code=game_engine_code,
        language="python", 
        description=game_desc,
        notes=DEBUG_NOTES
        )
    new_core_code = apply_edits(proposed_edits, core_code, "python")
    new_code = wrap_code(new_core_code)
    return new_code



