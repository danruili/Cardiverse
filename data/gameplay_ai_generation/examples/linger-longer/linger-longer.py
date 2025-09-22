"""Beginning of the game code"""
game_name = 'Linger Longer'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5]

def initiation(num_players: int, logger) -> DotDict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'trump_suit': None,
            'is_over': False,
            'faceup_cards': {
                'current_trick': [],
            },
            'facedown_cards': {
                'deck': init_deck(),
            },
        },
        'players': [
            DotDict({
                'public': {
                    'tricks_won': 0,
                },
                'private': {},
                'facedown_cards': {
                    'hand': [],
                },
                'faceup_cards': {},
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_dealing(game_state, logger)
    return game_state

def init_deck() -> List[LLMCard]:
    """Initialize the deck."""
    deck = []
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    for suit in suits:
        for rank in ranks:
            deck.append(LLMCard({'rank': rank, 'suit': suit}))
    random.shuffle(deck)
    return deck

def init_dealing(game_state: Dict, logger) -> Dict:
    """Deal the initial cards to each player and determine the trump suit."""
    logger.info("Dealing initial cards to players...")
    deck = game_state.common.facedown_cards.deck
    num_players = game_state.common.num_players
    for player in game_state.players:
        player.facedown_cards.hand = [deck.pop() for _ in range(num_players)]
        
    trump_card = deck.pop()
    game_state.common.trump_suit = trump_card.field['suit']
    logger.info(f"The trump suit is determined by {trump_card.get_str()} as {game_state.common.trump_suit}.")
    # Place the trump card back to ensure the deck continuity
    deck.append(trump_card)
    return game_state

def card_value(rank: str) -> int:
    """Get the value of a card for ranking purposes."""
    rank_order = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, '10': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
    return rank_order[rank]

def proceed_round(action: dict, game_state: DotDict, logger) -> DotDict:
    """Process the action and update the game state."""
    current_player = game_state.common.current_player
    player = game_state.players[current_player]

    if action['action'] == 'play':
        suit = action['args']['suit']
        rank = action['args']['rank']
        hand = player.facedown_cards.hand
        played_card = None
        for i, card in enumerate(hand):
            if card.field['suit'] == suit and card.field['rank'] == rank:
                played_card = hand.pop(i)
                break
        if played_card:
            game_state.common.faceup_cards.current_trick.append((played_card, current_player))
            logger.info(f"Player {current_player} plays {played_card.get_str()}.")

    # Check if trick is complete
    if len(game_state.common.faceup_cards.current_trick) == game_state.common.num_players:
        logger.info("Trick complete.")
        game_state = resolve_trick(game_state, logger)
        game_state.common.faceup_cards.current_trick = []
        game_state = check_game_over(game_state, logger)

    # Update current player if game is not over
    if not game_state.common.is_over:
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players
    return game_state

def resolve_trick(game_state: DotDict, logger) -> DotDict:
    """Determine the winner of the current trick."""
    trick = game_state.common.faceup_cards.current_trick
    trump_suit = game_state.common.trump_suit

    winning_card, winning_player = trick[0]
    for card, player in trick:
        if (card.field['suit'] == trump_suit and winning_card.field['suit'] != trump_suit) or \
           (card.field['suit'] == winning_card.field['suit'] and card_value(card.field['rank']) > card_value(winning_card.field['rank'])):
            winning_card, winning_player = card, player

    logger.info(f"Player {winning_player} wins the trick with {winning_card.get_str()}.")
    game_state.players[winning_player].public.tricks_won += 1

    # Replenish the winner's hand
    deck = game_state.common.facedown_cards.deck
    if deck:
        new_card = deck.pop()
        game_state.players[winning_player].facedown_cards.hand.append(new_card)
        logger.info(f"Player {winning_player} draws a card from the deck.")
    else:
        logger.info("No more cards in the stock pile to draw.")

    game_state.common.current_player = winning_player
    return game_state

def get_legal_actions(game_state: Dict) -> List[dict]:
    """Get all legal actions for the current player."""
    player_id = game_state.common.current_player
    player = game_state.players[player_id]
    legal_actions = []
    if not game_state.common.is_over:
        for card in player.facedown_cards.hand:
            legal_actions.append({'action': 'play', 'args': {'suit': card.field['suit'], 'rank': card.field['rank']}})
    if not legal_actions:
        # If no cards can be played and possibly no cards to draw, 'pass' action is added
        legal_actions.append({'action': 'pass'})
    return legal_actions

def check_game_over(game_state: DotDict, logger) -> DotDict:
    """Check if the game is over and update the state."""
    active_players = [p for p in game_state.players if len(p.facedown_cards.hand) > 0]
    if len(active_players) == 1:
        game_state.common.is_over = True
        game_state.common.winner = game_state.players.index(active_players[0])
        logger.info(f"Player {game_state.common.winner} wins the game as the last player remaining with cards.")
    elif not game_state.common.facedown_cards.deck:
        # Determine the player with the most tricks won if the deck is empty
        max_tricks = max(p.public.tricks_won for p in game_state.players)
        top_players = [p for p in range(game_state.common.num_players) if game_state.players[p].public.tricks_won == max_tricks]
        if len(top_players) == 1:
            game_state.common.winner = top_players[0]
            logger.info(f"Player {game_state.common.winner} wins the game with the most tricks won.")
        else:
            logger.info("The game is a draw since multiple players have the same highest trick count and no cards are left.")
        game_state.common.is_over = True
    return game_state

def get_payoffs(game_state: Dict, logger) -> List[int]:
    """Payoffs: 1 for the winner and 0 for others."""
    payoffs = [0] * game_state.common.num_players
    if game_state.common.is_over and game_state.common.winner is not None:
        payoffs[game_state.common.winner] = 1
    return payoffs
"""End of the game code"""