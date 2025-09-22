
"""Beginning of the game code"""
game_name = 'Fan Tan'
recommended_num_players: int = 4
num_players_range: List[int] = [3, 4, 5, 6]

def initiation(num_players, logger) -> DotDict:
    """
    Initialize the game state.
    """
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'pot': 0,
            'played_cards': {
                'hearts': [],
                'diamonds': [],
                'clubs': [],
                'spades': []
            },
            'is_over': False,
            'winner': None,
            'facedown_cards': {
                'deck': []
            }
        },
        'players': [
            DotDict({
                'public': {
                    'num_cards': 0,
                    'score': 0,
                    'chips_contributed': 0
                },
                'private': {},
                'facedown_cards': {
                    'hand': []
                }
            }) for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return game_state

def init_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Initialize the deck.
    """
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state['common']['facedown_cards']['deck'] = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Deal cards to players and collect antes.
    """
    logger.info("Dealing cards to players...")
    num_players = game_state['common']['num_players']
    deck = game_state['common']['facedown_cards']['deck']
    player_hands = [[] for _ in range(num_players)]
    player_index = 0
    while deck:
        card = deck.pop()
        player_hands[player_index].append(card)
        player_index = (player_index + 1) % num_players
    max_cards = max(len(hand) for hand in player_hands)
    for i in range(num_players):
        hand = player_hands[i]
        game_state['players'][i]['facedown_cards']['hand'] = hand
        game_state['players'][i]['public']['num_cards'] = len(hand)
        ante = 1
        if len(hand) < max_cards:
            ante += 1
        game_state['players'][i]['public']['chips_contributed'] = ante
        game_state['common']['pot'] += ante
        logger.info(f"Player {i} antes {ante} chips, holding {len(hand)} cards.")
    logger.info(f"Total pot after antes: {game_state['common']['pot']} chips.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Process the action, update the state, check if the game is over.
    """
    current_player = game_state['common']['current_player']
    player = game_state['players'][current_player]
    hand = player['facedown_cards']['hand']
    pot = game_state['common']['pot']
    action_type = action['action']
    
    logger.info(f"Player {current_player}'s turn with action: {action_type}")
    
    if action_type == 'play':
        card_index = action['args']['card_index']
        card = hand.pop(card_index)
        suit = card['suit']
        game_state['common']['played_cards'][suit].append(card)
        game_state['common']['played_cards'][suit].sort(key=lambda c: rank_value_dict()[c['rank']])
        logger.info(f"Player {current_player} plays {card['rank']} of {card['suit']}.")

        player['public']['num_cards'] = len(hand)
        logger.info(f"Player {current_player} now has {len(hand)} cards.")

        if len(hand) == 0:
            game_state['common']['is_over'] = True
            game_state['common']['winner'] = current_player
            logger.info(f"Player {current_player} has run out of cards and wins the game!")
    elif action_type == 'pass':
        pot += 1
        player['public']['chips_contributed'] += 1
        logger.info(f"Player {current_player} passes and adds one chip to the pot.")
        
        if any(is_playable(c, game_state) for c in hand):
            pot += 3
            player['public']['chips_contributed'] += 3
            logger.info(f"Player {current_player} had playable cards but passed, pays 3 chip penalty.")
            if any(c['rank'] == '7' for c in hand):
                pot += 5
                player['public']['chips_contributed'] += 5
                logger.info(f"Player {current_player} had a seven but passed, pays 5 more chips penalty.")
    else:
        logger.error(f"Unrecognized action: {action_type}")
    
    game_state['common']['pot'] = pot
    game_state['common']['current_player'] = (current_player + 1) % game_state['common']['num_players']
    if game_state['common']['is_over']:
        logger.info(f"Game over. Winner is Player {game_state['common']['winner']}.")
    
    return game_state

def get_legal_actions(game_state: Dict) -> list[dict]:
    """
    Get all legal actions for the current player.
    """
    current_player = game_state['common']['current_player']
    player = game_state['players'][current_player]
    hand = player['facedown_cards']['hand']
    legal_actions = []
    for idx, card in enumerate(hand):
        if is_playable(card, game_state):
            legal_actions.append({'action': 'play', 'args': {'card_index': idx}})
    if not legal_actions:
        legal_actions.append({'action': 'pass'})
    return legal_actions

def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """Return the payoffs for each player."""
    num_players = game_state['common']['num_players']
    payoffs = [0] * num_players
    pot = game_state['common']['pot']
    winner = game_state['common']['winner']
    
    if winner is not None:
        logger.info(f"Determining payoffs, pot is {pot} chips.")
        for i in range(num_players):
            contributions = game_state['players'][i]['public']['chips_contributed']
            if i == winner:
                payoffs[i] = pot - contributions
                logger.info(f"Player {i} wins {payoffs[i]} from the pot.")
            else:
                payoffs[i] = -contributions
                logger.info(f"Player {i} lost {contributions} chips.")
    return payoffs

def is_playable(card: LLMCard, game_state: Dict) -> bool:
    """Check if the card can be legally played."""
    suit = card['suit']
    rank = card['rank']
    played_cards = game_state['common']['played_cards'][suit]
    rank_values = rank_value_dict()
    rank_value = rank_values[rank]
    
    if rank_value == 7:
        return True
    elif rank_value < 7:
        next_rank_value = rank_value + 1
    else:
        next_rank_value = rank_value - 1
    
    next_rank = rank_from_value(next_rank_value)
    return any(c['rank'] == next_rank for c in played_cards)

def rank_value_dict() -> Dict[str, int]:
    """Return a dictionary mapping card ranks to numerical values."""
    return {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
            '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13}

def rank_from_value(value: int) -> str:
    """Return the rank corresponding to a numerical value."""
    values = {1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
              8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K'}
    return values.get(value, None)
"""End of the game code"""