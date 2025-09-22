
"""Beginning of the game code"""
game_name = 'CrazyEights'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5]


def initiation(num_players: int, logger) -> Dict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'winner': None,
            'current_suit': None,
            'is_over': False,
            'faceup_cards':{
                'played_cards': [],
                'target_card': None,
            },
            'facedown_cards':{
                'deck': init_deck(),
            },
        },
        'players': [
            DotDict({
                'public':{
                    'score': 0,
                },
                'facedown_cards':{
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
    ranks = ['2', '3', '4', '5', '6', '7', '9', '10', 'J', 'Q', 'K', 'A', '8']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    for suit in suits:
        for rank in ranks:
            deck.append(LLMCard({'rank': rank, 'suit': suit}))
    random.shuffle(deck)
    return deck


def init_dealing(game_state: Dict, logger) -> Dict:
    """Deal the initial cards to each player and initialize the discard pile."""
    logger.info("Dealing initial cards...")
    deck = game_state.common.facedown_cards.deck
    for player in game_state.players:
        player.facedown_cards.hand = [deck.pop() for _ in range(5)]
    card = deck.pop()
    while card.rank == '8':
        deck.insert(0, card)
        card = deck.pop()
    game_state.common.faceup_cards.played_cards.append(card)
    game_state.common.faceup_cards.target_card = card
    game_state.common.current_suit = card.suit
    logger.info(f"Initial target card: {card.rank} of {card.suit}")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger) -> DotDict:
    """Process the action and update the game state."""
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    played_cards = game_state.common.faceup_cards.played_cards
    hand = player.facedown_cards.hand

    if action['action'] == 'draw':
        if not game_state.common.facedown_cards.deck:
            logger.info('Stockpile is exhausted, player must pass if no card is playable.')
            game_state.common.current_player = (current_player + 1) % game_state.common.num_players
        else:
            card = game_state.common.facedown_cards.deck.pop()
            hand.append(card)
            logger.info(f"Player {current_player} draws a card")
            if not get_legal_actions(game_state, current_player)[0]:
                logger.info('No legal actions available, player must pass.')
                game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    elif action['action'] == 'pass':
        logger.info(f"Player {current_player} passes due to no legal actions available.")
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players
        if all(get_legal_actions(game_state, p)[0]['action'] == "pass" for p in range(game_state.common.num_players)) and not game_state.common.facedown_cards.deck:
            logger.info('All players pass, reshuffling the discard pile.')
            game_state.common.is_over = True
            logger.info('Game concludes as no cards available for play or to draw by any player.')
    
    else:
        card_index = action['args']['card_idx']
        card = hand.pop(card_index)
        logger.info(f"Player {current_player} plays {card.rank} of {card.suit}")

        if card.rank == '8':
            game_state.common.current_suit = action['args']['target_suit']
            card.suit = action['args']['target_suit']
            logger.info(f"Current suit changed to {action['args']['target_suit']}")
        else:
            game_state.common.current_suit = card.suit

        played_cards.append(card)
        game_state.common.faceup_cards.target_card = card

        if not hand:
            logger.info(f"Player {current_player} wins the round!")
            game_state.common.is_over = True
            game_state.common.winner = current_player
        else:
            game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    return game_state

def get_legal_actions(game_state: Dict, player_id: int=None) -> Tuple[List[dict]]:
    """Get all legal actions for the current player."""
    legal_actions = []
    player_id = game_state.common.current_player if player_id is None else player_id
    player = game_state.players[player_id]

    if not game_state.common.is_over:
        for i, card in enumerate(player.facedown_cards.hand):
            if card.rank == '8':
                for suit in ['hearts', 'diamonds', 'clubs', 'spades']:
                    legal_actions.append({'action': 'play', 'args':{'card_idx': i, 'target_suit': suit}})
            elif card.suit == game_state.common.current_suit or card.rank == game_state.common.faceup_cards.target_card.rank:
                legal_actions.append({'action': 'play', 'args':{'card_idx': i}})
        if game_state.common.facedown_cards.deck:
            legal_actions.append({'action': 'draw'})
        if not legal_actions:
            if game_state.common.facedown_cards.deck:
                legal_actions.append({'action': 'draw'})
            legal_actions.append({'action': 'pass'})
    return legal_actions

def card_point_value(rank: str) -> int:
    """Calculate the point value of a card."""
    if rank == '8':
        return 50
    elif rank in ['10', 'J', 'Q', 'K']:
        return 10
    elif rank == 'A':
        return 1
    else:
        return int(rank)

def get_payoffs(game_state: Dict, logger) -> List[Union[int, float]]:
    """Get the payoffs for each player."""
    payoffs = [0] * game_state.common.num_players
    if game_state.common.winner is not None:
        for i, player in enumerate(game_state.players):
            if i != game_state.common.winner:
                score = sum(card_point_value(card.rank) for card in player.facedown_cards.hand)
                payoffs[i] = -score
                payoffs[game_state.common.winner] += score
                logger.info(f"Player {i} has {score} points in hand.")
        logger.info(f"Player {game_state.common.winner} wins the round with {payoffs[game_state.common.winner]} points.")
    return payoffs
"""End of the game code"""