
"""Beginning of the code template"""
game_name = 'Gin Rummy' # TODO: specify the game name
recommended_num_players: int = 2  # TODO: specify the recommended number of players
num_players_range: List[int] = [2] # TODO: specify the range of number of players

# Helper functions for Gin Rummy logic

def _get_rank_order(rank: str) -> int:
    """Returns the numerical order of a card rank."""
    if rank.isdigit():
        return int(rank)
    return {'A': 1, 'T': 10, 'J': 11, 'Q': 12, 'K': 13}[rank[0]]

def _get_card_value(card: LLMCard) -> int:
    """Returns the deadwood point value of a card."""
    if card.rank.isdigit():
        return int(card.rank)
    return 10 if card.rank in ['T', 'J', 'Q', 'K'] else 1

def _find_card_in_hand(hand: List[LLMCard], card_str: str) -> Optional[LLMCard]:
    """Finds a card object in a hand by its string representation."""
    for card in hand:
        if card.get_str() == card_str:
            return card
    return None

def _calculate_deadwood(hand: List[LLMCard], melds: List[List[LLMCard]]) -> int:
    """Calculates the total deadwood value of a hand given the melds."""
    melded_cards = {card.get_str() for meld in melds for card in meld}
    deadwood_cards = [card for card in hand if card.get_str() not in melded_cards]
    return sum(_get_card_value(card) for card in deadwood_cards)

def _find_best_melds(hand: List[LLMCard]) -> Tuple[List[List[LLMCard]], int]:
    """
    Finds the combination of melds that results in the minimum deadwood.
    Returns the best meld combination and the minimum deadwood value.
    """
    if not hand:
        return [], 0

    # 1. Find all possible melds (sets and runs)
    sets, runs = [], []
    hand.sort(key=lambda c: (c.suit, _get_rank_order(c.rank)))
    
    # Find sets
    from itertools import groupby, combinations
    for _, group in groupby(hand, key=lambda c: c.rank):
        cards = list(group)
        if len(cards) >= 3:
            for combo in combinations(cards, 3):
                sets.append(list(combo))
            if len(cards) == 4:
                sets.append(cards)

    # Find runs
    for _, group in groupby(hand, key=lambda c: c.suit):
        cards_by_suit = sorted(list(group), key=lambda c: _get_rank_order(c.rank))
        if len(cards_by_suit) >= 3:
            for i in range(len(cards_by_suit) - 2):
                for j in range(i + 2, len(cards_by_suit)):
                    sub_hand = cards_by_suit[i:j+1]
                    is_a_run = all(_get_rank_order(sub_hand[k].rank) == _get_rank_order(sub_hand[k-1].rank) + 1 for k in range(1, len(sub_hand)))
                    if is_a_run:
                        runs.append(sub_hand)

    all_melds = sets + runs
    if not all_melds:
        return [], sum(_get_card_value(c) for c in hand)

    # 2. Use recursion to find the best non-overlapping combination
    memo = {}
    def find_best_recursive(card_indices_tuple):
        if not card_indices_tuple:
            return [], 0
        if card_indices_tuple in memo:
            return memo[card_indices_tuple]

        current_hand = [hand[i] for i in card_indices_tuple]
        min_deadwood = sum(_get_card_value(c) for c in current_hand)
        best_melds = []

        # Option 1: Don't use any meld from this sub-problem
        # This is the initial state for min_deadwood and best_melds

        # Option 2: Try using each possible meld in the current hand
        for meld in all_melds:
            meld_indices = [hand.index(c) for c in meld]
            if all(idx in card_indices_tuple for idx in meld_indices):
                remaining_indices = tuple(sorted(list(set(card_indices_tuple) - set(meld_indices))))
                
                # Recursive call
                recursive_melds, recursive_deadwood = find_best_recursive(remaining_indices)
                
                if recursive_deadwood < min_deadwood:
                    min_deadwood = recursive_deadwood
                    best_melds = [meld] + recursive_melds
        
        memo[card_indices_tuple] = (best_melds, min_deadwood)
        return best_melds, min_deadwood

    initial_indices = tuple(range(len(hand)))
    return find_best_recursive(initial_indices)


