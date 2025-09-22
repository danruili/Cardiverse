import random
from GameEngine.utils.base_agents import BaseAgent

from itertools import groupby, combinations
from typing import List, Dict, Tuple



def _get_rank_order(rank: str) -> int:
    """Returns the numerical order of a card rank for sorting runs."""
    if rank.isdigit():
        return int(rank)
    # Using 'T' for 10 internally is a common convention
    return {'A': 1, 'T': 10, 'J': 11, 'Q': 12, 'K': 13}.get(rank, 0)

def _get_card_value_from_dict(card: Dict) -> int:
    """Returns the deadwood point value of a card dictionary."""
    rank = card['rank']
    if rank.isdigit():
        return int(rank)
    return 10 if rank in ['T', 'J', 'Q', 'K'] else 1

def _card_to_str(card: Dict) -> str:
    """Creates a canonical string representation for a card dictionary."""
    return f"{card['rank']}-{card['suit']}"

def _find_card_in_hand(hand: List[dict], card_str: str):
    """Finds a card dictionary in a list by its string representation."""
    for card in hand:
        if _card_to_str(card) == card_str:
            return card
    return None

def _find_best_melds(hand: List[Dict]) -> Tuple[List[List[Dict]], int]:
    """
    Finds the optimal combination of melds in a hand to minimize deadwood value.

    This version uses plain dictionaries to represent cards, e.g.,
    {'rank': 'K', 'suit': 'Spades'}.

    Args:
        hand (List[Dict]): A list of dictionaries, where each dictionary is a card.

    Returns:
        Tuple[List[List[Dict]], int]: A tuple containing:
            - The list of melds in the best combination.
            - The resulting minimum deadwood value.
    """
    if not hand:
        return [], 0

    # --- 1. Find all possible melds (sets and runs) in the hand ---
    sets, runs = [], []
    # Sort hand to make finding runs easier
    hand.sort(key=lambda c: (c['suit'], _get_rank_order(c['rank'])))

    # Find all possible sets (3 or 4 of a kind)
    for _, group in groupby(hand, key=lambda c: c['rank']):
        cards = list(group)
        if len(cards) >= 3:
            for combo in combinations(cards, 3):
                sets.append(list(combo))
            if len(cards) == 4:
                sets.append(cards)

    # Find all possible runs (3+ consecutive cards of the same suit)
    for _, group in groupby(hand, key=lambda c: c['suit']):
        cards_by_suit = list(group) # Already sorted by rank from the initial sort
        if len(cards_by_suit) >= 3:
            for i in range(len(cards_by_suit) - 2):
                for j in range(i + 2, len(cards_by_suit)):
                    sub_hand = cards_by_suit[i:j + 1]
                    # Check for consecutive ranks
                    is_a_run = all(
                        _get_rank_order(sub_hand[k]['rank']) == _get_rank_order(sub_hand[k - 1]['rank']) + 1
                        for k in range(1, len(sub_hand))
                    )
                    if is_a_run:
                        runs.append(sub_hand)

    all_melds = sets + runs
    if not all_melds:
        return [], sum(_get_card_value_from_dict(c) for c in hand)

    # --- 2. Solve the exact cover problem using recursion and memoization ---
    # To use memoization, we need hashable keys. Dictionaries are not hashable,
    # so we create a canonical string for each card and use a tuple of these
    # strings as the key.
    memo = {}
    card_lookup = {_card_to_str(c): c for c in hand}

    def find_best_recursive(card_str_tuple: Tuple[str, ...]) -> Tuple[List[List[Dict]], int]:
        """ Recursively finds the best melds for a tuple of card strings. """
        if not card_str_tuple:
            return [], 0
        if card_str_tuple in memo:
            return memo[card_str_tuple]

        # Start with the assumption of no melds, deadwood is the whole hand
        current_hand = [card_lookup[s] for s in card_str_tuple]
        min_deadwood = sum(_get_card_value_from_dict(c) for c in current_hand)
        best_melds = []

        # Iterate through all possible melds
        current_hand_str_set = set(card_str_tuple)
        for meld in all_melds:
            meld_str_set = {_card_to_str(c) for c in meld}

            # If the meld can be formed from the current hand
            if meld_str_set.issubset(current_hand_str_set):
                # Recurse on the remaining cards
                remaining_strs = tuple(sorted(list(current_hand_str_set - meld_str_set)))
                
                recursive_melds, recursive_deadwood = find_best_recursive(remaining_strs)

                # If this path produced a better result, save it
                if recursive_deadwood < min_deadwood:
                    min_deadwood = recursive_deadwood
                    best_melds = [meld] + recursive_melds
        
        memo[card_str_tuple] = (best_melds, min_deadwood)
        return best_melds, min_deadwood

    # Initial call with the full hand, converted to a sorted tuple of strings
    initial_str_tuple = tuple(sorted([_card_to_str(c) for c in hand]))
    return find_best_recursive(initial_str_tuple)


