import logging
import os
from typing import List, Tuple, Dict
import threading
import json

from GameCode.utils.code_drafting import code_drafting
from GameCode.debug.test_env import test_with_repetition
from GameCode.validation.validate_env import validate_code
from GameCode.debug.debug_code import debug_code
from GameCode.utils.structure_description import structurize_description
from GameCode.retrieval.retrieve import retrieve
from GameCode.utils.formatting import unwrap_code, replace_print_with_pass
from Utils.LLMHandler import LLMHandler
from GameCode.retrieval.retrieve_snippets import CodeSnippetRetriever

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_with_repetition(kwargs) -> Tuple[bool, str, Dict]:
    latest_code, latest_performance = None, None

    # read the configs
    configs = kwargs.get("configs", {})
    repetition = configs.get("repetition", 3)

    # set up the LLM handler
    llm_model = configs.get("llm_model", None)
    if llm_model is None:
        logger.error("LLM model is not provided, use the default model gpt-4o-2024-08-06")
        llm_model = "gpt-4o-2024-08-06"
    kwargs["llm_handler"] = LLMHandler(llm_model=llm_model)

    # set up the code retriever
    code_retriever = CodeSnippetRetriever(\
        configs['retrieval']['library_path'])
    code_retriever.build_index()
    kwargs["code_retriever"] = code_retriever
    
    # create the game code with repetition
    for i in range(repetition):
        try:
            is_success, latest_code, latest_performance = create_pipeline(**kwargs)
            if is_success:
                break
        except Exception as e:
            logger.error(f"Error in creating game code in {i+1}th trial: {e}")
    return is_success, latest_code, latest_performance


def create_pipeline(
        llm_handler: LLMHandler, 
        game_name: str,
        game_description_or_file_path: str, 
        game_code_path: str, 
        temp_dir: str, 
        configs: Dict,
        code_retriever: CodeSnippetRetriever,
        structurize_game_desc: bool = True,
        skip_debug: bool = False,
        skip_validation: bool = False,
        **kwargs
    ) -> Tuple[bool, str, Dict]:
    """
    Create a pipeline to generate and test game code
    Notice: the file path shall use single slash or double backslashes
    """
    # set up logging
    logger.info(f"Creating game code for {game_name} in thread {threading.current_thread().name}")
    llm_handler.set_log_path(os.path.join(temp_dir, f"{game_name}_llm_chat.log"))

    # read the game description from file if it's a valid path
    if os.path.exists(game_description_or_file_path):
        try:
            with open(game_description_or_file_path, 'r', encoding='utf-8') as f:
                game_description = f.read()
        except:
            raise ValueError(f"Failed to read the game description from {game_description_or_file_path}")
    else:
        logger.info(f"Using the provided game description string for {game_name}")
        game_description = game_description_or_file_path
    
    # Step 1: structurize the game description
    if structurize_game_desc:
        struct_game_desc = structurize_description(game_description, llm_handler)
    else:
        struct_game_desc = game_description
    with open(os.path.join(temp_dir, f"{game_name}.md"), 'w', encoding="utf-8") as f:
        f.write(struct_game_desc)

    # Step 2: retrieve examples
    example_str, example_codes = retrieve(
        llm_handler, struct_game_desc, 
        configs['retrieval']['library_path'],
        configs['retrieval']['init_retrieval_num'],
        configs['retrieval']['final_example_num'],
    )
        
    # Step 3: draft the initial code
    # read game engine code
    env_code_path = os.path.join('GameEngine', 'mini_env.py')
    with open(env_code_path, 'r') as f:
        base_game_code = f.read()
    game_engine_code = unwrap_code(base_game_code, 'game engine')
    code_template = unwrap_code(base_game_code, 'code template')
    # draft the initial code
    game_code = code_drafting(
        llm_handler, struct_game_desc, example_str, game_engine_code, 
        code_template, 
        llm_model_for_init_draft=configs.get('init_llm_model', None),
        refine_num=configs.get('self_refinement_repetition', None)
    )
    # save the initial code to a temporary file
    temp_id = save_new_temp_code(game_code, temp_dir, game_name)

    # Apply iterative debugging and validation
    if not skip_debug or not skip_validation:
        is_success, game_code, edit_count, temp_ids, quality_score = iterative_debugging_and_validation(
            game_code, struct_game_desc, example_codes, game_engine_code, llm_handler, temp_dir, game_name, temp_id, 
            configs['test_and_validate'], code_retriever=code_retriever)
    else:
        is_success = True
        edit_count = 0
        quality_score = -1
        temp_ids = [temp_id]
        logger.info(f"Skipping debugging and validation for {game_name}")
        
    # Save the final game code
    with open(game_code_path, 'w', encoding="utf-8") as f:
        f.write(game_code)

    # Clean up temporary files
    clean_up_temp_files(temp_dir, game_name, temp_ids)

    if not is_success:
        logger.info(f"Failed to generate a working game code for {game_name} after {edit_count} edits")
    else:
        logger.info(f"Successfully generated a working game code for {game_name} after {edit_count} edits")

    performance_dict = {
        "game_name": game_name,
        "edit_count": edit_count,
        "max_score_so_far": quality_score,
    }
    performance_dict.update(llm_handler.get_usage())
    return is_success, game_code, performance_dict          


