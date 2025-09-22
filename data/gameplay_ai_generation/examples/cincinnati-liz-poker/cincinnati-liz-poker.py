
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

# Hand rank ordering (higher is better)
# We allow Five of a Kind with a single wild (joker).
HAND_RANKS = {
    'HIGH_CARD': 1,
    'ONE_PAIR': 2,
    'TWO_PAIR': 3,
    'THREE_OF_A_KIND': 4,
    'STRAIGHT': 5,
    'FLUSH': 6,
    'FULL_HOUSE': 7,
    'FOUR_OF_A_KIND': 8,
    'STRAIGHT_FLUSH': 9,
    'FIVE_OF_A_KIND': 10,
}

RANK_ORDER = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
              '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
ORDER_TO_RANK = {v: k for k, v in RANK_ORDER.items()}
SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
ALL_52 = [(r, s) for s in SUITS for r in RANK_ORDER.keys()]

def _card_tuple(c):
    # Returns (rank_str, suit_str)
    return (c.field['rank'], c.field['suit'])

def _is_same_card(a, b):
    return a.field['rank'] == b.field['rank'] and a.field['suit'] == b.field['suit']

def _is_straight(rank_values):
    """Given a sorted descending list of unique rank ints, determine straight and top card."""
    # Handle wheel straight (A-2-3-4-5)
    unique = sorted(set(rank_values))
    if len(unique) < 5:
        return False, None
    # convert A to 1 for wheel check
    if 14 in unique:
        unique_with_wheel = sorted(set([1 if v == 14 else v for v in unique]))
    else:
        unique_with_wheel = unique

    def longest_run(vals):
        run = 1
        best = (1, vals[0])
        for i in range(1, len(vals)):
            if vals[i] == vals[i-1] + 1:
                run += 1
                best = max(best, (run, vals[i]), key=lambda x: (x[0], x[1]))
            elif vals[i] != vals[i-1]:
                run = 1
        return best  # (length, top_value)

    l1, top1 = longest_run(unique)
    l2, top2 = longest_run(unique_with_wheel)
    if max(l1, l2) >= 5:
        # choose the better top
        if l1 >= 5:
            best_top = top1
        else:
            best_top = 5 if top2 == 5 else top2
        # map 1 back to 14 if needed
        if best_top == 5 and 1 in unique_with_wheel:
            # wheel straight; top is 5 (A counts low)
            return True, 5
        return True, best_top
    return False, None

def _hand_rank_and_kickers(cards5):
    """Evaluate an exact 5-card hand (no wilds here). Return (rank_value, kickers_list_high_to_low)."""
    ranks = [r for r, _ in cards5]
    suits = [s for _, s in cards5]
    rank_vals = sorted([RANK_ORDER[r] for r in ranks], reverse=True)

    # Counts by rank value for tie-breaking
    counts = {}
    for v in rank_vals:
        counts[v] = counts.get(v, 0) + 1
    # Sort ranks by (count desc, rank desc) for consistent kickers order
    by_count_then_rank = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    count_values = sorted(counts.values(), reverse=True)

    is_flush = len(set(suits)) == 1
    # Straight checking using unique ranks
    is_straight, straight_top = _is_straight(rank_vals)

    if is_straight and is_flush:
        return (HAND_RANKS['STRAIGHT_FLUSH'], [straight_top])

    if count_values == [4, 1]:
        # Four of a Kind: (quad_rank, kicker)
        quad_rank = by_count_then_rank[0][0]
        kicker = [v for v in rank_vals if v != quad_rank][0]
        return (HAND_RANKS['FOUR_OF_A_KIND'], [quad_rank, kicker])

    if count_values == [3, 2]:
        # Full House: (trip_rank, pair_rank)
        trip_rank = by_count_then_rank[0][0]
        pair_rank = by_count_then_rank[1][0]
        return (HAND_RANKS['FULL_HOUSE'], [trip_rank, pair_rank])

    if is_flush:
        return (HAND_RANKS['FLUSH'], rank_vals)

    if is_straight:
        return (HAND_RANKS['STRAIGHT'], [straight_top])

    if count_values == [3, 1, 1]:
        # Trips: (trip_rank, kickers...)
        trip_rank = by_count_then_rank[0][0]
        kickers = [v for v in rank_vals if v != trip_rank]
        return (HAND_RANKS['THREE_OF_A_KIND'], [trip_rank] + kickers)

    if count_values == [2, 2, 1]:
        # Two Pair: (higher_pair, lower_pair, kicker)
        pair_ranks = [rc for rc, cnt in by_count_then_rank if cnt == 2]
        kicker = [rc for rc, cnt in by_count_then_rank if cnt == 1][0]
        pair_ranks.sort(reverse=True)
        return (HAND_RANKS['TWO_PAIR'], pair_ranks + [kicker])

    if count_values == [2, 1, 1, 1]:
        pair_rank = [rc for rc, cnt in by_count_then_rank if cnt == 2][0]
        kickers = [rc for rc, cnt in by_count_then_rank if cnt == 1]
        kickers.sort(reverse=True)
        return (HAND_RANKS['ONE_PAIR'], [pair_rank] + kickers)

    return (HAND_RANKS['HIGH_CARD'], rank_vals)

