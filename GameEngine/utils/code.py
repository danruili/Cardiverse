import re
import os


def extract_from_json(raw_content):
    return extract_from_language(raw_content, 'json')

def extract_from_python(raw_code: str) -> str:
    python_codes = re.findall(r'```python\n(.*?)\n```', raw_code, re.DOTALL)
    code = "\n".join(python_codes)
    return code

def extract_from_language(raw_content, language=''):
    try:
        text = re.findall(r'```' + language + r'\s+(.*?)\s+```', raw_content, re.DOTALL)[-1]
    except:
        text = raw_content
    return text


def unwrap_code(code: str, label="code template") -> str:
    begin_spliter = f'"""Beginning of the {label}"""'
    end_spliter = f'"""End of the {label}"""'
    try:
        new_code = code.split(begin_spliter)[1]
        new_code = new_code.split(end_spliter)[0]
        return new_code
    except:
        return code
    
env_code_path = os.path.join('GameEngine', 'env.py')
with open(env_code_path, 'r') as f:
    base_game_code = f.read()
game_engine_code = unwrap_code(base_game_code, 'game engine')

code_ending='''\n"""End of the game code"""'''
code_header = '''\n"""Beginning of the game code"""\n'''

def wrap_env_code(code: str) -> str:
    code = unwrap_code(code, 'game code')

    # remove redundant "\n" at the beginning and end of the code
    code = code.strip("\n")

    # replace the class name in the code_ending
    code_footer = code_ending

    # combine the code_header, code, code_ending
    code = game_engine_code + code_header + code + code_footer
    
    return code


def try_read_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return file_path