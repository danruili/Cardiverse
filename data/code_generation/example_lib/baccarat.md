### 1. Card Design

* Uses **8 standard decks** (no jokers), all shuffled together at start.
* Card values:
  * **A, 2–9** = face value (Ace = 1)
  * **10, J, Q, K** = 0
* Hand total = **(sum of card values) mod 10** (e.g., 14 → 4).

---

### 2. Dealing

* **Players:** recommended **7**; supported **7–9**.
* **Betting first:** In seat order, each player makes **one bet** on exactly one outcome: **Player**, **Banker**, or **Tie**.
  * Allowed stakes: **10, 20, or 30 chips** (multiples of 10 only).
* After **all** players have bet:
  * Deal **two face-up cards** to **Player** hand and **two face-up cards** to **Banker** hand (alternating, starting with Player).
  * There is **no shoe/cut card** and **no burn sequence**.

---

### 3. Game Round

* **Naturals:** If either hand totals **8 or 9** on the first two cards, the coup **ends immediately** (no third cards).
* **If no natural, third-card draws:**

**Player’s draw rule (exactly as coded)**

* Player **draws a third card** if initial total **0–5**.
* Player **stands** on **6–7**.

**Banker’s draw rule (exactly as coded)**

* First recompute Banker total after the Player’s action.

* If **Player stood** (i.e., Player has only two cards):

  * **Banker draws** on totals **0–5**; **stands** on **6–7**.

* If **Player drew a third card**:

  * Banker **only** draws in these cases:

    * Banker total **3** → draw **unless** Player’s 3rd card = **8**
    * Banker total **4** → draw if Player’s 3rd card ∈ **{2,3,4,5,6,7}**
    * Banker total **5** → draw if Player’s 3rd card ∈ **{4,5,6,7}**
  * Otherwise (including Banker totals **0–2** or **6–7**) → **Banker stands**.
  * ⟶ **Note:** This is a simplified tableau: **Banker does *not* draw on 0–2** after a Player draw, and **never draws on 6** even if Player’s 3rd card is 6 or 7.

* **Resolution:** Compare final totals (0–9). Higher total wins; equal totals = **Tie**.

* The game is a **single coup** per round and **auto-resolves** once bets are placed (no player actions after betting).

---

### 4. Winning

* **Payouts:**
  * **Player** bet: **1:1**
  * **Banker** bet: **0.95:1** (5% commission reflected as 0.95 multiplier)
  * **Tie** bet: **8:1**
* **Tie handling:**
  * If the outcome is **Tie** and a player bet **Player** or **Banker**, that bet is a **push** (no win, no loss).
