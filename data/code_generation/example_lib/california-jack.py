
"""Beginning of the game code"""
game_name = 'CaliforniaJack'
recommended_num_players = 2
num_players_range = [2]

def init_deck() -> List[LLMCard]:
    """Initialize the deck with shuffled cards."""
    deck = []
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    for suit in suits:
        for rank in ranks:
            deck.append(LLMCard({'rank': rank, 'suit': suit}))
    random.shuffle(deck)
    return deck

def initiation(num_players: int, logger) -> DotDict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'current_leader': 0,
            'current_winner': None,
            'is_over': False,
            'winner': None,
            'trump_suit': None,

            'facedown_cards': {
                'deck': init_deck(),
            },
            'faceup_cards': {
                'trump_card': None,
                'current_trick': [],
            },
        },
        'players': [
            DotDict({
                'public': {
                    'trick_points': 0,
                },
                'private': {},
                'facedown_cards': {
                    'hand': []
                },
                'faceup_cards': {
                    'collected_cards': []
                },
            }) for _ in range(num_players)
        ],
    })
    game_state = init_dealing(game_state, logger)
    return game_state

def init_dealing(game_state: DotDict, logger) -> DotDict:
    """Deal cards to players and determine trump suit."""
    logger.info("Dealing cards to players...")
    deck = game_state.common.facedown_cards.deck
    num_players = game_state.common.num_players
    # Each player gets 6 cards initially
    for p in range(num_players):
        game_state.players[p].facedown_cards.hand = [deck.pop() for _ in range(6)]
    # The bottom card of the deck indicates trump
    trump_card = deck[-1]
    game_state.common.faceup_cards.trump_card = trump_card
    game_state.common.trump_suit = trump_card.field['suit']
    logger.info(f"Trump card is: {trump_card.get_str()}, Trump suit: {game_state.common.trump_suit}")
    return game_state

def card_value(rank: str) -> int:
    """Get the value of a card for ranking purposes."""
    rank_order = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, '10': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
    return rank_order[rank]

def card_points(card: LLMCard) -> int:
    """Get the point value of a card."""
    rank = card.field['rank']
    if rank == '10':
        return 10
    elif rank == 'A':
        return 4
    elif rank == 'K':
        return 3
    elif rank == 'Q':
        return 2
    elif rank == 'J':
        return 1
    else:
        return 0

def proceed_round(action: dict, game_state: DotDict, logger) -> DotDict:
    """
    Process the action and update the game state.
    Args:
        action (dict): action is a dict with a mandatory field 'action' and optional fields in 'args'.
                       For example: {'action': 'play', 'args': {'suit': 'hearts', 'rank': 'K'}}
    """
    current_player = game_state.common.current_player
    player = game_state.players[current_player]

    if action['action'] == 'play':
        suit = action['args']['suit']
        rank = action['args']['rank']
        hand = player.facedown_cards.hand
        # Find and play the card
        played_card_index = None
        for i, c in enumerate(hand):
            if c.field['suit'] == suit and c.field['rank'] == rank:
                played_card_index = i
                break
        if played_card_index is not None:
            played_card = hand.pop(played_card_index)
            game_state.common.faceup_cards.current_trick.append(played_card)
            logger.info(f"Player {current_player} plays {played_card.get_str()}.")
        else:
            logger.info(f"Player {current_player} attempted to play an invalid card: {suit}-{rank}")

    # Check if trick is complete
    if len(game_state.common.faceup_cards.current_trick) == game_state.common.num_players:
        logger.info(f"Trick complete: {cards2list(game_state.common.faceup_cards.current_trick)}")
        game_state = resolve_trick(game_state, logger)
        game_state.common.faceup_cards.current_trick = []
        game_state = check_round_over(game_state, logger)
        return game_state

    # Update current player if round not over
    if not game_state.common.is_over:
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    # Check if round/game over
    game_state = check_round_over(game_state, logger)
    return game_state

