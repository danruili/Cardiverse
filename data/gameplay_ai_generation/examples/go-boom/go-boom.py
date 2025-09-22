"""Beginning of the game code"""
game_name = 'GoBoom'
recommended_num_players = 4
num_players_range = [2, 3, 4]

def initiation(num_players: int, logger) -> DotDict:
    """
    Initialize the game state.
    """
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'winner': None,
            'is_over': False,
            'facedown_cards': {
                'deck': [],
            },
            'faceup_cards': {
                'trick': [],
                'lead_card': None,
            },
        },
        'players': [
            DotDict({
                'public': {
                    'played_cards': [],
                },
                'private': {},
                'facedown_cards': {
                    'hand': []
                },
                'faceup_cards': {}
            }) for _ in range(num_players)
        ],
    })

    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return game_state

def init_deck(game_state: DotDict, logger) -> DotDict:
    """Initialize a standard 52-card deck and shuffle."""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state.common.facedown_cards.deck = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: DotDict, logger) -> DotDict:
    """Deal 7 cards to each player."""
    logger.info("Dealing 7 cards to each player.")
    for idx, player in enumerate(game_state.players):
        player.facedown_cards.hand = [game_state.common.facedown_cards.deck.pop() for _ in range(7)]
        logger.info(f"Player {idx} receives 7 cards.")
    return game_state

def proceed_round(action: Dict, game_state: DotDict, logger) -> DotDict:
    current_player = game_state.common.current_player
    player_hand = game_state.players[current_player].facedown_cards.hand

    if action['action'] == 'play':
        card = action['args']['card']
        player_hand.remove(card)
        game_state.common.faceup_cards.trick.append(card)
        game_state.players[current_player].public.played_cards.append(card)
        logger.info(f"Player {current_player} plays {card}")

        # Set lead_card if not already set or reset for the new round
        if game_state.common.faceup_cards.lead_card is None:
            game_state.common.faceup_cards.lead_card = card
            logger.info(f"{card} is the lead card of this trick.")

    elif action['action'] == 'draw':
        if game_state.common.facedown_cards.deck:
            drawn_card = game_state.common.facedown_cards.deck.pop()
            player_hand.append(drawn_card)
            logger.info(f"Player {current_player} draws a card from the deck.")
        else:
            logger.info(f"Player {current_player} cannot draw as the deck is empty.")

    if len(game_state.common.faceup_cards.trick) == game_state.common.num_players:
        game_state = resolve_trick(game_state, logger)

    # Ensure the round actually moves on when all players choose to pass
    all_pass = all(action['action'] == 'pass' for action in get_legal_actions(game_state))
    if all_pass:
        game_state = resolve_trick(game_state, logger)

    game_state = check_game_over(game_state, logger)

    if not game_state.common.is_over:
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players
    return game_state

def resolve_trick(game_state: DotDict, logger) -> DotDict:
    lead_suit = game_state.common.faceup_cards.lead_card.field['suit'] if game_state.common.faceup_cards.lead_card else None
    highest_card_value = -1
    trick_winner = game_state.common.current_player

    for i, card in enumerate(game_state.common.faceup_cards.trick):
        card_value_ = card_value(card.field['rank'])
        if card.field['suit'] == lead_suit and card_value_ > highest_card_value:
            highest_card_value = card_value_
            trick_winner = (game_state.common.current_player + i) % game_state.common.num_players

    game_state.common.current_player = trick_winner
    game_state.common.faceup_cards.trick.clear()
    game_state.common.faceup_cards.lead_card = None
    logger.info(f"Trick resolved. Player {trick_winner} wins the trick.")

    return game_state

def card_value(rank: str) -> int:
    values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 1}
    return values[rank]

def check_game_over(game_state: DotDict, logger) -> DotDict:
    if any(len(player.facedown_cards.hand) == 0 for player in game_state.players):
        game_state.common.is_over = True
        for idx, player in enumerate(game_state.players):
            if len(player.facedown_cards.hand) == 0:
                game_state.common.winner = idx
                logger.info(f"Player {idx} gets rid of all cards and wins the game.")
                break

    if game_state.common.is_over:
        logger.info("Game over. Calculating payoffs.")

    return game_state

def get_legal_actions(game_state: DotDict) -> List[Dict]:
    current_player = game_state.common.current_player
    if game_state.common.is_over:
        return []

    player_hand = game_state.players[current_player].facedown_cards.hand
    lead_card = game_state.common.faceup_cards.lead_card
    legal_actions = []  # Start with an empty list of legal actions

    if lead_card is None or not game_state.common.faceup_cards.trick:
        # No trick in progress, the leading player can play any card
        legal_actions.extend([{'action': 'play', 'args': {'card': card}} for card in player_hand])
    else:
        lead_suit = lead_card.field['suit']
        lead_rank = lead_card.field['rank']

        # Attempt to follow suit or match rank
        follow_suit_cards = [card for card in player_hand if card.field['suit'] == lead_suit]
        match_rank_cards = [card for card in player_hand if card.field['rank'] == lead_rank]

        playable_cards = follow_suit_cards + match_rank_cards
        if playable_cards:
            # Allow the player to play any of the playable cards
            legal_actions.extend([{'action': 'play', 'args': {'card': card}} for card in playable_cards])
        if not playable_cards and game_state.common.facedown_cards.deck:
            legal_actions.append({'action': 'draw'})
        elif not playable_cards and not game_state.common.facedown_cards.deck:
            legal_actions.append({'action': 'pass'})
    return legal_actions

def get_payoffs(game_state: DotDict, logger) -> List[int]:
    payoffs = [0] * game_state.common.num_players
    if game_state.common.winner is not None:
        winner = game_state.common.winner
        for idx, player in enumerate(game_state.players):
            if idx != winner:
                hand_value = sum(card_value(card.field['rank']) for card in player.facedown_cards.hand)
                payoffs[idx] = -hand_value
                payoffs[winner] += hand_value
        logger.info(f"Payoffs calculated: {payoffs}")
    return payoffs
"""End of the game code"""