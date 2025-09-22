
"""Beginning of the game code"""
game_name = 'Fusion Rummy'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5, 6]

def initiation(num_players: int, logger) -> DotDict:
    """
    Initialize the game state for Fusion Rummy.
    """
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'pot': 0,
            'communal_pool': [],
            'sequence_info': {
                'current_suit': None,
                'current_sequence': []
            },
            'facedown_cards': {
                'stock': [],
            },
            'is_over': False,
            'winner': None,
        },
        'players': [
            DotDict({
                'public': {
                    'fusion_cards': [],
                    'chips_in_front': 0,
                },
                'private': {
                    'player_hand': [],
                    'special_abilities': [],
                },
            }) for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return game_state

def init_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    """Initialize and shuffle the deck."""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state.common.facedown_cards.stock = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    """Deal cards to players one at a time."""
    num_players = game_state.common.num_players
    deck = game_state.common.facedown_cards.stock
    min_cards = len(deck) // num_players
    extra_cards = len(deck) % num_players
    logger.info("Dealing cards one at a time starting from the player to the left of the dealer until all cards are allocated.")
    for _ in range(min_cards):
        for player in game_state.players:
            player.private.player_hand.append(deck.pop())
    for i in range(len(game_state.players)):
        if len(game_state.players[i].private.player_hand) < min_cards + (1 if i < extra_cards else 0):
            player = game_state.players[i]
            player.public.chips_in_front += 1
            game_state.common.pot += 1
            logger.info(f"Player {i} anteed an additional chip due to fewer cards.")
    for player in game_state.players:
        if len(player.private.player_hand) < min_cards + (1 if extra_cards > 0 else 0):
            player.public.chips_in_front += 1
            game_state.common.pot += 1
            logger.info("Player anteed an additional chip due to fewer cards.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Process the player's action and update the game state.
    """
    current_player = game_state.common.current_player
    player = game_state.players[current_player]

    logger.info(f"Player {current_player}'s action: {action['action']}.")

    if action['action'] == 'play_card':
        card = action['args']['card']
        if can_play_card(card, game_state):
            player.private.player_hand.remove(card)
            game_state.common.communal_pool.append(card)
            game_state.common.sequence_info['current_suit'] = card.suit
            game_state.common.sequence_info['current_sequence'].append(card.rank)
            logger.info(f"Player {current_player} plays {card}.")
            check_sequence_end(game_state, logger, player)
        else:
            logger.info("Invalid card played.")
    
    elif action['action'] == 'place_counter':
        player.public.chips_in_front += 1
        game_state.common.pot += 1
        logger.info(f"Player {current_player} places a counter into the pot.")
    
    elif action['action'] == 'create_fusion_card':
        cards = action['args']['cards']
        if can_create_fusion(cards, player):
            for card in cards:
                player.private.player_hand.remove(card)
            player.public.fusion_cards.append(cards)
            logger.info(f"Player {current_player} creates a fusion card: {cards}.")
            if check_fusion_victory(player):
                game_state.common.is_over = True
                game_state.common.winner = current_player
                logger.info(f"Player {current_player} wins by creating three fusion cards!")
        else:
            logger.info("Invalid fusion creation.")
    
    elif action['action'] == 'use_ability':
        ability = action['args']['ability']
        if can_use_ability(player, ability):
            activate_ability(player, ability, game_state, logger)
            logger.info(f"Player {current_player} uses ability {ability}.")
        else:
            logger.info("Invalid ability usage.")
    
    # Move to next player
    if not game_state.common.is_over:
        if is_sequence_stuck(game_state):
            game_state.common.is_over = True
            logger.info("No further actions can be taken. Game ends due to a stuck sequence.")
            determine_winner_by_remaining_cards(game_state, logger)
        else:
            game_state.common.current_player = (current_player + 1) % game_state.common.num_players
    
    return game_state

def check_sequence_end(game_state: Dict, logger: EnvLogger, player: DotDict) -> None:
    """Check if a suit sequence has ended and handle it."""
    current_suit = game_state.common.sequence_info['current_suit']
    sequence_end = (len(game_state.common.sequence_info['current_sequence']) == 13)
    if sequence_end:
        logger.info(f"Sequence for {current_suit} is exhausted.")
        start_new_sequence(game_state, logger)

def start_new_sequence(game_state: Dict, logger: EnvLogger) -> None:
    """Start a new suit sequence if possible."""
    game_state.common.sequence_info['current_sequence'] = []
    if logger is not None:
        logger.info("Starting a new suit sequence.")
    remaining_suits = set(card.suit for card in game_state.common.facedown_cards.stock)
    if not remaining_suits.difference(set(game_state.common.sequence_info['current_suit'])):
        if logger is not None:
            logger.info("No more suits to continue. Game ends.")
        game_state.common.is_over = True
        determine_winner_by_remaining_cards(game_state, logger)

def determine_winner_by_remaining_cards(game_state: Dict, logger: EnvLogger) -> None:
    """Determine the winner based on the fewest remaining cards."""
    min_cards = min(len(player.private.player_hand) for player in game_state.players)
    winners = [i for i, player in enumerate(game_state.players) if len(player.private.player_hand) == min_cards]
    if len(winners) == 1:
        game_state.common.winner = winners[0]
        if logger is not None:
            logger.info(f"Player {winners[0]} wins by having the least remaining cards.")
    else:
        game_state.common.winner = winners
        if logger is not None:
            logger.info(f"Players {winners} tie by having the least remaining cards.")
    game_state.common.is_over = True

def can_play_card(card: LLMCard, game_state: Dict) -> bool:
    """Check if the card can be played adherent to sequential rules."""
    if not game_state.common.sequence_info['current_suit']:
        return True
    current_suit = game_state.common.sequence_info['current_suit']
    current_sequence = game_state.common.sequence_info['current_sequence']
    return card.suit == current_suit and get_rank_value(card.rank) == get_rank_value(current_sequence[-1]) + 1

def get_rank_value(rank: str) -> int:
    """Return numerical value of card rank."""
    rank_order = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10,
                 'J':11, 'Q':12, 'K':13, 'A':14}
    return rank_order.get(rank, 0)

def find_possible_fusions(hand: List[LLMCard]) -> List[List[LLMCard]]:
    """Determine all valid three-card fusions from hand."""
    fusions = []
    hand_sorted = sorted(hand, key=lambda x: (x.suit, get_rank_value(x.rank)))
    for i in range(len(hand_sorted)):
        for j in range(i+1, len(hand_sorted)):
            for k in range(j+1, len(hand_sorted)):
                cards = [hand_sorted[i], hand_sorted[j], hand_sorted[k]]
                ranks = sorted([get_rank_value(card.rank) for card in cards])
                suits = [card.suit for card in cards]
                if suits.count(suits[0]) == 3 and ranks[2] - ranks[0] == 2 and ranks[1] - ranks[0] == 1:
                    fusions.append(cards)
    return fusions

def can_create_fusion(cards: List[LLMCard], player: DotDict) -> bool:
    """Check if the cards can form a valid fusion sequence."""
    if len(cards) != 3:
        return False
    ranks = sorted([get_rank_value(card.rank) for card in cards])
    suits = [card.suit for card in cards]
    return suits.count(suits[0]) == 3 and ranks[2] - ranks[0] == 2 and ranks[1] - ranks[0] == 1

def check_fusion_victory(player: DotDict) -> bool:
    """Determine if the player has won by creating three fusion cards."""
    return len(player.public.fusion_cards) >= 3

def can_use_ability(player: DotDict, ability: str) -> bool:
    """Verify if player can activate a specific fusion ability."""
    return ability in player.private.special_abilities

def activate_ability(player: DotDict, ability: str, game_state: Dict, logger: EnvLogger) -> None:
    """Execute the specified fusion card ability."""
    logger.info(f"Activating ability: {ability}.")
    if ability == "skip_turn":
        skip_next_player(game_state, logger)
    elif ability == "extra_turn":
        give_extra_turn(game_state, logger)
    elif ability == "draw_from_stock" and game_state.common.facedown_cards.stock:
        draw_card_from_stock(player, game_state, logger)

def skip_next_player(game_state: Dict, logger: EnvLogger) -> None:
    """Skip the next player's turn."""
    next_player = (game_state.common.current_player + 1) % game_state.common.num_players
    logger.info(f"Player {next_player}'s turn is skipped.")
    game_state.common.current_player = (next_player + 1) % game_state.common.num_players

def give_extra_turn(game_state: Dict, logger: EnvLogger) -> None:
    """Give the current player an extra turn."""
    logger.info("Current player gets an extra turn.")

def draw_card_from_stock(player: DotDict, game_state: Dict, logger: EnvLogger) -> None:
    """Draw a card from stock."""
    if game_state.common.facedown_cards.stock:
        card = game_state.common.facedown_cards.stock.pop()
        player.private.player_hand.append(card)
        logger.info(f"Player draws a card from the stock: {card}")

def get_legal_actions(game_state: Dict, logger: Optional[EnvLogger] = None) -> list[dict]:
    """
    List legal actions for the current player.
    """
    current_player = game_state.common.current_player
    next_rank_value = None
    if game_state.common.sequence_info['current_sequence']:
        next_rank_value = get_rank_value(game_state.common.sequence_info['current_sequence'][-1]) + 1
    player = game_state.players[current_player]
    legal_actions = []
    
    # Include action: Play a card that continues the current sequence.
    for card in player.private.player_hand:
        if not game_state.common.sequence_info['current_suit'] or (
           card.suit == game_state.common.sequence_info['current_suit'] and 
           get_rank_value(card.rank) == next_rank_value):
            legal_actions.append({'action': 'play_card', 'args': {'card': card}})
    
    # Action: Place a counter if no cards can be played in the current sequence.
    if not any(
        card.suit == game_state.common.sequence_info['current_suit'] and 
        get_rank_value(card.rank) == next_rank_value for card in player.private.player_hand
    ):
        legal_actions.append({'action': 'place_counter'})
    
    # Action: Create a fusion card
    possible_fusions = find_possible_fusions(player.private.player_hand)
    for fusion in possible_fusions:
        legal_actions.append({'action': 'create_fusion_card', 'args': {'cards': fusion}})
    
    # Action: Use a fusion special ability
    for ability in player.private.special_abilities:
        legal_actions.append({'action': 'use_ability', 'args': {'ability': ability}})
    
    return legal_actions

def is_sequence_stuck(game_state: Dict) -> bool:
    """
    Determine if the current suit sequence is stuck, i.e., no player can play any card.
    """
    current_suit = game_state.common.sequence_info['current_suit']
    current_sequence = game_state.common.sequence_info['current_sequence']
    next_rank_value = get_rank_value(current_sequence[-1]) + 1 if current_sequence else None

    for player in game_state.players:
        for card in player.private.player_hand:
            if card.suit == current_suit and get_rank_value(card.rank) == next_rank_value:
                return False  # Sequence is not stuck because at least one card can be played
    return True

def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """Compute and return payoffs for each player."""
    payoffs = [0 for _ in range(game_state.common.num_players)]
    winner = game_state.common.winner
    if winner is not None:
        if isinstance(winner, int):
            payoffs[winner] = game_state.common.pot
            logger.info(f"Player {winner} wins the pot of {game_state.common.pot}.")
        else:
            shared_pot = game_state.common.pot / len(winner)
            for w in winner:
                payoffs[w] = shared_pot
                logger.info(f"Player {w} shares the pot, receiving {shared_pot}.")
    else:
        for i, player in enumerate(game_state.players):
            score = -len(player.private.player_hand)
            payoffs[i] = score
            logger.info(f"Player {i} ends with score: {score}.")
    return payoffs

def fusion_special_abilities(fusion: List[LLMCard]) -> List[str]:
    """Retrieve special abilities based on the fusion card."""
    return ["skip_turn", "extra_turn", "draw_from_stock"]
"""End of the game code"""