def iterative_debugging_and_validation(
        game_code: str, game_desc: str, example_codes: List[str], engine_code: str,
        llm_handler, temp_dir: str, game_name: str, temp_id: str, configs: Dict, code_retriever=None
        ) -> Tuple[bool, str, int, str, str, List[str]]:
    """
    Function to iteratively debug and validate the generated game code.
    """
    edit_count = 0
    is_success = False
    temp_ids = [temp_id]
    is_first_validation = True
    validation_candidate_code_path = ''
    test_candidate_code_path = ''
    validation_analysis_history = []

    # unpack the configs
    max_edits = configs['max_edits']
    credits = configs['init_credits']
    loop_penalty = configs['reward_and_penalty']['loop']
    validate_reward = configs['reward_and_penalty']['validate']
    execute_reward = configs['reward_and_penalty']['execute']

    test_repetition = configs['test']['repetition']
    test_timeout = configs['test']['timeout']
    debug_example_num = configs['test'].get('debug_example_num', 2)

    enable_info = configs.get('enable_info', True)
    enable_validation = configs.get('enable_validation', True)
    validate_repetition = min(configs['validate'].get('repetition', test_repetition), test_repetition)
    
    while (not is_success) and (max_edits > edit_count) and (credits > 0):
        # need to be successful in each test repetition
        is_success, gameplay_log_files, error_log_files, suceess_num = test_with_repetition(
            temp_dir, game_name, temp_id, repetition=test_repetition, timeout=test_timeout,
            enable_info=enable_info)
        # apply the credits change during the test
        credits += suceess_num * execute_reward

        if not is_success:
            # read the error message and propose edits
            error_log_path = error_log_files[-1]
            with open(error_log_path, 'r', encoding="utf-8") as f:
                error_msg = f.read()
            game_code = debug_code(llm_handler, game_code, error_msg, game_desc, 
                                     example_codes[:min(debug_example_num, len(example_codes))], engine_code)
            game_code = replace_print_with_pass(game_code)
            edit_count += 1
            credits -= 1

            # if the error_msg contains "infinite loop", deduct more credits
            if "infinite loop" in error_msg:
                credits += loop_penalty  # penalty is a negative number

            # we need to save the new code to another file
            # otherwise the test_env function will not be able to import the new code
            temp_id = save_new_temp_code(game_code, temp_dir, game_name)
            temp_ids.append(temp_id)
        else:
            if is_first_validation:
                is_first_validation = False
                logger.info(f"Validation for {game_name}, first-time, current edit count: {edit_count}, current llm usage: {json.dumps(llm_handler.get_usage())}")
                # save the current code as a special copy
                no_val_code_path = os.path.join(temp_dir, f"{game_name}-no-val.py")
                with open(no_val_code_path, 'w', encoding="utf-8") as f:
                    f.write(game_code)
            else:
                logger.info(f"Validation for {game_name}, current edit count: {edit_count}")

            # save the current code as a candidate
            test_candidate_code_path = os.path.join(temp_dir, f"{game_name}-test-pass.py")
            with open(test_candidate_code_path, 'w', encoding="utf-8") as f:
                f.write(game_code)

            if not enable_validation:
                # save the current code as a candidate
                validation_candidate_code_path = os.path.join(temp_dir, f"{game_name}-validation-pass-1.py")
                with open(validation_candidate_code_path, 'w', encoding="utf-8") as f:
                    f.write(game_code)  
            else:
                # validate the game code with each gameplay log
                for valid_idx, play_log_path in enumerate(gameplay_log_files[: validate_repetition]):
                    with open(play_log_path, 'r', encoding="utf-8") as f:
                        game_play_log = f.read()
                    is_success, game_code, analysis_dict = \
                        validate_code(llm_handler, game_desc, game_code, game_play_log, 
                                      config=configs['validate'], code_retriever=code_retriever)
                    validation_analysis_history.append(analysis_dict)
                    logger.info(f"Validation result for {game_name}-{temp_id}: {is_success}")
                    if not is_success:
                        game_code = replace_print_with_pass(game_code)
                        edit_count += 1
                        credits -= 1
                        temp_id = save_new_temp_code(game_code, temp_dir, game_name)
                        temp_ids.append(temp_id)
                        break
                    else:
                        # award the credits if the validation is successful
                        credits += validate_reward 
                        # save the current code as a candidate
                        validation_candidate_code_path = os.path.join(temp_dir, f"{game_name}-validation-pass-{valid_idx}.py")
                        with open(validation_candidate_code_path, 'w', encoding="utf-8") as f:
                            f.write(game_code)   
        
        # no matter we succeed or not, 
        # we clean up the log files after each edit test
        for log_file in gameplay_log_files:
            if os.path.exists(log_file):
                os.remove(log_file)
        for error_log_file in error_log_files:
            if os.path.exists(error_log_file):
                os.remove(error_log_file)

    game_code, quality_score = select_final_code(temp_dir, game_name, test_repetition, validation_candidate_code_path, test_candidate_code_path)
    save_analysis_history(temp_dir, game_name, validation_analysis_history)

    return is_success, game_code, edit_count, temp_ids, quality_score

