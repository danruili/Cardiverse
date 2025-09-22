

"""Beginning of the game code"""
game_name = 'Go Fish: Misdirection Edition'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5]

def initiation(num_players: int, logger) -> Dict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'is_over': False,
            'facedown_cards': {
                'stock': [],
            },
            'faceup_cards': {
                'books_collected': {player_id: [] for player_id in range(num_players)},
                'turn_actions': [],
            },
        },
        'players': [
            DotDict({
                'public': {
                    'revealed_books': [],
                },
                'private': {
                    'hand': [],
                },
            }) for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return DotDict(game_state)

def init_deck(game_state: Dict, logger) -> Dict:
    """Initialize the deck."""
    ranks = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
    deck = [LLMCard({'rank': rank, 'id': idx}) for idx, rank in enumerate(ranks * 4)]
    random.shuffle(deck)
    game_state.common.facedown_cards.stock = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: Dict, logger) -> Dict:
    """Deal the initial cards to each player."""
    num_players = game_state.common.num_players
    num_cards = 7 if num_players in [2, 3] else 5
    logger.info(f"Dealing {num_cards} cards to each of {num_players} players.")
    stock = game_state.common.facedown_cards.stock
    num_total_cards = 52
    cards_dealt = num_players * num_cards
    game_state.common.facedown_cards.stock = stock[:num_total_cards - cards_dealt]
    for player in game_state.players:
        player.private.hand = [stock.pop() for _ in range(num_cards)]
    return game_state

def proceed_round(action: dict, game_state: Dict, logger) -> Dict:
    """Process the action and update the game state."""
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    args = action['args']
    logger.info(f"Player {current_player} requests {args['rank']} from Player {args['target_player']}.")
    target_player_index = args['target_player']
    target_player = game_state.players[target_player_index]
    requested_rank = args['rank']
    target_hand = target_player.private.hand
    transferred_cards = [card for card in target_hand if card.rank == requested_rank]
    
    if transferred_cards:
        for card in transferred_cards:
            target_hand.remove(card)
            player.private.hand.append(card)
        logger.info(f"Player {target_player_index} gives {len(transferred_cards)} '{requested_rank}' card(s) to Player {current_player}.")
        game_state.common.faceup_cards.turn_actions.append({'requester': current_player, 'target': target_player_index, 'rank': requested_rank, 'result': 'success', 'count': len(transferred_cards)})
        check_and_reveal_books(player, game_state, logger)
    else:
        logger.info(f"Player {target_player_index} has no '{requested_rank}' card. Go Fish!")
        game_state.common.faceup_cards.turn_actions.append({'requester': current_player, 'target': target_player_index, 'rank': requested_rank, 'result': 'fail', 'count': 0})
        if game_state.common.facedown_cards.stock:
            drawn_card = game_state.common.facedown_cards.stock.pop()
            player.private.hand.append(drawn_card)
            logger.info(f"Player {current_player} draws a card from stock.")
            check_and_reveal_books(player, game_state, logger)
        else:
            logger.info("The stockpile is empty. No card drawn.")
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    check_game_over(game_state, logger)
    return game_state

def get_legal_actions(game_state: Dict) -> list[dict]:
    """Get all legal actions for the current player."""
    legal_actions = []
    current_player = game_state.common.current_player
    target_players = [pid for pid in range(game_state.common.num_players) if pid != current_player]
    all_ranks = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
    for target in target_players:
        for rank in all_ranks:
            legal_actions.append({'action': 'request', 'args': {'target_player': target, 'rank': rank}})
    assert legal_actions, "No legal actions available."
    return legal_actions

def get_payoffs(game_state: Dict, logger) -> List[Union[int, float]]:
    """Return the payoffs for each player."""
    books = {pid: len(game_state.common.faceup_cards.books_collected[pid]) for pid in range(game_state.common.num_players)}
    max_books = max(books.values())
    payoffs = []
    for pid, count in books.items():
        if count == max_books:
            payoffs.append(0)
            logger.info(f"Player {pid} has the highest number of books: {count}.")
        else:
            payoff = count - max_books
            payoffs.append(payoff)
            logger.info(f"Player {pid} has {count} books.")
    return payoffs

def check_and_reveal_books(player: DotDict, game_state: Dict, logger: EnvLogger) -> None:
    """Check if the player has any books and reveal them."""
    player_id = game_state.common.current_player
    rank_counts = {}
    for card in player.private.hand:
        rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1
    for rank, count in rank_counts.items():
        if count == 4:
            if rank not in game_state.common.faceup_cards.books_collected[player_id]:
                game_state.common.faceup_cards.books_collected[player_id].append(rank)
                player.public.revealed_books.append(rank)
                player.private.hand = [card for card in player.private.hand if card.rank != rank]
                logger.info(f"Player {player_id} has collected a book of '{rank}'s.")

def check_game_over(game_state: Dict, logger: EnvLogger) -> None:
    """Check if the game is over."""
    total_books = sum(len(books) for books in game_state.common.faceup_cards.books_collected.values())
    if total_books == 13:
        game_state.common.is_over = True
        logger.info("All books have been collected. The game is over.")
    elif not game_state.common.facedown_cards.stock:
        for player_id in range(game_state.common.num_players):
            check_and_reveal_books(game_state.players[player_id], game_state, logger)
        game_state.common.is_over = True
        logger.info("Stockpile exhausted, game ends.")
        determine_winner(game_state, logger)

def determine_winner(game_state: Dict, logger: EnvLogger) -> None:
    """Determine the winner."""
    books = {pid: len(game_state.common.faceup_cards.books_collected[pid]) for pid in range(game_state.common.num_players)}
    max_books = max(books.values())
    winners = [pid for pid, count in books.items() if count == max_books]
    logger.info(f"Player(s) {' and '.join(map(str, winners))} win(s) with {max_books} books collected.")
"""End of the game code"""