def resolve_trick(game_state: DotDict, logger) -> DotDict:
    """Determine the winner of the current trick."""
    trick = game_state.common.faceup_cards.current_trick
    trump_suit = game_state.common.trump_suit
    leading_suit = trick[0].field['suit']
    current_leader = game_state.common.current_leader

    winning_card = trick[0]
    winning_player = current_leader
    for i, card in enumerate(trick):
        # Check if card beats the current winning_card
        if (card.field['suit'] == trump_suit and winning_card.field['suit'] != trump_suit) or \
           (card.field['suit'] == winning_card.field['suit'] and card_value(card.field['rank']) > card_value(winning_card.field['rank'])):
            winning_card = card
            winning_player = (current_leader + i) % game_state.common.num_players

    logger.info(f"Player {winning_player} wins the trick with {winning_card.get_str()}.")

    # Add trick cards to winner's collected pile
    game_state.players[winning_player].faceup_cards.collected_cards.extend(trick)

    # Deal one more card to each player if deck not empty
    deck = game_state.common.facedown_cards.deck
    for pid, p in enumerate(game_state.players):
        if deck:
            new_card = deck.pop()
            p.facedown_cards.hand.append(new_card)
            logger.info(f"Player {pid} draws a card from the deck.")

    game_state.common.current_leader = winning_player
    game_state.common.current_player = winning_player
    logger.info(f"Player {winning_player} leads the next trick.")
    return game_state

def check_round_over(game_state: DotDict, logger) -> DotDict:
    """Check if the round (or game) is over and update the state."""
    # Round is over if all hands are empty and deck is empty
    if all(len(p.facedown_cards.hand) == 0 for p in game_state.players) and len(game_state.common.facedown_cards.deck) == 0:
        game_state.common.is_over = True
        logger.info("Round is over as all cards have been played.")

    # Always check scores, end game if someone reaches threshold
    game_state = calculate_scores(game_state, logger)
    return game_state

def calculate_scores(game_state: DotDict, logger) -> DotDict:
    """Calculate the scores for each player and determine if someone wins."""
    trump_suit = game_state.common.trump_suit
    num_players = game_state.common.num_players

    # Calculate trick_points as per California Jack scoring
    def has_rank(player_cards, rank, suit):
        return any(c.field['rank'] == rank and c.field['suit'] == suit for c in player_cards)

    # High (A of trump), Low (2 of trump), Jack (J of trump), and Game points
    for pid in range(num_players):
        collected = game_state.players[pid].faceup_cards.collected_cards
        high = 1 if has_rank(collected, 'A', trump_suit) else 0
        low = 1 if has_rank(collected, '2', trump_suit) else 0
        jack = 1 if has_rank(collected, 'J', trump_suit) else 0
        game_points = sum(card_points(card) for card in collected)

        total_points = high + low + jack + game_points
        game_state.players[pid].public.trick_points = total_points

    # Determine if someone wins
    for pid, player in enumerate(game_state.players):
        score = player.public.trick_points
        if score >= 10:  # Threshold to win
            game_state.common.winner = pid
            game_state.common.is_over = True
            logger.info(f"Player {pid} wins the game with {score} points. Collected cards: {cards2list(player.faceup_cards.collected_cards)}")

    return game_state

def get_legal_actions(game_state: DotDict) -> List[dict]:
    """Get legal actions for the current player."""
    if game_state.common.is_over:
        return []

    player_id = game_state.common.current_player
    player = game_state.players[player_id]
    hand = player.facedown_cards.hand
    current_trick = game_state.common.faceup_cards.current_trick
    trump_suit = game_state.common.trump_suit
    leader = game_state.common.current_leader

    # If leader, can play any card
    if player_id == leader or len(current_trick) == 0:
        return [{'action': 'play', 'args': {'suit': c.field['suit'], 'rank': c.field['rank']}} for c in hand]
    else:
        # Must follow suit if possible
        leading_suit = current_trick[0].field['suit']
        follow_actions = [{'action': 'play', 'args': {'suit': c.field['suit'], 'rank': c.field['rank']}} for c in hand if c.field['suit'] == leading_suit]
        if follow_actions:
            return follow_actions
        # If cannot follow suit, try playing trump
        trump_actions = [{'action': 'play', 'args': {'suit': c.field['suit'], 'rank': c.field['rank']}} for c in hand if c.field['suit'] == trump_suit]
        if trump_actions:
            return trump_actions
        # Else play any card
        return [{'action': 'play', 'args': {'suit': c.field['suit'], 'rank': c.field['rank']}} for c in hand]

def get_payoffs(game_state: DotDict, logger) -> List[int]:
    """Payoffs: 1 for winner, 0 for others."""
    payoffs = [0] * game_state.common.num_players
    if game_state.common.winner is not None:
        payoffs[game_state.common.winner] = 1
    return payoffs
"""End of the game code"""
