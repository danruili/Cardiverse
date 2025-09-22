
"""Beginning of the game code"""  

game_name = 'BullPoker'
recommended_num_players = 5
num_players_range = [4, 5, 6, 7]

def initiation(num_players: int, logger) -> DotDict:
    """
    Initialize the game state. 
    This sets up a poker-like scenario with face-down and face-up cards, betting rounds, and folding.
    """
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'direction': 1,
            'winner': None,
            'is_over': False,
            'folded_players': set(),
            'played_players': set(),
            'facedown_reveal_index': 0,
            'facedown_cards': {
                'deck': [],
            },
            'faceup_cards': {
                'discard': [],
            },
            'pot': 0,
            'current_bet': 0,
        },
        'players': [
            DotDict({
                'public': {
                    # Publicly known info about the player (no card info)
                    'current_bet_amount': 0,
                },
                'private': {
                    # Private info (if needed) can go here
                },
                'facedown_cards': {
                    'hole_cards': []  # Player's private hole cards
                },
                'faceup_cards': {
                    'shown_cards': []  # Cards revealed/face-up in front of the player
                },
            }) for _ in range(num_players)
        ],
    })

    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return game_state


def init_deck(game_state: DotDict, logger) -> DotDict:
    """Initialize a standard 52-card deck for Poker and shuffle."""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state.common.facedown_cards.deck = deck
    logger.info("Deck initialized and shuffled.")
    return game_state


def init_deal(game_state: DotDict, logger) -> DotDict:
    """Deal three hole cards to each player as initial facedown cards."""
    logger.info("Dealing initial hole cards to each player...")
    for i, player in enumerate(game_state.players):
        player.facedown_cards.hole_cards = [game_state.common.facedown_cards.deck.pop() for _ in range(3)]
        logger.info(f"Player {i} received 3 hole cards.")
    return game_state


def proceed_round(action: Dict, game_state: DotDict, logger) -> DotDict:
    """
    Process the action, update the game state: the bets, folds, dealing of faceup cards, and
    eventually trigger a showdown if conditions are met.
    Actions format:
    - {'action': 'bet', 'args': {'amount': int}}
    - {'action': 'raise', 'args': {'amount': int}}
    - {'action': 'call'}
    - {'action': 'fold'}

    This function updates the state accordingly.
    """
    current_player = game_state.common.current_player
    logger.info(f"Processing action by player {current_player}: {action}")
    
    if action['action'] in ['bet', 'raise', 'call']:
        game_state = handle_betting(action, game_state, logger)
    elif action['action'] == 'fold':
        logger.info(f"Player {current_player} folds.")
        game_state.common.folded_players.add(current_player)
    else:
        logger.info("Unknown action, skipping.")

    # Check if game should progress to showdown or end
    game_state = check_for_showdown(game_state, logger)

    # Move to next player if game not over
    if not game_state.common.is_over:
        game_state.common.current_player = next_active_player(game_state)
        # Deal faceup or reveal facedown as necessary based on round progression
        game_state = deal_faceup_or_reveal(game_state, logger)

    return game_state


def handle_betting(action: Dict, game_state: DotDict, logger) -> DotDict:
    """Handle betting/raising/calling actions."""
    current_player = game_state.common.current_player
    player_state = game_state.players[current_player]
    game_state.common.played_players.add(current_player)

    if action['action'] in ['bet', 'raise']:
        amount = action['args']['amount']
        diff = amount - player_state.public.current_bet_amount
        game_state.common.pot += diff
        player_state.public.current_bet_amount = amount
        game_state.common.current_bet = amount
        logger.info(f"Player {current_player} {action['action']}s to {amount}.")
    elif action['action'] == 'call':
        diff = game_state.common.current_bet - player_state.public.current_bet_amount
        if diff > 0:
            game_state.common.pot += diff
            player_state.public.current_bet_amount = game_state.common.current_bet
        logger.info(f"Player {current_player} calls.")

    return game_state


def check_for_showdown(game_state: DotDict, logger) -> DotDict:
    """Check if conditions for a showdown or game end are met."""
    active_players = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]
    if len(active_players) == 1:
        # Only one player remains
        logger.info("Only one player remains. Game over.")
        game_state.common.is_over = True
        game_state.common.winner = active_players[0]
    elif all(len(p.facedown_cards.hole_cards) == 0 for i, p in enumerate(game_state.players) if i in active_players):
        # All facedown revealed, and presumably all faceup dealt
        logger.info("All hole cards revealed. Proceeding to showdown...")
        game_state.common.is_over = True
        game_state = determine_winner(game_state, logger)
    return game_state


def determine_winner(game_state: DotDict, logger) -> DotDict:
    """Determine the winner(s) by evaluating the poker hands of all active players."""
    logger.info("Determining the winner via showdown...")
    active_players = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]

    best_hand_score = -1
    best_hand_ranks = []
    winning_players = []

    for i in active_players:
        player = game_state.players[i]
        # Combine facedown and faceup cards
        player_cards = player.facedown_cards.hole_cards + player.faceup_cards.shown_cards
        hand_score, hand_ranks = evaluate_hand(player_cards)
        logger.info(f"Player {i}: hand_score={hand_score}, ranks={hand_ranks}")

        if (hand_score > best_hand_score) or (hand_score == best_hand_score and hand_ranks > best_hand_ranks):
            best_hand_score = hand_score
            best_hand_ranks = hand_ranks
            winning_players = [i]
        elif hand_score == best_hand_score and hand_ranks == best_hand_ranks:
            winning_players.append(i)

    game_state.common.winner = winning_players if len(winning_players) > 1 else winning_players[0]
    logger.info(f"Winner(s): {game_state.common.winner}")
    return game_state


