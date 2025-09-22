## Refined Ruleset for Card Game: "Fusion Rummy"

### 1. **Game State**

#### **Common Information:**
- **Communal Pool:** Cards that are laid down and visible to all players, used for fusion.
- **Pot:** Number of counters in the pot visible to all players.
- **Current Player:** The active player's turn status, with previous actions taken.
- **Sequence Information:** Current suit being played and its sequence.

#### **Player-Specific Information:**
- **Public**:
  - **Fusion Cards:** Displayed unique fusion cards for each player.
  - **Chips in Front:** If additional chips are anteed due to unequal cards.
- **Private**:
  - **Player Hand:** Cards held by the player, visible only to them.
  - **Special Abilities:** Any special effects granted by fusion cards.

---

### 2. **Card**

#### **Attributes:**
- **Rank:** K, Q, J, 10, 9, 8, 7, 6, 5, 4, 3, 2, A (with King being high).
- **Suit:** Hearts, Diamonds, Clubs, Spades.

#### **Special Values:**
- **Fusion Cards:** Derived from sequences of three consecutive ranks that offer strategic advantages.

---

### 3. **Deck and Initial Dealing**

#### **Deck Composition:**
- A standard 52-card deck, comprising 13 ranks across 4 suits.

#### **Initial Dealing:**
- Cards are dealt one at a time starting from the player to the left of the dealer until all cards are allocated. 
- Some players may have more cards than others. Players with fewer cards must ante an additional chip to the pot.

---

### 4. **Legal Action Space**

#### **On a Turn, a Player May:**
1. **Play a Card:**
   - Play the next higher card in the current suit in sequence.
   - Pre-requisite: Card must follow the current suit and sequence.
2. **Place a Counter:**
   - Place one counter into the pot if unable or unwilling to play.
3. **Create a Fusion Card:**
   - Form a sequence of three consecutive cards solely from their hand.
   - Added Clarification: Cards used for fusion are removed from the player's hand and displayed publicly, contributing to the player's fusion count.
4. **Use Fusion Special Ability:**
   - Activate special abilities provided by previously formed fusion cards during the player's turn.

---

### 5. **Round**

#### **Sequence of Play:**
1. The player to the dealer's left starts the play by playing a card of choice.
2. Each subsequent player must follow the sequence:
   - Play a higher rank of the same suit, OR
   - Place a counter in the pot if unable or unwilling to play the required card.
3. Players may form fusion cards from valid sequences purely in their hands.
4. Continuation until the suit is exhausted, or a player fulfills the fusion card requirement.
5. Player completing a sequence can start a new suit sequence.
6. A player wins the game by creating the designated number of fusion cards.
7. Rounds end when a player creates the required number of fusion cards or all card sequences are exhausted.

#### **Winning Conditions:**
- The first player to create three unique fusion cards wins the game, immediately ending the current round and ignoring leftover cards.

---

### 6. **Other Game Mechanics & Rules**

- **Reform Initiative:** Upon exhausting a suit sequence, the player may start a new suit.
- **Fusion Abilities:** Include actions like skip-turn effects, card protection, or counter retrieval from the pot, used during the player's turn.
- **Card Exhaustion:** If all sequences are exhausted, the round ends normally.

---

### 7. **Player Observation Information**

#### **Visible Information to Each Player:**
- Their own hand.
- Communal pool of cards.
- Current pot chips.
- Publicly displayed fusion cards and their effects.
- Actions taken by every player during their turn.

#### **Hidden Information:**
- Unrevealed card sequences or strategies of other players.

---

### 8. **Payoffs**

#### **End of Round Scoring:**
- Scoring for rounds via card remnants is nullified if the game ends via fusion victory.
- In games without an immediate fusion victory, traditional scoring proceeds; 1 point for each card left.

#### **Fusion Bonuses:**
- Formation of unique and strategic fusion cards that empower players with special actions and directly influence game outcomes. 

This refined version maintains consistency in the rules and resolves previous ambiguities, enhancing the clarity and strategic depth of "Fusion Rummy."