def initiation(num_players, logger) -> DotDict:
    """
    Initialize the game state. The game state contains all information of the game.
    """
    # TODO: initialize the game state
    game_state = DotDict({
        'common':  # mandatory field, store non-player-related information
        {
            'num_players': num_players,
            'current_player': 0,  # mandatory field
            'dealer_id': 0,
            'phase': 'deal', #Phases: deal, discard, draw, game_over
            'end_type': None, # Types: knock, gin, dead_hand
            'going_out_player': None,
            'knock_card': None,
            'winner': None,  # mandatory field
            'is_over': False,  # mandatory field
            'facedown_cards':  # facedown cards such as deck go here
            {
                'deck': [], 
            },
            'faceup_cards':  # faceup cards such as played cards go here
            {
                'discard_pile': [],
                'final_melds': {
                    'player_0': [],
                    'player_1': []
                }
            },
        },
        'players': [  # mandatory field
            DotDict({
                'public': {'score': 0}, # mandatory field, card-related fields shall not be included here
                'private': {},  # private information of the player
                'facedown_cards': { 
                    'hand': [],
                },
                'faceup_cards': {  
                    'melds': [] # Melds are revealed at the end
                },
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return DotDict(game_state)


def init_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    # TODO: initialize the deck
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']
    suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    deck = [LLMCard(field={'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state.common.facedown_cards.deck = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    # TODO: deal cards to players
    assert game_state.common.num_players == 2, "Gin Rummy is a 2-player game."
    deck = game_state.common.facedown_cards.deck
    
    dealer_id = 1  # the dealer is always player 1 (index 1)
    non_dealer_id = 1 - dealer_id
    game_state.common.dealer_id = dealer_id
    game_state.common.current_player = non_dealer_id

    # Non-dealer gets 11 cards, dealer gets 10. Non-dealer starts by discarding.
    game_state.players[non_dealer_id].facedown_cards.hand = [deck.pop() for _ in range(11)]
    game_state.players[dealer_id].facedown_cards.hand = [deck.pop() for _ in range(10)]
    
    # The first action of the game is for the non-dealer to discard.
    game_state.common.phase = 'discard'

    logger.info(f"Player {dealer_id} is the dealer.")
    logger.info(f"Player {non_dealer_id} receives 11 cards and starts the game.")
    logger.info(f"Player {dealer_id} receives 10 cards.")
    
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Process the action, update the state.
    """
    current_player_id = game_state.common.current_player
    player_hand = game_state.players[current_player_id].facedown_cards.hand
    deck = game_state.common.facedown_cards.deck
    discard_pile = game_state.common.faceup_cards.discard_pile
    action_type = action['action']

    # print(f"Deck size: {len(deck)}")

    if action_type == 'draw':
        drawn_card = deck.pop()
        player_hand.append(drawn_card)
        game_state.common.phase = 'discard'
        logger.info(f"Player {current_player_id} draws a card from the deck.")
    
    elif action_type == 'pickup':
        picked_card = discard_pile.pop()
        player_hand.append(picked_card)
        game_state.common.phase = 'discard'
        logger.info(f"Player {current_player_id} picks up {picked_card.get_str()} from the discard pile.")

    elif action_type == 'discard':
        card_to_discard = _find_card_in_hand(player_hand, action['args']['card'])
        player_hand.remove(card_to_discard)
        discard_pile.append(card_to_discard)
        game_state.common.current_player = 1 - current_player_id
        game_state.common.phase = 'draw'
        logger.info(f"Player {current_player_id} discards {card_to_discard.get_str()}.")

    elif action_type in ['knock', 'gin']:
        game_state.common.is_over = True
        game_state.common.phase = 'game_over'
        game_state.common.going_out_player = current_player_id
        game_state.common.end_type = action_type
        
        card_str = action['args']['card']
        card_to_remove = _find_card_in_hand(player_hand, card_str)
        player_hand.remove(card_to_remove) # The final 10-card hand for melds
        if action_type == 'knock':
            game_state.common.knock_card = card_to_remove
            logger.info(f"Player {current_player_id} knocks with {card_str}.")
        else:
             logger.info(f"Player {current_player_id} goes Gin!")

    elif action_type == 'declare_dead_hand':
        game_state.common.is_over = True
        game_state.common.phase = 'game_over'
        game_state.common.end_type = 'dead_hand'
        logger.info("The hand is declared dead. The game is a draw.")

    # Check for dead hand condition after a player discards
    if action_type == 'discard' and len(deck) <= 2:
        game_state.common.is_over = True
        game_state.common.phase = 'game_over'
        game_state.common.end_type = 'dead_hand'
        logger.info("Only two cards left in the stock. The hand is dead.")

    return game_state


def get_legal_actions(game_state: Dict) -> list[dict]:
    """
    Get all legal actions given the current state.
    """
    legal_actions = []
    current_player_id = game_state.common.current_player
    player = game_state.players[current_player_id]
    phase = game_state.common.phase

    if phase == 'draw':
        if len(game_state.common.facedown_cards.deck) > 2:
            legal_actions.append({'action': 'draw'})
        else: # If stock pile is too low, the game ends
            legal_actions.append({'action': 'declare_dead_hand'})
        
        if game_state.common.faceup_cards.discard_pile:
            legal_actions.append({'action': 'pickup'})
    
    elif phase == 'discard':
        hand = player.facedown_cards.hand
        assert len(hand) == 11, "Player should have 11 cards to discard."
        
        can_gin = False
        knock_actions = []

        for card_to_discard in hand:
            remaining_hand = [c for c in hand if c != card_to_discard]
            _, deadwood_count = _find_best_melds(remaining_hand)
            
            if deadwood_count == 0:
                can_gin = True
                legal_actions.append({'action': 'gin', 'args': {'card': card_to_discard.get_str()}})
                # Once a gin action is possible, it's the only one needed besides discard.
                # However, the player might choose to continue.
            elif deadwood_count <= 10:
                knock_actions.append({'action': 'knock', 'args': {'card': card_to_discard.get_str()}})

            legal_actions.append({'action': 'discard', 'args': {'card': card_to_discard.get_str(), 'deadwood': deadwood_count}})
        
        # To avoid redundancy, let's refine this. A player can always discard.
        # If they can knock with a discard, that's an additional option.
        # If they can gin, that is also an option.
        # Let's remove simple discards if knock/gin is available for that card.
        
        final_actions = []
        discards = {}
        for act in legal_actions:
            if act['action'] == 'discard':
                 discards[act['args']['card']] = act
            else:
                final_actions.append(act)
                # If we can knock/gin with a card, don't also add it as a simple discard
                if act['args']['card'] in discards:
                    del discards[act['args']['card']]
        
        legal_actions = final_actions + list(discards.values())

    else:
        legal_actions.append({'action': 'wait_for_announcement'})

    assert legal_actions, "get_legal_actions should not return an empty list."
    return legal_actions


def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """ Return the payoffs for each player."""
    end_type = game_state.common.end_type
    payoffs = [0, 0]

    if end_type == 'dead_hand':
        logger.info("Game ends in a draw. No points awarded.")

        # calculate deadwood for both players
        p0_hand = game_state.players[0].facedown_cards.hand
        p1_hand = game_state.players[1].facedown_cards.hand
        p0_opt_melds, p0_deadwood = _find_best_melds(p0_hand)
        p1_opt_melds, p1_deadwood = _find_best_melds(p1_hand)
        logger.info(f"Player 0's deadwood: {p0_deadwood}. Player 1's deadwood: {p1_deadwood}.")
        payoffs[0] = -p0_deadwood
        payoffs[1] = -p1_deadwood
        return payoffs

    p_out_id = game_state.common.going_out_player
    opp_id = 1 - p_out_id
    p_out_hand = game_state.players[p_out_id].facedown_cards.hand
    opp_hand = game_state.players[opp_id].facedown_cards.hand

    p_out_melds, p_out_deadwood = _find_best_melds(p_out_hand)
    opp_melds, opp_deadwood = _find_best_melds(opp_hand)

    # # Store final melds for observation
    # game_state.common.faceup_cards.final_melds[f'player_{p_out_id}'] = cards2list(p_out_melds)
    # game_state.common.faceup_cards.final_melds[f'player_{opp_id}'] = cards2list(opp_melds)

    if end_type == 'gin':
        score = 25 + opp_deadwood
        payoffs[p_out_id] = score
        payoffs[opp_id] = -score
        logger.info(f"Player {p_out_id} wins with Gin, scoring 25 + {opp_deadwood} = {score} points.")
        game_state.common.winner = p_out_id
        return payoffs

    if end_type == 'knock':
        opp_unmelded = [c for c in opp_hand if c not in [m for meld in opp_melds for m in meld]]
        
        # Lay-off logic
        layoff_melds = deepcopy(p_out_melds)
        layoff_cards = []
        for card in opp_unmelded[:]:
            for meld in layoff_melds:
                temp_meld = meld + [card]
                temp_meld.sort(key=lambda c: _get_rank_order(c.rank))
                # Check if it's a valid set or run after adding
                is_set = len(set(c.rank for c in temp_meld)) == 1
                is_run = len(set(c.suit for c in temp_meld)) == 1 and all(_get_rank_order(temp_meld[i].rank) == _get_rank_order(temp_meld[i-1].rank) + 1 for i in range(1, len(temp_meld)))
                
                if is_set or is_run:
                    opp_unmelded.remove(card)
                    meld.append(card) # Card is now part of the meld for further layoffs
                    layoff_cards.append(card)
                    break
        
        # if layoff_cards:
        #     logger.info(f"Player {opp_id} lays off {cards2list(layoff_cards)}.")
        
        opp_final_deadwood = sum(_get_card_value(c) for c in opp_unmelded)
        logger.info(f"Player {p_out_id}'s deadwood: {p_out_deadwood}. Player {opp_id}'s final deadwood: {opp_final_deadwood}.")

        if p_out_deadwood < opp_final_deadwood: # Knocker wins
            score = opp_final_deadwood - p_out_deadwood
            payoffs[p_out_id] = score
            payoffs[opp_id] = -score
            game_state.common.winner = p_out_id
            logger.info(f"Player {p_out_id} (knocker) wins, scoring {score} points.")
        else: # Opponent undercuts
            score = 25 + (p_out_deadwood - opp_final_deadwood)
            payoffs[opp_id] = score
            payoffs[p_out_id] = -score
            game_state.common.winner = opp_id
            logger.info(f"Player {opp_id} undercuts the knocker, scoring 25 + {p_out_deadwood - opp_final_deadwood} = {score} points.")

    return payoffs

"""End of the code template"""
