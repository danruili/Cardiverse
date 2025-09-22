from Utils.LLMHandler import LLMHandler
from typing import List, Union

"""
Reference:
https://github.com/OpenAutoCoder/Agentless/blob/main/agentless/repair/repair.py
"""

PROMPT_JS = """
You are a wonderful game code programmer. You should fix the bug in a given code based on error message. 

# Game Engine Code
The game code is inherited from this. You should use this as a reference.
```python
{game_engine_code}
```

# Example Code
This is the code of other game examples. You should use this as a reference.
{example_code}


# code
```javascript
{code}
```

# error message
{error}


Please first localize the bug based on the issue statement, and then generate *SEARCH/REPLACE* edits to fix the issue.

Every *SEARCH/REPLACE* edit must use this format:
1. The start of search block: <<<<<<< SEARCH
2. A contiguous chunk of lines to search for in the existing source code
3. The dividing line: =======
4. The lines to replace into the source code
5. The end of the replace block: >>>>>>> REPLACE

Here is an example:

```javascript
<<<<<<< SEARCH
this.scene.physics.add.existing(this);
this.scene.physics.add.collider(this, this.scene.platforms);
=======
this.scene.physics.add.existing(this);
this.setCollideWorldBounds(true).setBounce(1).setVelocity(100);
this.scene.physics.add.collider(this, this.scene.platforms);
>>>>>>> REPLACE
```

Please note that the *SEARCH/REPLACE* edit REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the *SEARCH/REPLACE* edit in blocks ```javascript...```.
"""

FORMAT_PYTHON = """
Please first localize the modification (if any), and then generate *SEARCH/REPLACE* edits to fix the issue.

Every *SEARCH/REPLACE* edit must use this format:
1. The start of search block: <<<<<<< SEARCH
2. A contiguous chunk of lines to search for in the existing source code, WITH ORIGINAL INDENTATION from the source code
3. The dividing line: =======
4. The lines to replace into the source code
5. The end of the replace block: >>>>>>> REPLACE

Here is an example:

original code:
```python
def main():
    def foo():
        print('hello')
    foo()

main()
```   
    
proposed edits, you can see that the indentation is PRESERVED:
```python
<<<<<<< SEARCH
    def foo():
        print('hello')
=======
    def foo():
        print('world')
>>>>>>> REPLACE
```

when adding new lines, include surrounding context and proper indentation:
```python
<<<<<<< SEARCH
main()
=======
main()
print('program finished')
>>>>>>> REPLACE
```

when removing lines, also include surrounding context and proper indentation:
```python
<<<<<<< SEARCH
print('program started')
main()
=======
main()
>>>>>>> REPLACE
```
Please note that the *SEARCH/REPLACE* edit REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the *SEARCH/REPLACE* edit in blocks ```python...```.
"""

PROMPT_PYTHON = """
You are a wonderful game code programmer. You should fix the bug in a given code based on error message.

# Game Engine Code
The game code is inherited from this. You should use this as a reference.
```python
{game_engine_code}
```

# Example Code
This is the code of other game examples. You should use this as a reference.
{example_code}

# Your game description
{description}

# Your game code
```python
{code}
```

# error message
{error}

# notes
{notes}

""" + FORMAT_PYTHON


def propose_edits(llm_handler: LLMHandler, 
                  code: str, 
                  error: str, 
                  target_path: str = None,
                  engine_code: str = "(not provided)",
                  example_code: Union[str, List[str]] = "(not provided)",
                  language: str = "javascript",
                  description: str = "(not provided)",
                  notes: str = "(no notes provided)"
                  ) -> str:
    
    # construct the example code string
    example_code_str = ""
    if isinstance(example_code, str):
        example_code_str = "```python\n" + example_code + "\n```"
    else:
        for i, example in enumerate(example_code):
            example_code_str += f"```python\n{example}\n```\n"

    script_prompt = PROMPT_PYTHON if language == "python" else PROMPT_JS
    script_prompt = script_prompt.replace("{code}", code).replace("{error}", error)\
        .replace("{description}", description).replace("{notes}", notes)\
        .replace("{game_engine_code}", engine_code).replace("{example_code}", example_code_str)
    raw_content = llm_handler.chat(script_prompt)
    result = raw_content

    if target_path:
        with open(target_path, 'w') as f:
            f.write(result)
    return result



