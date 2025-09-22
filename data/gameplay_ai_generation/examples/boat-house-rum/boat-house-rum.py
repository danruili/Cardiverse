"""Beginning of the game code"""   

game_name = 'Boat House Rum'
recommended_num_players = 3
num_players_range = [2, 3, 4, 5, 6]

def initiation(num_players: int, logger) -> Dict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'winner': None,
            'has_drawn_cards_this_turn': False,
            'is_over': False,
            'faceup_cards':{
                'discard_pile': [],
            },
            'facedown_cards':{
                'stock': init_deck(),
            },
        },
        'players': [
            DotDict({
                'public': {
                    'score': 0,
                },
                'faceup_cards': {
                    'melds': [],
                },
                'facedown_cards': {
                    'hand': [],
                    'recent_discard_draw': [],
                },
            }) for _ in range(num_players)
        ],
    })
    game_state = init_dealing(game_state, logger)
    return game_state

def init_deck() -> List[LLMCard]:
    """Initialize the deck."""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

def init_dealing(game_state: Dict, logger) -> Dict:
    """Deal the initial cards to each player and set up the discard pile."""
    num_cards = {2: 10, 3: 7, 4: 7}.get(game_state.common.num_players, 6)
    logger.info(f"Dealing {num_cards} cards to each player")
    deck = game_state.common.facedown_cards.stock
    for player in game_state.players:
        player.facedown_cards.hand = [deck.pop() for _ in range(num_cards)]
    game_state.common.faceup_cards.discard_pile.append(deck.pop())
    return game_state

def proceed_round(action: dict, game_state: Dict, logger) -> Dict:
    """Process the action and update the game state."""
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    discard_pile = game_state.common.faceup_cards.discard_pile
    stock = game_state.common.facedown_cards.stock

    if action['action'] == 'draw':
        draw_from_stock = action['args']['source'] == 'stock'
        if draw_from_stock:
            player.facedown_cards.hand.extend(stock[-2:])
            game_state.common.facedown_cards.stock = stock[:-2]
        else:
            player.facedown_cards.hand.extend(discard_pile[-2:])
            game_state.common.faceup_cards.discard_pile = discard_pile[:-2]
        logger.info(f"Player {current_player} draws cards from {'stock' if draw_from_stock else 'discard pile'}.")
        game_state.common.has_drawn_cards_this_turn = True

    elif action['action'] == 'discard':
        card_idx = action['args']['card_idx']
        card = player.facedown_cards.hand.pop(card_idx)
        game_state.common.faceup_cards.discard_pile.append(card)
        player.facedown_cards.recent_discard_draw.clear()
        logger.info(f"Player {current_player} discards {card}.")
        game_state.common.has_drawn_cards_this_turn = False
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    elif action['action'] == 'laydown':
        meld_indices = action['args']['meld_indices']
        meld = [player.facedown_cards.hand[i] for i in meld_indices]
        player.faceup_cards.melds.append(meld)  # Update melds in public (faceup)
        for card in meld:
            player.facedown_cards.hand.remove(card)
        logger.info(f"Player {current_player} lays down meld: {meld}.")

    elif action['action'] == 'layoff':
        card_idx = action['args']['card_idx']
        meld_idx = action['args']['meld_idx']
        card = player.facedown_cards.hand.pop(card_idx)
        player.faceup_cards.melds[meld_idx].append(card)  # Update meld in public (faceup)
        logger.info(f"Player {current_player} lays off card {card} to meld {player.faceup_cards.melds[meld_idx]}.")

    check_end_conditions(game_state, logger)
    return game_state

