
"""
Simplified from
https://github.com/OpenAutoCoder/Agentless/blob/main/agentless/util/postprocess_data.py
"""

def extract_snippets(raw_content, language="javascript"):
    # Extract all code snippets from the raw content
    prefix = f"```{language}"
    suffix = "```"
    final = []
    code = raw_content

    while code.find(prefix) != -1:
        start = code.find(prefix)
        end = code.find(suffix, start + len(prefix))
        snippet = code[start+len(prefix):end]
        final.append(snippet)
        code = code[:start] + code[end + len(suffix):]

    final = "".join(final)
    return final

def parse_instructions(instructions):
    # extract the search and replace instructions,
    # there might be multiple search and replace instructions
    search = []
    replace = []
    prefix = "<<<<<<< SEARCH"
    suffix = ">>>>>>> REPLACE"
    splitter = "======="
    while instructions.find(prefix) != -1:
        start = instructions.find(prefix)
        end = instructions.find(suffix, start + len(prefix))
        snippet = instructions[start + len(prefix):end]
        search.append(snippet.split(splitter)[0])
        replace.append(snippet.split(splitter)[1])
        instructions = instructions[:start] + instructions[end + len(suffix):]
    return search, replace


def apply_search_replace(code, search, replace):
    # apply the search and replace instructions to the code
    for s, r in zip(search, replace):
        # # remove the ending \n from the replace string
        # r = r.strip()
        # if the search string is empty, then append the replace string
        if len(s.strip()) == 0:
            code = code + r
        else:
            code = code.replace(s, r)
    return code

def apply_edits(raw_instructions, code, language="javascript"):
    instructions = extract_snippets(raw_instructions, language)
    search, replace = parse_instructions(instructions)
    new_code = apply_search_replace(code, search, replace)
    return new_code


# Test the apply_edits function
if __name__ == "__main__":
    from GameCode.debug.ApplyEditsTestCases import example_code, example_code2, example_code3, example_instructions
    new_code = apply_edits(example_instructions, example_code)
    print(new_code)
    new_code2 = apply_edits(example_instructions, example_code2)
    print(new_code2)
    new_code3 = apply_edits(example_instructions, example_code3)
    print(new_code3)