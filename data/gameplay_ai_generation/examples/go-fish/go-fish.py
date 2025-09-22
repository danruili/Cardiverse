
"""Beginning of the game code"""
game_name = 'GoFish'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5]

def initiation(num_players: int, logger) -> DotDict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'winner': None,
            'is_over': False,
            'books': [0] * num_players,
            'facedown_cards': {
                'stock': init_deck()
            },
        },
        'players': [
            DotDict({
                'public': {},
                'facedown_cards': {
                    'hand': [],
                },
                'faceup_cards': {
                    'books': [],
                }
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
    for rank in ranks:
        for _ in range(4):  # Four cards of each rank
            deck.append(LLMCard({'rank': rank}))
    random.shuffle(deck)
    return deck

def init_dealing(game_state: Dict, logger) -> Dict:
    """Deal the initial cards to each player."""
    num_cards = 7 if game_state.common.num_players <= 3 else 5
    for player in game_state.players:
        player.facedown_cards.hand = [game_state.common.facedown_cards.stock.pop() for _ in range(num_cards)]
    logger.info(f"Initial cards dealt. Stock size: {len(game_state.common.facedown_cards.stock)}")
    return game_state  # Return the updated game state

def proceed_round(action: dict, game_state: Dict, logger) -> DotDict:
    """Process the action and update the game state."""
    current_player = game_state.common.current_player
    logger.info(f"Player {current_player} takes an action: {action}")
    
    if action['action'] == 'request':
        if process_request(action, game_state, logger):
            return game_state  # Successful request allows player to continue.
    elif action['action'] == 'draw':
        if game_state.common.facedown_cards.stock:
            card = game_state.common.facedown_cards.stock.pop()
            game_state.players[current_player].facedown_cards.hand.append(card)
            logger.info(f"Player {current_player} draws a card.")
        else:
            logger.info("Stock pile is empty, no card to draw.")

    check_for_books(game_state.players[current_player], game_state, logger)
    
    # Check if the game is over
    if is_game_over(game_state, logger):
        return game_state
    
    game_state.common.current_player = next_player(game_state, logger)
    return game_state  # Return the updated game state

def get_legal_actions(game_state: Dict, player_id: Optional[int] = None) -> List[Dict]:
    """Get all legal actions for the current player or specified player."""
    legal_actions = []
    player_id = game_state.common.current_player if player_id is None else player_id
    player = game_state.players[player_id]

    # If the game is over, no actions are legal
    if game_state.common.is_over:
        return legal_actions

    # Legal action: request cards of a specific rank from another player
    player_hand_ranks = set(card.rank for card in player.facedown_cards.hand)
    # Check if the player has a completed book that must be revealed
    rank_count = {}
    for card in player.facedown_cards.hand:
        rank_count[card.rank] = rank_count.get(card.rank, 0) + 1
    for rank, count in rank_count.items():
        if count == 4:
            legal_actions.append({'action': 'reveal', 'args': {'rank': rank}})
            return legal_actions

    # Legal action: request cards of a specific rank from another player only if they have cards
    for opponent_id, opponent in enumerate(game_state.players):
        if opponent_id != player_id and opponent.facedown_cards.hand:  # Only request from players with cards
            for rank in player_hand_ranks:
                legal_actions.append({'action': 'request', 'args': {'target_player': opponent_id, 'rank': rank}})

    # Legal action: draw a card if stock is available
    if game_state.common.facedown_cards.stock:
        legal_actions.append({'action': 'draw'})

    # Allow action to reveal a completed book if the player has it
    rank_count = {}
    for card in player.facedown_cards.hand:
        rank_count[card.rank] = rank_count.get(card.rank, 0) + 1
    for rank, count in rank_count.items():
        if count == 4:
            legal_actions.append({'action': 'reveal', 'args': {'rank': rank}})
    
    unique_legal_actions = []
    seen = set()
    for action in legal_actions:
        action_tuple = tuple(sorted((k, tuple(v.items()) if isinstance(v, dict) else v) for k, v in action.items()))
        if action_tuple not in seen:
            unique_legal_actions.append(action)
            seen.add(action_tuple)
    return unique_legal_actions

def process_request(action: Dict, game_state: DotDict, logger) -> bool:
    """Process a card request action."""
    current_player = game_state.common.current_player
    target_player = action['args']['target_player']
    rank = action['args']['rank']
    
    if logger:
        logger.info(f"Player {current_player} requests rank {rank} from Player {target_player}.")
    
    target_hand = game_state.players[target_player].facedown_cards.hand
    requested_cards = [card for card in target_hand if card.rank == rank]
    
    if requested_cards:
        logger.info(f"Player {target_player} gives {len(requested_cards)} card(s) to Player {current_player}.")
        game_state.players[target_player].facedown_cards.hand = [card for card in target_hand if card.rank != rank]
        game_state.players[current_player].facedown_cards.hand.extend(requested_cards)
        return True  # Successful request allows player to continue.
    else:
        logger.info(f"Player {target_player} says 'Go Fish!'.")
        if game_state.common.facedown_cards.stock:
            card = game_state.common.facedown_cards.stock.pop()
            game_state.players[current_player].facedown_cards.hand.append(card)
            logger.info(f"Player {current_player} draws {card.rank} from stock.")
        return False  # Unsuccessful request passes the turn.

def check_for_books(player: DotDict, game_state: DotDict, logger) -> None:
    """Check and reveal completed books in a player's hand."""
    hand = player.facedown_cards.hand
    rank_count = {}
    for card in hand:
        rank_count[card.rank] = rank_count.get(card.rank, 0) + 1
    for rank, count in rank_count.items():
        if count == 4:
            logger.info(f"Player completes a book of {rank}s.")
            player.facedown_cards.hand = [card for card in hand if card.rank != rank]
            current_player = game_state.common.current_player
            if rank not in player.faceup_cards.books:
                player.faceup_cards.books.append(rank)
                game_state.common.books[current_player] += 1

def next_player(game_state: DotDict, logger) -> int:
    """Determine the next player."""
    current_player = game_state.common.current_player
    num_players = game_state.common.num_players
    while True:
        current_player = (current_player + 1) % num_players
        if game_state.players[current_player].facedown_cards.hand or game_state.common.facedown_cards.stock:
            logger.info(f"Next player is Player {current_player}.")
            return current_player

def is_game_over(game_state: DotDict, logger) -> bool:
    """Determine if the game is over and set the winner if so."""
    if sum(game_state.common.books) == (52 // 4) or all(not player.facedown_cards.hand for player in game_state.players):
        game_state.common.is_over = True
        logger.info("The game has ended.")
        determine_winner(game_state, logger)
        return True
    return False

def determine_winner(game_state: DotDict, logger):
    """Declare the winner based on the number of books completed."""
    max_books = max(game_state.common.books)
    winners = [i for i, books in enumerate(game_state.common.books) if books == max_books]
    if len(winners) == 1:
        game_state.common.winner = winners[0]
        logger.info(f"Player {game_state.common.winner} is the winner with {max_books} books!")
    else:
        game_state.common.winner = winners
        logger.info(f"It's a tie among players {winners} with {max_books} books each!")

def get_payoffs(game_state: Dict, logger) -> List[Union[int, float]]:
    """Get the payoffs for each player."""
    payoffs = []
    max_books = max(game_state.common.books)
    num_tied_players = game_state.common.books.count(max_books)
    # Adjust payoff for ties: all players with max_books get equal points
    for i, books in enumerate(game_state.common.books):
        payoffs.append(1 / num_tied_players if books == max_books else 0)
    logger.info(f"Payoffs for each player: {payoffs}")
    return payoffs
"""End of the game code"""