def select_final_code(temp_dir: str, game_name: str, test_repetition: int, 
                      validation_candidate_code_path: str, test_candidate_code_path: str
                      ) -> Tuple[str, int]:
    """
    Select the final game code based on validation success.
    """
    for valid_idx in range(test_repetition, -2, -1):  # make it end at -1
        if os.path.exists(os.path.join(temp_dir, f"{game_name}-validation-pass-{valid_idx}.py")):
            validation_candidate_code_path = os.path.join(temp_dir, f"{game_name}-validation-pass-{valid_idx}.py")
            break
    if os.path.exists(validation_candidate_code_path):
        with open(validation_candidate_code_path, 'r', encoding="utf-8") as f:
            return f.read(), valid_idx + 1
    elif os.path.exists(test_candidate_code_path):
        with open(test_candidate_code_path, 'r', encoding="utf-8") as f:
            return f.read(), 0
    return "", -1


def clean_up_temp_files(temp_dir: str, game_name: str, temp_ids: List[str]) -> None:
    """
    Clean up temporary files created during the pipeline.
    """
    for temp_id in temp_ids:
        temp_file_path = os.path.join(temp_dir, f"{game_name}_{temp_id}.py")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def save_new_temp_code(game_code: str, temp_dir: str, game_name: str
                        ) -> str:
    """
    Save the game code to a new temporary file
    """
    import uuid
    temp_id = uuid.uuid4().hex
    temp_code_path = os.path.join(temp_dir, f"{game_name}_{temp_id}.py")
    with open(temp_code_path, 'w', encoding="utf-8") as f:
        f.write(game_code)
    return temp_id

def save_analysis_history(temp_dir: str, game_name: str, analysis_history: List[Dict]) -> None:
    """
    Save the analysis history to a json file
    """
    analysis_history_path = os.path.join(temp_dir, f"{game_name}_analysis_history.json")

    # remove None from the history
    analysis_history = [item for item in analysis_history if item is not None]

    # read the existing history if exists
    if os.path.exists(analysis_history_path):
        with open(analysis_history_path, 'r', encoding="utf-8") as f:
            existing_history = json.load(f)
        analysis_history = existing_history + analysis_history

    with open(analysis_history_path, 'w', encoding="utf-8") as f:
        json.dump(analysis_history, f, indent=4)