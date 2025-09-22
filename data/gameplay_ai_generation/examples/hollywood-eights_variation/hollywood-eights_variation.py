
"""Beginning of the game code"""
game_name = 'CardMergeChallenge'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5]

def initiation(num_players: int, logger) -> Dict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'winner': None,
            'is_over': False,
            'starter_pile': {
                'top_card': None,
            },
            'facedown_cards': {
                'stock': init_deck(),
            },
            'discard_pile': [],
        },
        'players': [
            DotDict({
                'public': {
                    'score': 0,
                    'merged_sequences': [],
                },
                'facedown_cards': {
                    'hand': [],
                },
            }) for _ in range(num_players)
        ],
    })
    game_state = init_dealing(game_state, logger)
    return game_state

def init_deck() -> List[LLMCard]:
    """Initialize the deck."""
    ranks = ['A', '2', '3', '4', '5', '6', '7', '9', '10', 'J', 'Q', 'K', '8']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit, 'symbol': rank}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

def init_dealing(game_state: Dict, logger) -> Dict:
    """Deal the initial cards to each player and set the starter pile."""
    deck = game_state.common.facedown_cards.stock
    for player in game_state.players:
        player.facedown_cards.hand = [deck.pop() for _ in range(5)]
    top_card = deck.pop()
    # Ensure the top card is not a wild card
    while top_card.rank == '8':
        deck.insert(0, top_card)
        top_card = deck.pop()
    game_state.common.starter_pile.top_card = top_card
    logger.info(f"The starter pile's top card is {top_card}.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger) -> DotDict:
    """Process the action and update the game state."""
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    hand = player.facedown_cards.hand
    starter_pile = game_state.common.starter_pile

    if action['action'] == 'draw':
        if not game_state.common.facedown_cards.stock:
            if not game_state.common.discard_pile:
                game_state.common.is_over = True
                logger.info("The stock is exhausted. Game ends in a draw due to no available cards.")
                return game_state
            logger.info("Refilling stock from discard pile.")
            reshuffle_deck(game_state)
        
        card = game_state.common.facedown_cards.stock.pop()
        hand.append(card)
        logger.info(f"Player {current_player} draws a card from the stock.")
    elif action['action'] == 'play':
        card_idx = action['args']['card_idx']
        card = hand.pop(card_idx)
        game_state.common.discard_pile.append(starter_pile.top_card)
        starter_pile.top_card = card
        logger.info(f"Player {current_player} plays {card} onto the starter pile.")

    elif action['action'] == 'merge':
        merge_indices = action['args']['card_indices']
        sequence = [starter_pile.top_card] + [hand.pop(i) for i in sorted(merge_indices, reverse=True)]
        player.public.merged_sequences.append(sequence)
        player.public.score += len(sequence) * 10
        logger.info(f"Player {current_player} merges sequence: {cards2list(sequence)}. Total score: {player.public.score}.")

    elif action['action'] == 'use_wild':
        card_idx = action['args']['card_idx']
        new_suit = action['args']['new_suit']
        card = hand.pop(card_idx)
        card.suit = new_suit
        game_state.common.discard_pile.append(starter_pile.top_card)
        starter_pile.top_card = card
        logger.info(f"Player {current_player} uses a wild card to change the suit to {new_suit}.")

    elif action['action'] == 'draw':
        if not game_state.common.facedown_cards.stock:
            if not game_state.common.discard_pile:
                game_state.common.is_over = True
                logger.info("The stock is exhausted. Game ends in a draw due to no available cards.")
                return game_state
            logger.info("Refilling stock from discard pile.")
            reshuffle_deck(game_state)
        
        card = game_state.common.facedown_cards.stock.pop()
        hand.append(card)
        logger.info(f"Player {current_player} draws a card from the stock.")
    
    # Check if the player has reached the winning score of 150
    if player.public.score >= 150 and not game_state.common.is_over:
        game_state.common.is_over = True
        game_state.common.winner = current_player
        logger.info(f"Player {current_player} scores 150 points and wins the game!")

    # Advance to the next player
    game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    return game_state

def reshuffle_deck(game_state: Dict) -> None:
    """Refill the stock from the discard pile."""
    game_state.common.facedown_cards.stock = list(reversed(game_state.common.discard_pile[:-1]))
    game_state.common.discard_pile = [game_state.common.discard_pile[-1]]
    random.shuffle(game_state.common.facedown_cards.stock)

def get_legal_actions(game_state: Dict) -> List[dict]:
    """Get all legal actions for the current player."""
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    hand = player.facedown_cards.hand
    top_card = game_state.common.starter_pile.top_card
    legal_actions = []

    for i, card in enumerate(hand):
        if (card.suit == top_card.suit or card.rank == top_card.rank or card.symbol == top_card.symbol):
            legal_actions.append({'action': 'play', 'args': {'card_idx': i}})
    # Check for wild card usage
    for i, card in enumerate(hand):
        if card.rank == '8':  # Only allow wild card actions for Eights
            for suit in ['hearts', 'diamonds', 'clubs', 'spades']:
                legal_actions.append({'action': 'use_wild', 'args': {'card_idx': i, 'new_suit': suit}})

    if len(hand) >= 2:
        matching_symbol_cards = [i for i, card in enumerate(hand) if card.symbol == top_card.symbol]
        # Adjust the number of required cards for merging condition
        if len(matching_symbol_cards) >= 3:
            legal_actions.append({'action': 'merge', 'args': {'card_indices': matching_symbol_cards}})

    # Check if only draw actions are available and the deck is exhausted
    if not legal_actions and not game_state.common.facedown_cards.stock:
        game_state.common.is_over = True
        return []
    if not legal_actions:
        legal_actions.append({'action': 'draw'})

    return legal_actions

def card_point_value(card: LLMCard) -> int:
    """Calculate the point value of a card."""
    if card.rank in ['J', 'Q', 'K']:
        return 10
    elif card.rank == '8':
        return 20
    elif card.rank == 'A':
        return 15
    else:
        return int(card.rank)

def get_payoffs(game_state: Dict, logger) -> List[Union[int, float]]:
    """Return the payoffs for each player."""
    payoffs = [0] * game_state.common.num_players
    for i, player in enumerate(game_state.players):
        score = sum(card_point_value(card) for card in player.facedown_cards.hand)
        if i == game_state.common.winner:
            payoffs[i] = 150
            logger.info(f"Player {i} wins with a total score of 150 points!")
        else:
            payoffs[i] = -score
            logger.info(f"Player {i} has remaining cards worth {score} points.")
    return payoffs
"""End of the game code"""