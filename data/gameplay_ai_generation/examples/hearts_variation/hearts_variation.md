# Hearts of Time Game System Ruleset (Refined)

### 1. **Game State**

#### **Common Information:**
- **Trick History:** Sequence of played cards in each trick, visible to all players.
- **Current Leader:** Player who won the last trick, visible to all players.
- **Turn Information:** Current player and actions taken during the turn.
- **Player Order:** Logical order of play, visible to all players.

#### **Player-Specific Information:**
- **Public**:
  - **Scores:** Current interference (disturbance scores) known at all times.
  - **Trick Wins:** Number of tricks each player has won.
- **Private**:
  - **Player Hand:** Cards held by the player.
  - **Temporal Suit Shift Status:** Whether the player has used their shift ability.

---

### 2. **Card**

#### **Attributes:**
- **Rank:** From 2 to Ace.
- **Suit:** One of {Hearts, Diamonds, Clubs, Spades}.
- **Special Cards:**
  - **Queen of Spades:** 13 points of disturbance.
  - **Hearts:** Each incurs 1 point of disturbance.

---

### 3. **Deck and Initial Dealing**

#### **Deck Composition:**
- A standard 52-card deck divided into four suits.

#### **Initial Dealing:**
- **4 Players:** Each player receives 13 cards.
- Other player counts require deck adjustment by removing low-ranking cards, maintaining suit balance.

---

### 4. **Legal Action Space**

#### **On a Turn, a Player May:**
1. **Lead a Trick:**
   - Play any card from their hand.
   - Pre-requisite: Must follow suit, unless void in that suit.
2. **Follow a Trick:**
   - Play a card matching the led suit, if possible.
   - Else, play any card.
3. **Declare Temporal Suit Shift:**
   - Announce the shift of rule for a trick to establish a temporary trump suit. This can be declared before playing any card during a player's turn.
   - Pre-requisite: Can only be used once per game per player.

---

### 5. **Round**

#### **Sequence of Play:**
1. The player with the 2 of Clubs starts the first trick.
2. Players take turns in clockwise order, leading with the suit following rules.
3. Each trick consists of:
   - Playing cards in the order of player turns.
   - Using Temporal Suit Shift if strategically advantageous. When declared, the player's chosen suit acts as trump for that entire trick.
4. The winner of a trick leads the next trick.
5. Play continues until all cards have been played.

#### **Winning Conditions:**
- Game ends when a player reaches a preset disturbance threshold (commonly 100 points).
- Player with the lowest disturbance score wins.

---

### 6. **Other Game Mechanics & Rules**

- **No Hearts or Queen of Spades First Trick:** During the first trick, players must avoid playing hearts or the Queen of Spades unless they have no alternative.
- **Shooting the Moon:** Capturing all Hearts and Queen of Spades reduces disturbance to zero for that round, increasing opponents' scores by 26 points.
- **Temporal Strategy:** Deciding when to use Temporal Suit Shift is critical to altering trick outcomes. The temporary trump suit impacts only one trick and reverts after its resolution.

---

### 7. **Player Observation Information**

#### **Visible Information to Each Player:**
- Cards in their own hand.
- Cards played in tricks.
- Scores of each player.
- Temporal Suit Shift use and declared trump suit.

#### **Hidden Information:**
- Cards in opponents’ hands.

---

### 8. **Payoffs**

##### **Endgame Scoring:**
- A point of disturbance equals 1 for each Heart.
- Queen of Spades is worth 13 disturbance points.
- Shooting the Moon results in zero points for the round, with opponents' scores increased.

##### **Winning Player’s Reward:**
- Having the lowest disturbance score leads to victory when the game concludes.

With these refinements, the "Hearts of Time" game provides clarity on the use and impact of Temporal Suit Shift, maintaining the intrigue and strategy native to Hearts, while clearly outlining the new rules. Enjoy your journey through the mystical realm as you guide your temporal path among the "Hearts of Time."