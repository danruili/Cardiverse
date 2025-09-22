import re

EMPTY_ANALYSIS = {
    'text_blocks': [],
    'code_blocks': [],
    'markdown_blocks': []
}

def extract_analysis_blocks(text) -> dict:
    """
    Extracts code, markdown, and text blocks from a given text.
    Returns: A dictionary containing the extracted blocks.
        {
            'text_blocks': List[str],
            'code_blocks': List[str],
            'markdown_blocks': List[str]
        }
    """
    # Regular expressions for different block types
    code_pattern = r'```python(.*?)```'
    text_pattern = r'Summary:\n```text(.*?)```|Summary:\n```(.*?)```'
    markdown_pattern = r'Quote \(optional\):\n```markdown(.*?)```|Quote \(optional\):\n```(.*?)```|Quote:\n```markdown(.*?)```|Quote:\n```(.*?)```'
    
    # Extract code blocks (with or without language identifiers)
    code_blocks = re.findall(code_pattern, text, re.DOTALL)
    markdown_blocks = re.findall(markdown_pattern, text, re.DOTALL)
    text_blocks = re.findall(text_pattern, text, re.DOTALL)

    # only keep the first match for markdown and text blocks
    for i in range(len(markdown_blocks)):
        for j in range(len(markdown_blocks[i])):
            if markdown_blocks[i][j]:
                markdown_blocks[i] = markdown_blocks[i][j]
                break
    for i in range(len(text_blocks)):
        for j in range(len(text_blocks[i])):
            if text_blocks[i][j]:
                text_blocks[i] = text_blocks[i][j]
                break
    
    # Remove potential "text" and "markdown" labels from blocks
    cleaned_code_blocks = code_blocks
    cleaned_markdown_blocks = [block.strip() for block in markdown_blocks]
    cleaned_text_blocks = [block.strip() for block in text_blocks]
    
    result = {
        'text_blocks': cleaned_text_blocks,
        'code_blocks': cleaned_code_blocks,
        'markdown_blocks': cleaned_markdown_blocks
    }
    
    return result



# unit test below

sample_text = """
The fundamental issue lies in the fact that player 1 incorrectly played an eight without declaring a suit, and the get_legal_actions did not account for this need.
   
***Analysis Summary***
Summary:
```text
Player 1's action 'play-2-0' when playing an eight did not allow for suit declaration, which is required by the rules.
```
Quote (optional):
```markdown
- **Special Abilities**: Eights: Wild cards that can be played at any time, allowing the player to declare the suit to be followed.
```
Edit:
```python
<<<<<<< SEARCH
        if (card['suit'] == starter_card['suit'] or 
            card['rank'] == starter_card['rank'] or 
            card['rank'] == '8'):
            if card['rank'] == '8':
                for suit in ['clubs', 'diamonds', 'hearts', 'spades']:
                    legal_actions.append(f'play-{idx}-{suit}')
            else:
                legal_actions.append(f'play-{idx}-0')
=======
        if (card['suit'] == starter_card['suit'] or 
            card['rank'] == starter_card['rank']):
            legal_actions.append(f'play-{idx}-0')
        elif card['rank'] == '8':
            for suit in ['clubs', 'diamonds', 'hearts', 'spades']:
                legal_actions.append(f'play-{idx}-{suit}')
>>>>>>> REPLACE
```
"""

sample_text_2 = """
The gameplay log aligns with the rules described, as all actions taken conform to expected legal plays and transitions between states.

***Analysis Summary***
```pass```
"""

sample_text_3 = """
***Analysis Summary***
Summary:
```text
Player 2 was able to play an "8" card and specify a suit ('clubs'), but did so without explicitly declaring it in the log. The assumption of clubs must explicitly appear in the player action; the previous code considers multiple suits valid.
```
Quote:
```markdown
- **Eights**: Wild cards, which can be played at any time, allowing the player to declare the suit to be followed.
```
Edit:
```python
<<<<<<< SEARCH
        elif card['suit'] == starter_card['suit'] or card['rank'] == starter_card['rank']:
            legal_actions.append(f'play-{idx}')
=======
        elif (card['suit'] == starter_card['suit'] or card['rank'] == starter_card['rank']) \
            and wildcard_suit is None:
            legal_actions.append(f'play-{idx}')
>>>>>>> REPLACE
```
```python
<<<<<<< SEARCH
def player_has_valid_play(player: int, hand: List[LLMCard], starter: LLMCard, wildcard_suit: str = None) -> bool:
=======
def player_has_valid_play(player: int, hand: List[LLMCard], starter: LLMCard, wildcard_suit: str) -> bool:
>>>>>>> REPLACE
```
```python
<<<<<<< SEARCH
    effective_suit = wildcard_suit if wildcard_suit else starter['suit']
=======
    effective_suit = wildcard_suit if wildcard_suit else starter['suit']  
>>>>>>> REPLACE
```
"""

if __name__ == "__main__":
    extracted_blocks = extract_analysis_blocks(sample_text)
    print(extracted_blocks)
    print()
    extracted_blocks_2 = extract_analysis_blocks(sample_text_2)
    print(extracted_blocks_2)
    extracted_blocks_3 = extract_analysis_blocks(sample_text_3)
    print(extracted_blocks_3)