def evaluate_hand(cards: List[LLMCard]) -> Tuple[int, List[int]]:
    """Evaluate the poker hand and return a score and a sorted rank list."""
    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    rank_counts = {}
    suit_counts = {}

    for card in cards:
        r = card.field['rank']
        s = card.field['suit']
        rank_counts[r] = rank_counts.get(r, 0) + 1
        suit_counts[s] = suit_counts.get(s, 0) + 1

    sorted_ranks = sorted([rank_values[r] for r in rank_counts], reverse=True)
    is_flush = len(suit_counts) == 1
    is_straight = (len(rank_counts) == 5 and (sorted_ranks[0] - sorted_ranks[-1] == 4))

    # Simple scoring system, akin to standard poker hands
    max_count = max(rank_counts.values())
    if max_count == 5:
        return (10, sorted_ranks)
    if is_straight and is_flush:
        return (9, sorted_ranks)
    if 4 in rank_counts.values():
        return (8, sorted_ranks)
    if 3 in rank_counts.values() and 2 in rank_counts.values():
        return (7, sorted_ranks)
    if is_flush:
        return (6, sorted_ranks)
    if is_straight:
        return (5, sorted_ranks)
    if 3 in rank_counts.values():
        return (4, sorted_ranks)
    if list(rank_counts.values()).count(2) == 2:
        return (3, sorted_ranks)
    if 2 in rank_counts.values():
        return (2, sorted_ranks)
    return (1, sorted_ranks)  # High card


def next_active_player(game_state: DotDict) -> int:
    """Get the next player who hasn't folded."""
    np = game_state.common.num_players
    next_p = (game_state.common.current_player + 1) % np
    while next_p in game_state.common.folded_players:
        next_p = (next_p + 1) % np
    return next_p


def deal_faceup_or_reveal(game_state: DotDict, logger) -> DotDict:
    """
    If all active players have acted this round:
      - If players can still receive more faceup cards, deal them.
      - Otherwise, reveal one of their facedown cards.
    """
    active_players = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]
    if all(p in game_state.common.played_players for p in active_players):
        # Check if we need to deal faceup cards or reveal facedown
        if any(len(game_state.players[i].faceup_cards.shown_cards) < 4 for i in active_players):
            # Deal one faceup card to each active player
            logger.info("Dealing faceup cards to active players...")
            for i in active_players:
                card = game_state.common.facedown_cards.deck.pop()
                game_state.players[i].faceup_cards.shown_cards.append(card)
                logger.info(f"Player {i} gets a faceup card: {card}")
        else:
            # Reveal a facedown card
            if game_state.common.facedown_reveal_index < 3:
                logger.info("Revealing a facedown card for each active player...")
                for i in active_players:
                    hole_cards = game_state.players[i].facedown_cards.hole_cards
                    if hole_cards:
                        revealed_card = hole_cards.pop()  # reveal the last hole card
                        game_state.players[i].faceup_cards.shown_cards.append(revealed_card)
                        logger.info(f"Player {i} reveals a hole card: {revealed_card}")
                game_state.common.facedown_reveal_index += 1

        game_state.common.played_players = set()

    return game_state


def get_legal_actions(game_state: DotDict) -> List[Dict]:
    """
    Get all legal actions for the current player.
    Actions must be dicts with at least {'action': str} and optional 'args'.
    For betting:
    - If current_bet == 0: player can 'bet' with some amounts
    - Else player can 'raise', 'call', or 'fold'
    """
    current_player = game_state.common.current_player
    legal_actions = []

    if current_player not in game_state.common.folded_players and not game_state.common.is_over:
        if game_state.common.current_bet == 0:
            # Player can bet some amounts
            for amt in range(1, 4):
                legal_actions.append({'action': 'bet', 'args': {'amount': amt}})
        else:
            # Player can raise, call or fold
            for amt in range(game_state.common.current_bet + 1, game_state.common.current_bet + 4):
                legal_actions.append({'action': 'raise', 'args': {'amount': amt}})
            legal_actions.append({'action': 'call'})
            legal_actions.append({'action': 'fold'})

    return legal_actions


def get_payoffs(game_state: DotDict, logger) -> List[Union[int, float]]:
    """Distribute the pot to the winner or winners."""
    payoffs = [0] * game_state.common.num_players
    if game_state.common.winner is not None:
        if isinstance(game_state.common.winner, int):
            # Single winner
            payoffs[game_state.common.winner] = game_state.common.pot
            logger.info(f"Player {game_state.common.winner} wins the pot of {game_state.common.pot}.")
        else:
            # Split pot
            split_pot = game_state.common.pot / len(game_state.common.winner)
            for w in game_state.common.winner:
                payoffs[w] = split_pot
            logger.info(f"Players {game_state.common.winner} split the pot of {game_state.common.pot}.")
    return payoffs
"""End of the game code"""