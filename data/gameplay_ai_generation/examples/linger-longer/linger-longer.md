### 1. Card Design

* The game uses **1 standard 52-card deck** (no jokers).
* Cards have ranks and suits:

  * **Rank order (low → high):** 2,3,4,5,6,7,8,9,10,J,Q,K,A (Ace is high).
* A **trump suit** is chosen at the start of the game by revealing one card from the deck; its **suit** becomes trump. That card is returned to the deck.
* There are **no numeric hand totals** and **no modulo arithmetic** in this game.

---

### 2. Dealing

* **Players:** Recommended **4**, supported range **2–5**.
* Each player is dealt a number of cards equal to the number of players.

  * Example: In a 4-player game, each receives 4 cards.
* After dealing, one extra card is revealed to determine the **trump suit**, then returned to the deck.
* Turn order begins with the first player and proceeds clockwise.

---

### 3. Game Round

* **Turns:** On your turn, you play one card from your hand face up.

* **Tricks:**

  * A trick consists of one card played by each player.
  * Once all players have contributed a card, the trick is resolved.

* **Resolving a trick:**

  * The winner is determined as follows:

    * If a **trump card** is played and no earlier trump has won, the trump card wins.
    * If multiple trumps are played, the **highest-ranked trump** wins.
    * If no trumps are played, the **highest-ranked card of the leading suit** (the suit of the first card played that trick) wins.

* **After a trick:**

  * The trick winner adds **+1 trick** to their score.
  * The winner then draws one card from the deck (if any remain).
  * The winner also leads the next trick.

* **Ending conditions:**

  * If only **one player has cards remaining**, that player immediately wins.
  * If the deck is empty and all hands are exhausted, the player with the **most tricks won** is the winner.
  * If two or more players tie for most tricks, the game ends in a **draw**.

---

### 4. Winning

* **Victory is binary:**

  * The winner receives full credit for the game.
  * All other players score nothing.
* A **draw** occurs if multiple players tie for most tricks when the deck is depleted.
* There are **no wagers, chips, or payouts** in this game.

