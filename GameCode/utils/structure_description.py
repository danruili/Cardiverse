from Utils.LLMHandler import LLMHandler
from GameCode.utils.formatting import extract_from_language

STRUCTURE_TEMPLATE = """
Design a structured ruleset for implementing a card game system based on the provided input. Ensure the output includes key components as below. The output should be comprehensive, logical, and organized in a format suitable for programming or detailed documentation purposes. Wrap the output in a markdown block.

Include the following sections:
1. **Game State**
   - Define the game state, categorized into common information and player-specific information (grouped into public and private).
2. **Card**
    - Specify card attributes such as rank, suit, and any special abilities or values.
3. **Deck and Initial Dealing**
    - Describe the deck composition, dealing process, and setup at the beginning of the game.
4. **Legal Action Space**
    - List all possible actions players can perform during their turn, specifying the prerequisites of each action.    
5. **Round**
    - Describe the sequence of play and how the game progresses from one player to the next.
    - Elaborate in each players' turn, the order of actions they can take, and the outcomes of each action.
    - Explain how the game ends and the winning conditions. Pay attention to corner cases such as deck exhaustion or all players passing.
6. **Other Game Mechanics & Rules**
    - Detail any additional game mechanics, rules, or special actions that players can take during the game.
7. **Player Observation Information**
    - Specify what information players can observe during the game, such as their hand, the starter pile, declared suits, and opponent actions.
8. **Payoffs**
    - Explain when game ends, how scoring works, including point values for cards.

Ensure clarity and precision to facilitate implementation or usage as a reference for game rules.

# Example

```markdown
### 1. **Game State**

#### **Common Information:**
- **Discard Pile:** Top card visible to all players.
- **Stock Pile:** Number of cards in the stock (but not their identities).
- **Turn Information:** Current player and actions taken during the turn.
- **Player Order:** Turn sequence visible to all players.

#### **Player-Specific Information:**
- **Public**:
    - **Melds:** All matched sets and sequences laid down on the table.
    - **Score:** Current score, maintained privately for each player.
    - **Drawn Cards:** If drawn from the discard pile, visible during the draw.
- **Private**:
    - **Player Hand:** Cards held by the player, visible only to them.

---

### 2. **Card**

#### **Attributes:**
- **Rank:** One of {K, Q, J, 10, 9, 8, 7, 6, 5, 4, 3, 2, A}.
- **Suit:** One of {Hearts, Diamonds, Clubs, Spades}.
- **Special Values:**
  - Ace: Can act as high (11 points) or low (1 point) depending on the sequence.
  - Pip Value: Numeric rank is equivalent to its points; face cards (K, Q, J) are worth 10 points.

#### **Card States:**
- Face-down: Cards in the stock pile.
- Face-up: Cards in the discard pile or melds.

---

### 3. **Deck and Initial Dealing**

#### **Deck Composition:**
- A standard 52-card deck with 13 ranks across 4 suits.

#### **Initial Dealing:**
- **2 Players:** 10 cards each.
- **3-4 Players:** 7 cards each.
- **5-6 Players:** 6 cards each.
- Remaining cards form the stock pile.
- Top card of the stock pile is turned face-up to create the discard pile.

---

### 4. **Legal Action Space**

#### **On a Turn, a Player May:**
1. **Draw Cards:**
   - Draw two cards from the stock pile OR draw two cards from the top of the discard pile.
    - Pre-requisite: Player have not drawn cards this turn.
2. **Lay Down Melds:**
   - Place matched sets.
    - Pre-requisite: Player must have drawn a card this turn. And the cards are three or four of a kind.
   - OR lay down sequences
    - Pre-requisite: Player must have drawn a card this turn. And the cards are a valid sequence (three or more consecutive cards of the same suit, including corner cases like K-A-2).
3. **Laying Off:**
   - Add one or more cards to existing melds.
    - Pre-requisite: The card must be a valid addition to the meld.
4. **Discard One Card:**
   - Place a card from their hand onto the discard pile.
    - Pre-requisite: Player must have drawn a card this turn. And cannot discard the same card drawn from the discard pile in the same turn.

---

### 5. **Round**

#### **Sequence of Play:**
1. The player to the dealer’s left starts the round.
2. Players take turns sequentially in clockwise order.
3. Each turn consists of:
   - Drawing cards (stock or discard pile).
   - Optionally laying down melds or laying off cards.
   - Discarding a single card.
   - Passing the turn to the next player.
4. Play continues until:
   - A player goes out (uses all cards in their hand).
   - OR the stock pile is exhausted, and no player can go out.

#### **Winning Conditions:**
- A player wins by going out.
- In case of a tie (stock exhausted and no one goes out), scores are calculated based on unmatched cards.

---

### 6. **Other Game Mechanics & Rules**

- **Rummy Bonus:** A player who goes out without having previously laid down or laid off earns a Rummy bonus. Opponents pay double penalties.
- **Reforming the Stock:** If the stock is empty, the discard pile (except its top card) is flipped over to form a new stock pile.
- **Legal Melds:** Must consist of:
  - A set (e.g., 7-7-7 or K-K-K-K).
  - A sequence (e.g., 5-6-7 or Q-K-A).
- **Corner Cases for Aces:** Aces can form sequences like K-A-2 or A-2-3.

---

### 7. **Player Observation Information**

#### **Visible Information to Each Player:**
- Their own hand.
- The top card of the discard pile.
- Melds on the table (all players’ contributions).
- Total cards remaining in the stock pile.
- Actions performed by other players during their turn.

#### **Hidden Information:**
- The identity of cards in the stock pile.
- Cards in opponents’ hands.

---

#### 8. **Payoffs**

##### **Endgame Scoring:**
- A player’s score is the total pip value of unmatched cards in their hand:
  - Ace = 11 points.
  - Face cards = 10 points.
  - Numbered cards = Rank value.
- If a player goes Rummy, opponents pay double their calculated penalty.

##### **Winning Player’s Reward:**
- Other players’ scores are added to the winner’s score as a positive payoff.

##### **Tie Resolution:**
- If no player goes out, the winner is the player with the lowest unmatched card value in their hand.
```
"""


def structurize_description(game_description: str, 
           llm_handler: LLMHandler
           ) -> str:
    """Create a structured description for the game"""

    response = llm_handler.chat(
        STRUCTURE_TEMPLATE + "\n# Your input\n" + game_description)
    return extract_from_language(response, 'markdown')