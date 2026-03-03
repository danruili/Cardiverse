PROMPTS: dict[str, str] = {}

PROMPTS[
    "chain_extraction_init"
] ="""
You are a wonderful card game designer who extract game logic chains from the game description. You will be given a game description and you need to extract the game logic chains step by step.

# Task

Read the following game description and answer the questions: how to win this card game? Please respond with all direct mechanics that contribute or hinder to this. for example: discard all the cards, get highest hand score. Your output should be a JSON object with the following format:
```json
[
    {
        "name": "Name of the game mechanic",
        "type": "<only choose among: Contribute, Hinder, Mixed>",
        "description": "A concise explanation of how the mechanic works",
        "reasoning": "Explain how this mechanic contributes to the goal"
    },
    ...
]
```

Remember to extract mechanics that DIRECTLY relate to the goal. Examples:
```
input: <a UNO game description>
correct extraction: "Empty the hands"
wrong extraction: "Play a matching card" or "Draw 4 cards".
analysis: "Play a matching card" or "Draw 4 cards" should be extracted in future steps.
```
```
input: The main purpose of the game is to remove all cards from the table, assembling them in the tableau before removing them. Initially, 54 cards are dealt to the tableau in ten piles, face down except for the top cards. The tableau piles build down by rank, and in-suit sequences can be moved together. The 50 remaining cards can be dealt to the tableau ten at a time when none of the piles are empty.
correct extraction: "Remove all cards from the table"
wrong extraction: "Move sequences strategically".
```

# Game Description
{game_description}
"""

PROMPTS[
    "chain_extraction_init_check"
] ="""
Check and refine your results based on the following criteria:
(1) Are there any mechanics that are not DIRECTLY related to the goal?

Respond a complete result in the same format as before.
"""

PROMPTS[
    "chain_extraction_subsequent"
] ="""
What are the game mechanics/concept that directly trigger/stop this mechanic: {goal}? Please respond with the direct mechanic that contributes to this. 

- Try your best to extract ALL direct mechanics.
- When evaluating, pay special attention to mechanics that are interesting or unique.
- You can choose from previously extracted mechanics: {previous_mechanics}. But you can also extract new mechanics/concepts.
- Use the same format as before. 
- Usually there are always mechanics or concepts to extract, unless you have reached the end of the chain such as card design or very basic elements.
- If there are no more mechanics or concepts to extract, respond with:
```json
[]
```
"""

PROMPTS[
    "instance_summary"
] = """
**Role**: You are an assistant tasked with summarizing game concept from a list of gameplay mechanics.

**Instructions**:
1. **Input**: You will receive a list of gameplay concept instances. These concepts are often centered around a theme or have similar mechanics.
2. **Output**: Your response should include:
```json
{
    "name": "<The name of the game concept>",
    "description":{
        "common": "<A concise statement that generalizes the core concept or theme common across the listed gameplay concept instances.>",
        "variation": "How the description of given instances vary from the shared common themes."
    }
}
```

# Your input
{input_text}
"""

PROMPTS[
    "instance_summary_in_between"
] = """
You are an assistant tasked with analyzing a list of card game concept instances.

# Instructions
1. **Input**: You will receive a list of card game concept instances under a given concept theme.
2. **Output**: Your response should include:
```json
{
    "variation_summary": "<How the instances vary from the given theme>",
    "category":[
        {
            "description": "<description of the first category of variation>",
            "instance_idx": [<indices of instances that belong to this category>]
        },
        {
            "description": "<description of the second category of variation>",
            "instance_idx": [<indices of instances that belong to this category>]
        }
        ...
    ]
}
```

# Theme
All instances are different approaches to realize this game concept theme:
{theme}

# Instances
{input_text}
"""

PROMPTS[
    "entity_design_in_between"
] = """
{prefix_prompt}. Now design a novel concept instance that:
(1) serves for the same theme: {theme}
(2) falls into the category: {category}
(3) is different from all given instances.

# Format
```json
{
    "name": "Name of the game concept (e.g., Dynamic Wild Card, Critical Threshold).",
    "description": "A short concise explanation in one sentence, following the writing style of the previous instances."
}
```
"""

PROMPTS[
    "entity_continue_design"
] = "Design another one"


PROMPTS[
    "entity_design"
] = """
{prefix_prompt}. Now design the novel concept instance based on your summary. 
- The concept should center around the summary you have concluded.
- The concept should be different from all given instances.
- Mimic the variation pattern you have observed in the previous instances.
- You should specify its name and description. 
- You should follow this format:
```json
{
    "name": "Name of the game concept, following the writing style of the previous instances.",
    "description": "A short concise explanation in one sentence, following the writing style of the previous instances."
}
```
"""
