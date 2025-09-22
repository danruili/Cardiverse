
"""Beginning of the game code"""
game_name = 'WildCardPoker'
recommended_num_players = 5
num_players_range = [2, 3, 4, 5, 6, 7, 8]


def initiation(num_players: int, logger) -> DotDict:
    """Initialize the game state for WildCardPoker."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'current_bet': 0,
            'pot': 0,
            'is_over': False,
            'winner': None,
            'last_raiser': None,
            'community_cards': {
                'face_down': [],
                'face_up': [],
                'wild_card_index': 2,
                'wild_card': None,
            },
            'folded_players': set(),
            'revealed_cards_count': 0,
            'deck': [],
        },
        'players': [
            DotDict({
                'public': {
                    'bet': 0,
                    'folded': False,
                },
                'private': {
                    'hand': [],
                },
                'faceup_cards': {
                    'selected_hand': [],
                },
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return game_state


def init_deck(game_state: DotDict, logger: EnvLogger) -> DotDict:
    """Initialize a standard 52-card deck and shuffle."""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state.common['deck'] = deck
    logger.info("Deck initialized and shuffled.")
    return game_state


def init_deal(game_state: DotDict, logger: EnvLogger) -> DotDict:
    """Deal cards to players and set up community cards."""
    logger.info("Dealing cards to players and community...")
    deck = game_state.common['deck']
    num_players = game_state.common['num_players']
    for i in range(num_players):
        hand = [deck.pop() for _ in range(5)]
        game_state.players[i].private['hand'] = hand
        logger.info(f"Player {i} has been dealt 5 cards.")
    community_cards = [deck.pop() for _ in range(5)]
    game_state.common.community_cards['face_down'] = community_cards
    logger.info("Community cards have been dealt face down.")
    return game_state


def proceed_round(action: dict, game_state: DotDict, logger: EnvLogger) -> DotDict:
    """Process the action and update the game state."""
    current_player = game_state.common['current_player']
    player = game_state.players[current_player]
    logger.info(f"Player {current_player} action: {action}")

    if player.public['folded']:
        logger.info(f"Player {current_player} has already folded.")
        game_state.common['current_player'] = (current_player + 1) % game_state.common['num_players']
        return game_state

    action_type = action['action']
    current_bet = game_state.common['current_bet']
    player_bet = player.public['bet']

    if action_type == 'fold':
        player.public['folded'] = True
        game_state.common.folded_players.add(current_player)
        logger.info(f"Player {current_player} folds.")
    elif action_type == 'check':
        if player_bet == current_bet:
            logger.info(f"Player {current_player} checks.")
        else:
            logger.info(f"Player {current_player} cannot check, must call or raise.")
    elif action_type == 'call':
        call_amount = current_bet - player_bet
        player.public['bet'] += call_amount
        game_state.common['pot'] += call_amount
        logger.info(f"Player {current_player} calls.")
    elif action_type == 'bet':
        amount = action['args']['amount']
        game_state.common['current_bet'] = amount
        player.public['bet'] += amount
        game_state.common['pot'] += amount
        game_state.common['last_raiser'] = current_player
        logger.info(f"Player {current_player} bets {amount}.")
    elif action_type == 'raise':
        amount = action['args']['amount']
        additional_bet = amount - player_bet
        game_state.common['current_bet'] = amount
        player.public['bet'] += additional_bet
        game_state.common['pot'] += additional_bet
        game_state.common['last_raiser'] = current_player
        logger.info(f"Player {current_player} raises to {amount}.")
    else:
        logger.info(f"Invalid action by Player {current_player}.")

    # Determine if only one player is left standing
    active_players = [i for i in range(game_state.common['num_players']) if not game_state.players[i].public['folded']]
    if len(active_players) == 1:
        game_state.common['is_over'] = True
        game_state.common['winner'] = active_players[0]
        logger.info(f"Player {active_players[0]} wins by default as all others have folded.")
        return game_state

    # Move to the next active player
    next_player = (current_player + 1) % game_state.common['num_players']
    while game_state.players[next_player].public['folded']:
        next_player = (next_player + 1) % game_state.common['num_players']
    game_state.common['current_player'] = next_player

    # Determine if the betting round is over
    if game_state.common['last_raiser'] is None:
        betting_round_over = all(
            game_state.players[i].public['bet'] == game_state.common['current_bet'] or game_state.players[i].public['folded']
            for i in range(game_state.common['num_players'])
        )
    elif next_player == game_state.common['last_raiser']:
        betting_round_over = all(
            game_state.players[i].public['bet'] == game_state.common['current_bet'] or game_state.players[i].public['folded']
            for i in range(game_state.common['num_players'])
        )
    else:
        betting_round_over = False

    # Reveal community cards if a betting round is over
    if betting_round_over:
        logger.info("Betting round is over.")
        for i in range(game_state.common['num_players']):
            game_state.players[i].public['bet'] = 0
        game_state.common['current_bet'] = 0
        game_state.common['last_raiser'] = None

        if game_state.common['revealed_cards_count'] < 5:
            card = game_state.common.community_cards['face_down'][game_state.common['revealed_cards_count']]
            game_state.common.community_cards['face_up'].append(card)
            game_state.common['revealed_cards_count'] += 1
            logger.info(f"Community card revealed: {card}")
            if game_state.common['revealed_cards_count'] == 3:
                game_state.common.community_cards['wild_card'] = card
                logger.info(f"The wild card is {card}")
        else:
            logger.info("All community cards have been revealed. Proceeding to showdown.")
            game_state.common['is_over'] = True

    return game_state


def evaluate_hand(cards: List[LLMCard], wild_card: Optional[LLMCard]) -> int:
    """Evaluate the poker hand and return a score."""
    ranks = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
             '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    rank_counts = {rank: 0 for rank in ranks}
    suit_counts = {suit: 0 for suit in suits}

    for card in cards:
        rank_counts[card.field['rank']] += 1
        suit_counts[card.field['suit']] += 1

    wild_value = ranks[wild_card.field['rank']] if wild_card else None
    max_count = max(rank_counts.values())

    # Simplified placeholder for evaluating hand ranks
    if max_count == 5:
        return 9  # Five of a Kind
    elif 5 in suit_counts.values():
        return 8  # Straight Flush
    elif 4 in rank_counts.values():
        return 7  # Four of a Kind
    elif 3 in rank_counts.values() and 2 in rank_counts.values():
        return 6  # Full House
    elif 5 in suit_counts.values():
        return 5  # Flush
    elif 3 in rank_counts.values():
        return 4  # Three of a Kind
    elif list(rank_counts.values()).count(2) == 2:
        return 3  # Two Pair
    elif 2 in rank_counts.values():
        return 2  # One Pair
    else:
        return 1  # High Card


def get_legal_actions(game_state: Dict) -> List[dict]:
    """Get all legal actions for the current player."""
    current_player = game_state['common']['current_player']
    player = game_state['players'][current_player]
    legal_actions = []

    if player.public['folded']:
        return legal_actions

    current_bet = game_state['common']['current_bet']
    player_bet = player.public['bet']

    if current_bet == 0:
        legal_actions.append({'action': 'check'})
        for amount in range(1, 4):
            legal_actions.append({'action': 'bet', 'args': {'amount': amount}})
    else:
        if player_bet < current_bet:
            legal_actions.append({'action': 'call'})
            for raise_amount in range(current_bet + 1, current_bet + 4):
                legal_actions.append({'action': 'raise', 'args': {'amount': raise_amount}})
            legal_actions.append({'action': 'fold'})
        else:
            legal_actions.append({'action': 'check'})
            for raise_amount in range(current_bet + 1, current_bet + 4):
                legal_actions.append({'action': 'raise', 'args': {'amount': raise_amount}})
            legal_actions.append({'action': 'fold'})

    return legal_actions


def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """Return the payoffs for each player."""
    num_players = game_state.common['num_players']
    payoffs = [0] * num_players
    active_players = [i for i in range(num_players) if not game_state.players[i].public['folded']]

    if game_state.common['winner'] is not None:
        winner = game_state.common['winner']
        if isinstance(winner, int):
            payoffs[winner] = game_state.common['pot']
            logger.info(f"Player {winner} wins the pot of {game_state.common['pot']}.")
        else:
            split_pot = game_state.common['pot'] / len(winner)
            for w in winner:
                payoffs[w] = split_pot
            logger.info(f"Players {winner} split the pot of {game_state.common['pot']}.")
        return payoffs

    community_cards = game_state.common.community_cards['face_up']
    wild_card = game_state.common.community_cards.get('wild_card', None)

    hand_scores = {}
    for i in active_players:
        player_hand = game_state.players[i].private['hand']
        total_cards = player_hand + community_cards
        score = evaluate_hand(total_cards, wild_card)
        hand_scores[i] = score
        logger.info(f"Player {i} hand score: {score}")

    best_score = max(hand_scores.values())
    winners = [i for i, score in hand_scores.items() if score == best_score]

    if len(winners) == 1:
        payoffs[winners[0]] = game_state.common['pot']
        logger.info(f"Player {winners[0]} wins the pot of {game_state.common['pot']}.")
    else:
        split_pot = game_state.common['pot'] / len(winners)
        for w in winners:
            payoffs[w] = split_pot
        logger.info(f"Players {winners} split the pot of {game_state.common['pot']}.")

    return payoffs
"""End of the game code"""