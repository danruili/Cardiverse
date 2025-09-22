import os
import logging

from GameCode.retrieval.naive_retrieval import get_similar_texts
from GameCode.utils.formatting import unwrap_code
from typing import Literal
from Utils.LLMHandler import LLMHandler

RETRIEVAL_METHODS = Literal['naive']

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def retrieve(
        llm_handler: LLMHandler, 
        game_description: str,
        library_path: str,
        retrieval_num: int,
        final_example_num: int,    
        retrieval_method: RETRIEVAL_METHODS = 'naive',
        ) -> tuple[str, list]:

    # fetch similar games as examples
    if not library_path:
        logger.error("Library path is not provided, using the default path")
        library_path = os.path.join('data', 'code_generation', 'example_lib', 'indexing')

    lib_index_dir = os.path.join(library_path, 'indexing')
    os.makedirs(lib_index_dir, exist_ok=True)

    top_file_names = get_similar_texts(
        game_description, 
        llm_handler, 
        index_dir=lib_index_dir,
    )
    retrieved_game_descs = []
    retrieved_code = []
    retrieved_file_names = []
    logger.info(f"Retrieved top files: {top_file_names}")
    for file_name in top_file_names[:retrieval_num]:
        with open(os.path.join(lib_index_dir, file_name), 'r', encoding='utf-8') as f:
            retrieved_game_descs.append(f.read())
        with open(os.path.join(library_path, file_name.replace('.md', '.py')), 'r', encoding='utf-8') as f:
            retrieved_code.append(f.read())
        retrieved_file_names.append(file_name)

    # include examples in prompt
    if retrieved_game_descs and retrieved_code:
        if retrieval_method == 'naive':
            final_num = min(final_example_num, len(retrieved_game_descs))
            examples = naive_example_list(retrieved_game_descs[:final_num], retrieved_code[:final_num])
        else:
            raise ValueError(f"Invalid retrieval method: {retrieval_method}")
        return examples, retrieved_code
    else:
        logger.info("No retrieved examples found.")
        return '', retrieved_code


def naive_example_list(
        retrieved_game_descs, retrieved_code
        ) -> str:
    examples = ""
    for i, (desc, code) in enumerate(zip(retrieved_game_descs, retrieved_code)):
        code_unwrapped = unwrap_code(code)
        examples += f"\n**Example {i + 1}**\n\n_Input:_\n```{desc} ```\n\n_Output:_\n```python{code_unwrapped}```\n"
    return examples

