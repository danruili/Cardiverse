PROMPT_MUTATE_PROMPT = """
{thinking_style}. {mutation_prompt}

INSTRUCTION: 
```markdown
{instruction}
```
- Don't make up game descriptions in the instruction, as it will be provided in downstream tasks.
- Wrap up your mutated instruction in a markdown block.
"""

GAME_MUTATION_PROMPT_CORE = """You are a good card game designer, and you are asked to mutate a given card game description."""

CONCEPT_DESIGN_PROMPT_CORE = """You are a good card game designer, please design a novel game concept instance based on your previous summary."""


if __name__ == "__main__":
    import json
    from Utils.LLMHandler import LLMHandler
    from GameCode.utils.formatting import extract_from_language

    thinking_style_path = "GameIdea/llm_op/base_thinking_styles.json"
    mutation_prompt_path = "GameIdea/llm_op/base_mutation_prompts.json"
    # load thinking styles and mutation prompts
    with open(thinking_style_path, "r", encoding="utf-8") as f:
        thinking_styles = json.load(f)
    with open(mutation_prompt_path, "r", encoding="utf-8") as f:
        mutation_prompts = json.load(f)

    # randomly sample combinations of thinking styles and mutation prompts
    import random
    prompts = []
    for i in range(35):
        thinking_style = random.choice(thinking_styles)
        mutation_prompt = random.choice(mutation_prompts)
        prompt = PROMPT_MUTATE_PROMPT.format(
            thinking_style=thinking_style,
            mutation_prompt=mutation_prompt,
            instruction=CONCEPT_DESIGN_PROMPT_CORE,
        )
        prompts.append(prompt)
    
    # call LLM to generate the mutated game descriptions
    llm_handler = LLMHandler()
    results = []
    for i, prompt in enumerate(prompts):
        print(f"Prompt {i+1}: {prompt}")
        response = llm_handler.chat(prompt)
        markdown_content = extract_from_language(response, "markdown")
        results.append(markdown_content)

    # save the results to json
    with open("GameGraph/CardGame/llm_op/mutated_design_prompts.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)