def get_legal_actions(game_state: Dict, player_id: int = None) -> List[dict]:
    """Get all legal actions for the current player."""
    player_id = game_state.common.current_player if player_id is None else player_id
    player = game_state.players[player_id]
    legal_actions = []

    if not game_state.common.has_drawn_cards_this_turn:
        if game_state.common.facedown_cards.stock:
            legal_actions.append({'action': 'draw', 'args': {'source': 'stock'}})
        if game_state.common.faceup_cards.discard_pile:
            legal_actions.append({'action': 'draw', 'args': {'source': 'discard_pile'}})
    else:
        for i, card in enumerate(player.facedown_cards.hand):
            if card not in player.facedown_cards.recent_discard_draw:
                legal_actions.append({'action': 'discard', 'args': {'card_idx': i}})
        
        # Layoff actions should now use public.melds
        for i, card in enumerate(player.facedown_cards.hand):
            for j, meld in enumerate(player.faceup_cards.melds):
                if can_layoff(card, meld):
                    legal_actions.append({'action': 'layoff', 'args': {'card_idx': i, 'meld_idx': j}})

        # Laydown logic
        if len(player.facedown_cards.hand) >= 3:
            for i, card in enumerate(player.facedown_cards.hand):
                for j, card2 in enumerate(player.facedown_cards.hand[i + 1:], i + 1):
                    for k, card3 in enumerate(player.facedown_cards.hand[j + 1:], j + 1):
                        if check_valid_meld([card, card2, card3]):
                            legal_actions.append({'action': 'laydown', 'args': {'meld_indices': [i, j, k]}})
    
    return legal_actions

def get_payoffs(game_state: Dict, logger) -> List[int]:
    """Calculate and return payoffs for each player."""
    payoffs = []
    winner_ids = [game_state.common.winner] if game_state.common.winner is not None else []
    for i, player in enumerate(game_state.players):
        if i in winner_ids:
            payoffs.append(0)
            logger.info(f"Player {i} wins the game!")
        else:
            score = sum(card_point_value(card.rank) for card in player.facedown_cards.hand)
            # if the winner goes Rummy, the score is doubled
            if game_state.common.winner is not None:
                winner_id = game_state.common.winner
                if not game_state.players[winner_id].faceup_cards.melds:
                    score *= 2
                    logger.info(f"Player {winner_id} goes Rummy, so the score is doubled.")
            payoffs.append(-score)
            logger.info(f"Player {i} loses with a score of {score}.")
            
    return payoffs

def card_point_value(rank: str) -> int:
    """Calculate the point value of a card."""
    return int(rank) if rank.isdigit() else 11 if rank == 'A' else 10

def can_layoff(card: Dict, meld: List[Dict]) -> bool:
    """Check if a card can be laid off on a meld."""
    return check_valid_meld(meld + [card])

def check_valid_meld(meld: List[Dict]) -> bool:
    """Check if a set of cards forms a valid meld."""
    ranks = [card['rank'] for card in meld]
    suits = [card['suit'] for card in meld]
    ranks = ['T' if rank == '10' else rank for rank in ranks]
    return all(rank == ranks[0] for rank in ranks) or is_consecutive(ranks, suits)

def is_consecutive(ranks: List[str], suits: List[str]) -> bool:
    """Check if ranks are consecutive."""
    sorted_ranks = sorted(ranks, key=lambda rank: "23456789TJQKA".index(rank))
    return all("23456789TJQKA".index(sorted_ranks[i + 1]) - "23456789TJQKA".index(sorted_ranks[i]) == 1 for i in range(len(sorted_ranks) - 1)) and all(suit == suits[0] for suit in suits)

def check_end_conditions(game_state: Dict, logger) -> None:
    """Check if the game has ended."""
    if not game_state.players[game_state.common.current_player].facedown_cards.hand:
        game_state.common.is_over = True
        game_state.common.winner = game_state.common.current_player
        logger.info(f"Player {game_state.common.current_player} wins the game!")

    if len(game_state.common.facedown_cards.stock) < 2:
        refill_stock_from_discard(game_state, logger)

def refill_stock_from_discard(game_state: Dict, logger) -> None:
    """Refill stock from the discard pile if needed."""
    if len(game_state.common.faceup_cards.discard_pile) > 1:
        game_state.common.facedown_cards.stock.extend(reversed(game_state.common.faceup_cards.discard_pile[:-1]))
        game_state.common.faceup_cards.discard_pile = game_state.common.faceup_cards.discard_pile[-1:]
        logger.info("Stock refilled from discard pile.")
    else:
        game_state.common.is_over = True
        logger.info("Game ends in a draw as there are no cards to draw.")
"""End of the game code"""