def _best_with_optional_wild(cards5, has_wild):
    """Return best (rank_value, kickers) for a 5-card set that may contain a single wild placeholder."""
    if not has_wild:
        return _hand_rank_and_kickers(cards5)

    # Replace the one wild with any card not already in cards5
    used = set(cards5)
    best = (0, [])
    for r, s in ALL_52:
        if (r, s) in used:
            continue
        candidate = [(r, s) if c == ('*WILD*', '*WILD*') else c for c in cards5]
        score = _hand_rank_and_kickers(candidate)

        # Detect FIVE OF A KIND: if rank counts become [5]
        rank_vals = [RANK_ORDER[x[0]] for x in candidate]
        cts = {}
        for v in rank_vals:
            cts[v] = cts.get(v, 0) + 1
        if 5 in cts.values():
            score = (HAND_RANKS['FIVE_OF_A_KIND'], [max([k for k, v in cts.items() if v == 5])])

        if score > best:
            best = score
    return best

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


def evaluate_hand(cards: List[LLMCard], wild_card: Optional[LLMCard]) -> tuple:
    """
    Evaluate the BEST 5-card poker hand from 'cards' (>=5 cards).
    Supports a single wild card (the specific revealed card at wild_card_index) that can become any rank/suit.
    Returns (rank_value:int, tiebreakers:list[int]) where higher tuple compares greater.
    """
    # Prepare tuples and find if the specific wild card instance is present
    tuples = [_card_tuple(c) for c in cards]
    has_specific_wild = False
    if wild_card is not None:
        # Only the exact wild card instance counts as wild (not "all cards of that rank")
        # Since players take from a single deck, identity match works; fallback by value if objects compare by value only.
        for i, c in enumerate(cards):
            if _is_same_card(c, wild_card):
                has_specific_wild = True
                break

    best = (HAND_RANKS['HIGH_CARD'], [0, 0, 0, 0, 0])

    # Iterate over all 5-card combinations from available cards
    for combo_idxs in combinations(range(len(tuples)), 5):
        subset = [tuples[i] for i in combo_idxs]
        # mark wild position with sentinel if this exact card is included
        has_wild_here = False
        if has_specific_wild:
            # find which tuple corresponds to the wild card; compare by rank+suit
            wild_tuple = _card_tuple(wild_card)
            if wild_tuple in subset:
                # replace the first occurrence with a sentinel
                idx = subset.index(wild_tuple)
                subset[idx] = ('*WILD*', '*WILD*')
                has_wild_here = True

        score = _best_with_optional_wild(subset, has_wild_here)
        if score > best:
            best = score

    return best


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
    """Return the payoffs for each player using proper hand comparisons and tiebreakers."""
    num_players = game_state.common['num_players']
    payoffs = [0] * num_players
    active_players = [i for i in range(num_players) if not game_state.players[i].public['folded']]

    # Early winner by folds
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

    # Compute rich scores (rank, tiebreakers)
    hand_scores = {}
    for i in active_players:
        player_hand = game_state.players[i].private['hand']
        total_cards = player_hand + community_cards
        score = evaluate_hand(total_cards, wild_card)  # returns (rank_value, kickers)
        hand_scores[i] = score
        logger.info(f"Player {i} hand score: {score}")

    # Determine winners by full tuple comparison
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