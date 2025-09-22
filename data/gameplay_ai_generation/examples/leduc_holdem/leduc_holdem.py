"""Beginning of the game code"""
# --- Game Configuration ---
game_name = "Leduc Hold'em"
recommended_num_players: int = 2
num_players_range: List[int] = [2]

# --- Helper Functions & Constants ---
CARD_RANKS = {'J': 1, 'Q': 2, 'K': 3}
RAISE_AMOUNTS = {1: 2, 2: 4} # Raise amounts for round 1 and 2
MAX_RAISES = 2

def _get_round_pot_contribution(game_state: Dict, player_id: int) -> int:
    """Helper to get a player's contribution to the pot in the current round."""
    return game_state.players[player_id].public.round_pot_contribution

def _showdown(game_state: Dict, logger: "EnvLogger") -> Dict:
    """
    Determines the winner at the end of the game and updates the state.
    Handles ties correctly.
    """
    logger.info("Proceeding to showdown.")
    public_card = game_state.common.faceup_cards.public_card
    player0 = game_state.players[0]
    player1 = game_state.players[1]
    
    p0_card = player0.facedown_cards.hand[0]
    p1_card = player1.facedown_cards.hand[0]

    logger.info(f"Player 0 has: {p0_card.get_str()}")
    logger.info(f"Player 1 has: {p1_card.get_str()}")
    logger.info(f"The public card is: {public_card.get_str()}")

    # Check for pairs with the public card
    p0_has_pair = p0_card.rank == public_card.rank
    p1_has_pair = p1_card.rank == public_card.rank

    if p0_has_pair and not p1_has_pair:
        logger.info("Player 0 wins with a pair.")
        game_state.common.winner = 0
    elif p1_has_pair and not p0_has_pair:
        logger.info("Player 1 wins with a pair.")
        game_state.common.winner = 1
    else: # This covers no pairs, or both players having a pair (which is impossible with this deck)
        # Compare high cards
        p0_rank = CARD_RANKS[p0_card.rank]
        p1_rank = CARD_RANKS[p1_card.rank]
        if p0_rank > p1_rank:
            logger.info("Player 0 wins with a higher card.")
            game_state.common.winner = 0
        elif p1_rank > p0_rank:
            logger.info("Player 1 wins with a higher card.")
            game_state.common.winner = 1
        else:
            logger.info("Tie game (equal high cards), the pot is split.")
            game_state.common.winner = 'tie'
            
    game_state.common.is_over = True
    return game_state

def _start_new_round(game_state: Dict, logger: "EnvLogger") -> Dict:
    """
    Handles the transition from the first betting round to the second.
    """
    logger.info("End of betting round 1.")
    game_state.common.round = 2
    game_state.common.num_raises = 0

    # Reveal the public card
    public_card = game_state.common.facedown_cards.deck.pop()
    game_state.common.faceup_cards.public_card = public_card
    logger.info(f"Public card is revealed: {public_card.get_str()}")
    
    # Reset pot contributions for the new round
    for player in game_state.players:
        player.public.round_pot_contribution = 0
        
    # Small blind player acts first in the second round
    game_state.common.current_player = game_state.common.small_blind_player
    
    return game_state

# --- Core Game Functions ---

def initiation(num_players, logger) -> "DotDict":
    """
    Initialize the game state for Leduc Hold'em.
    """
    if num_players != 2:
        raise ValueError("Leduc Hold'em must be played with 2 players.")
        
    game_state = DotDict({
        'common': {
            'num_players': 2,
            'current_player': 0,
            'round': 1,
            'num_raises': 0,
            'last_raise': 0,
            'small_blind_player': 0,
            'big_blind_player': 1,
            'winner': None,
            'is_over': False,
            'facedown_cards': {'deck': []},
            'faceup_cards': {'public_card': None},
        },
        'players': [
            DotDict({
                'public': {'folded': False, 'total_pot_contribution': 0, 'round_pot_contribution': 0},
                'facedown_cards': {'hand': []},
            }) for _ in range(num_players)
        ],
    })
    
    game_state = init_deck(game_state, logger)

    # small blind is always player 0, big blind is player 1
    blind_players = [0, 1]
    # random.shuffle(blind_players)
    sb_player_id, bb_player_id = blind_players[0], blind_players[1]
    game_state.common.small_blind_player = sb_player_id
    game_state.common.big_blind_player = bb_player_id

    # Post blinds
    sb_player = game_state.players[sb_player_id]
    bb_player = game_state.players[bb_player_id]
    
    sb_player.public.total_pot_contribution = 1
    sb_player.public.round_pot_contribution = 1
    bb_player.public.total_pot_contribution = 2
    bb_player.public.round_pot_contribution = 2
    game_state.common.last_raise = 1 # The BB is effectively the first 'raise'
    
    logger.info(f"Player {sb_player_id} is Small Blind (1), Player {bb_player_id} is Big Blind (2).")
    
    game_state = init_deal(game_state, logger)
    
    # Small blind acts first
    game_state.common.current_player = sb_player_id
    
    return game_state