class GinRummyRuleAgent(BaseAgent):
    ''' Gin Rummy Novice Rule agent adapted for the new game engine.
    
    This agent's strategy is as follows:
    1. If it can go 'gin', it will choose a random 'gin' action.
    2. If it cannot 'gin' but can 'knock', it will choose a random 'knock' action.
    3. If its only option is to discard, it will calculate the best card to discard.
       The "best" discard is the one that leaves the remaining hand with the
       lowest possible deadwood value. If multiple discards yield the same
       best outcome, it chooses one randomly.
    4. For any other situation (e.g., drawing a card), it will choose a random
       legal action.
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_raw = True

    def step(self, state: dict) -> tuple[dict, dict]:
        ''' Predict the action given the structured state from the new game engine.
        
        Args:
            state (dict): Structured state from the game.

        Returns:
            (dict, dict): A tuple containing the chosen action dictionary
                          and an info dictionary for analysis.
        '''
        legal_actions = state['legal_actions']
        
        # --- Strategy 1: Prioritize Gin ---
        gin_actions = [a for a in legal_actions if a['action'] == 'gin']
        if gin_actions:
            chosen_action = random.choice(gin_actions)
            return chosen_action, {'agent_strategy': 'gin'}

        # --- Strategy 2: Prioritize Knock ---
        knock_actions = [a for a in legal_actions if a['action'] == 'knock']
        if knock_actions:
            chosen_action = random.choice(knock_actions)
            return chosen_action, {'agent_strategy': 'knock'}

        # --- Strategy 3: Best Discard ---
        discard_actions = [a for a in legal_actions if a['action'] == 'discard']
        if discard_actions:
            # import ipdb; ipdb.set_trace()  # Debugging breakpoint

            current_player_id = state['common']['current_player']
            hand = state['players'][current_player_id]['facedown_cards']['hand']
            chosen_action = self._get_best_discard_action(discard_actions, hand)
            return chosen_action, {'agent_strategy': 'best_discard'}
        
        # --- Strategy 4: Fallback (for Draw, Pickup, etc.) ---
        chosen_action = random.choice(legal_actions)
        return chosen_action, {'agent_strategy': 'random_fallback'}

    def eval_step(self, state: dict) -> tuple[dict, dict]:
        """ For rule-based agents, eval_step is the same as step. """
        return self.step(state)

    def _get_best_discard_action(self, discard_actions: list[dict], hand: list[object]) -> dict:
        """
        Determines the best discard action by finding which discard leaves the
        hand with the minimum possible deadwood.
        """
        best_discard_options = []
        min_resulting_deadwood = float('inf')

        for action in discard_actions:
            card_to_discard = _find_card_in_hand(hand, action['args']['card'])
            
            if card_to_discard is None: continue

            # Create the hand that would remain after discarding
            remaining_hand = [c for c in hand if c != card_to_discard]
            
            # Calculate the minimum deadwood for the remaining hand
            _, deadwood_count = _find_best_melds(remaining_hand)

            if deadwood_count < min_resulting_deadwood:
                min_resulting_deadwood = deadwood_count
                best_discard_options = [action]
            elif deadwood_count == min_resulting_deadwood:
                best_discard_options.append(action)
        
        # If there are multiple "best" discards, choose one randomly
        return random.choice(best_discard_options) if best_discard_options else random.choice(discard_actions)
