import os
import shutil
import ast
from tqdm import tqdm

from GameCode.utils.formatting import unwrap_code, extract_from_python
from GameCode.utils.structure_description import structurize_description
from Utils.LLMHandler import LLMHandler
import argparse

MERGE_PROMPT = """
You are a good card game code programmer. You will study the given game descriptions and code function, then you shall augment the code with comments.

You should insert the original related description snippets into the code as comments, only if the code is the direct implementation of the description, for example:
```python
# **Wild Card Eight:** An eight can be played regardless of the top card on the starter pile. 
# The player playing the eight must declare a suit.
if card.rank == '8':
    for suit in ['hearts', 'diamonds', 'clubs', 'spades']:
        legal_actions.append({'action': 'play', 'args':{'card_idx': i, 'target_suit': suit}})
# Requirement: The card must match the suit or rank of the current top card on the starter pile, except for an eight.
elif card.suit == game_state.common.current_suit or card.rank == game_state.common.faceup_cards.target_card.rank:
    legal_actions.append({'action': 'play', 'args':{'card_idx': i}})
```

# Description
{game_description}

# Code
{game_code}

# Output format
Responed with the complete code with comments, wrapped by triple quotes. For example:
```python
<your code here>
```
"""


def comment(code: str, desc: str) -> str:
    """
    This function takes a code snippet and a description and returns a commented version of the code.
    """
    llm_handler = LLMHandler(llm_model='gpt-4o-mini')
    prompt = MERGE_PROMPT.replace('{game_description}', desc).replace('{game_code}', code)
    response = llm_handler.chat(prompt)
    commented_code = extract_from_python(response)
    return commented_code


def update_functions_with_comments(
        code: str, 
        desc: str, 
        exclude_func: list[str] = None, 
        ):
    """
    This function takes Python code, a description, and a list of function names to exclude.
    It will parse the code into an AST, find all functions not in exclude_func, and for each
    such function:
      - Extract its source
      - Pass it to an external 'comment(code, desc)' function to get a commented version
      - Replace the original function in the code with the commented version

    Finally, it returns the updated code as a string.
    """
    if exclude_func is None:
        exclude_func = ['initiation', 'init_deck', 'init_dealing', 'init_deal']

    # Parse the original code into an AST
    tree = ast.parse(code)

    # We'll record the replacements as a list of tuples: (start_line, end_line, replacement_str)
    replacements = []

    # Extract the source code lines
    lines = code.splitlines(keepends=True)

    # For Python 3.8+, ast nodes have end_lineno. If using older Python, consider 'asttokens' library.
    # Assuming Python 3.8+ is available:
    for node in tqdm(ast.walk(tree)):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            if func_name not in exclude_func:
                # Extract the original function source code segment
                func_code = ast.get_source_segment(code, node)

                # Call the external comment function
                commented_func = comment(func_code, desc)

                # Store the replacement
                # Note: lineno and end_lineno are 1-based indices
                start_line = node.lineno
                end_line = node.end_lineno
                replacements.append((start_line, end_line, commented_func))

    # If no replacements, just return the original code
    if not replacements:
        return code

    # Sort replacements by start_line (just to be sure we handle them in order)
    replacements.sort(key=lambda x: x[0])

    # We'll build the new code by iterating over lines and applying replacements
    updated_code_lines = []
    current_line_num = 1
    i = 0

    while i < len(lines):
        line_num = current_line_num
        line = lines[i]

        # Check if there's a replacement starting at this line
        replacement_to_apply = None
        for (start_line, end_line, replaced_code) in replacements:
            if start_line == line_num:
                replacement_to_apply = (start_line, end_line, replaced_code)
                break

        if replacement_to_apply is not None:
            # Apply this replacement
            start_line, end_line, replaced_code = replacement_to_apply

            # Append the replaced code (ensure it ends with a newline if not)
            if not replaced_code.endswith("\n"):
                replaced_code += "\n"
            updated_code_lines.append(replaced_code)

            # Skip the original lines corresponding to the replaced function
            lines_to_skip = end_line - start_line + 1
            i += lines_to_skip
            current_line_num += lines_to_skip

            # Remove this replacement from the list so we don't apply it twice
            replacements.remove(replacement_to_apply)
        else:
            # No replacement at this line, just copy the original line
            updated_code_lines.append(line)
            i += 1
            current_line_num += 1

    updated_code = "".join(updated_code_lines)
    return updated_code

def merge(code, desc):
    core_code = unwrap_code(code)
    new_code = update_functions_with_comments(core_code, desc)
    return new_code

def process_md_py_pairs(source_folder_path):
    # Ensure the target folder exists
    target_folder_path = os.path.join(source_folder_path, 'indexing')
    os.makedirs(target_folder_path, exist_ok=True)

    # List all files in the source folder
    files = os.listdir(source_folder_path)
    
    # Group files by their base name without extension
    grouped_files = {}
    for file in files:
        base_name, ext = os.path.splitext(file)
        if ext in ['.md', '.py']:
            grouped_files.setdefault(base_name, []).append(file)
    
    # Find and process .md and .py pairs
    for base_name, file_list in grouped_files.items():
        if '.md' in [os.path.splitext(f)[1] for f in file_list] and \
           '.py' in [os.path.splitext(f)[1] for f in file_list]:
            
            # Paths of .md and .py files
            md_file_path = os.path.join(source_folder_path, f"{base_name}.md")
            py_file_path = os.path.join(source_folder_path, f"{base_name}.py")
            structure_file_path = os.path.join(target_folder_path, f"{base_name}.md")
            
            # Structure the .md content and save it to the target folder
            with open(md_file_path, 'r', encoding='utf-8') as md_file:
                md_content = md_file.read()
            structured_md_content = structurize_description(md_content, LLMHandler())
            with open(structure_file_path, 'w', encoding='utf-8') as f:
                f.write(structured_md_content)

            # Read the .py content
            with open(py_file_path, 'r', encoding='utf-8') as py_file:
                py_content = py_file.read()
            
            # Merge the contents
            new_code = merge(py_content, structured_md_content)
            
            # Write the merged .py file to the target folder
            target_py_path = os.path.join(target_folder_path, f"{base_name}.py")
            with open(target_py_path, 'w', encoding='utf-8') as target_py_file:
                target_py_file.write(new_code)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process .md and .py pairs and add comments into code.")
    parser.add_argument("--source", help="Source folder containing .md and .py files")
    args = parser.parse_args()

    process_md_py_pairs(args.source)