def init_deck(game_state: Dict, logger: "EnvLogger") -> Dict:
    """
    Initializes and shuffles the 6-card Leduc deck.
    """
    ranks = ['J', 'Q', 'K']
    deck = [LLMCard({'rank': rank}) for rank in ranks for _ in range(2)]
    random.shuffle(deck)
    game_state.common.facedown_cards.deck = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: Dict, logger: "EnvLogger") -> Dict:
    """
    Deals one private card to each of the two players.
    """
    deck = game_state.common.facedown_cards.deck
    for i in range(game_state.common.num_players):
        card = deck.pop()
        game_state.players[i].facedown_cards.hand.append(card)
        logger.info(f"Player {i} is dealt a card.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: "EnvLogger") -> Dict:
    """
    Processes a player's action and updates the game state.
    """
    player_id = game_state.common.current_player
    opponent_id = 1 - player_id
    player = game_state.players[player_id]

    # === BUG FIX: Start ===
    # Add a defensive check to handle cases where a faulty agent returns None or an invalid action.
    # Defaulting to 'fold' is the safest way to prevent a crash and keep the game state valid.
    if not action or 'action' not in action:
        logger.warning(f"Player {player_id} provided an invalid action: {action}. Defaulting to 'fold'.")
        action = {'action': 'fold'}
    # === BUG FIX: End ===
    
    action_type = action['action']
    logger.info(f"Player {player_id} chose action: {action_type}")

    if action_type == 'fold':
        game_state.common.winner = opponent_id
        game_state.common.is_over = True
        player.public.folded = True
        return game_state

    # Calculate amounts for call/raise
    call_amount = _get_round_pot_contribution(game_state, opponent_id) - _get_round_pot_contribution(game_state, player_id)
    raise_amount = RAISE_AMOUNTS[game_state.common.round]
    
    if action_type == 'call':
        player.public.total_pot_contribution += call_amount
        player.public.round_pot_contribution += call_amount
        
        # If a call is made, the betting round is over
        if game_state.common.round == 1:
            return _start_new_round(game_state, logger)
        else:
            return _showdown(game_state, logger)
            
    elif action_type == 'check':
        # This only happens if both players have contributed equally. It ends the betting round.
        if game_state.common.round == 1:
            return _start_new_round(game_state, logger)
        else:
            return _showdown(game_state, logger)

    elif action_type == 'raise':
        amount_to_put = call_amount + raise_amount
        player.public.total_pot_contribution += amount_to_put
        player.public.round_pot_contribution += amount_to_put
        game_state.common.num_raises += 1
        game_state.common.last_raise = raise_amount
        # After a raise, it's the other player's turn
        game_state.common.current_player = opponent_id
        
    return game_state

def get_legal_actions(game_state: Dict) -> list[dict]:
    """
    Gets the legal actions for the current player.
    """
    player_id = game_state.common.current_player
    opponent_id = 1 - player_id
    
    legal_actions = []
    
    # Calculate the amount needed to call
    call_amount = _get_round_pot_contribution(game_state, opponent_id) - _get_round_pot_contribution(game_state, player_id)
    
    # Action: Fold
    legal_actions.append({'action': 'fold'})
    
    # Action: Call or Check
    if call_amount == 0:
        # If no bet to call, the action is 'check'
        legal_actions.append({'action': 'check'})
    else:
        legal_actions.append({'action': 'call'})
        
    # Action: Raise
    # Can only raise if the number of raises is below the maximum
    if game_state.common.num_raises < MAX_RAISES:
        legal_actions.append({'action': 'raise'})
        
    assert legal_actions, "get_legal_actions must not return an empty list."
    # import ipdb; ipdb.set_trace()
    return legal_actions

def get_payoffs(game_state: Dict, logger: "EnvLogger") -> List[Union[int, float]]:
    """
    Returns the payoffs for each player at the end of the game.
    The payoff is the net amount won or lost.
    """
    winner = game_state.common.winner
    if winner is None:
        return [0, 0] # Should not happen in a finished game

    if winner == 'tie':
        # No money is exchanged. Payoff is 0 as they each get their bet back.
        logger.info("Payoffs: Pot is split, net payoffs are 0 for both players.")
        return [0, 0]
        
    loser = 1 - winner
    
    # The winner's payoff is the amount the loser contributed to the pot.
    winner_payoff = game_state.players[loser].public.total_pot_contribution
    # The loser's payoff is the negative of their own contribution.
    loser_payoff = -game_state.players[loser].public.total_pot_contribution
    
    payoffs = [0, 0]
    payoffs[winner] = winner_payoff
    payoffs[loser] = loser_payoff
    
    logger.info(f"Payoffs: Player {winner} wins {winner_payoff}. Player {loser} loses {abs(loser_payoff)}.")
    return payoffs
"""End of the game code"""