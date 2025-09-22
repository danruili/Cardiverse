
"""Beginning of the game code"""
game_name = 'DynamicAlliance'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5]

def initiation(num_players: int, logger) -> Dict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'central_pile': [],
            'turn_order': list(range(num_players)),
            'phase_tracker': 'Accumulation',
            'is_over': False,
            'winner': None,
            'facedown_cards': {
                'deck': init_deck(),
            },
            'faceup_cards': {
                'challenges': [],
                'alliances': [],
                'gem_collections': [],
            },
        },
        'players': [
            DotDict({
                'public': {
                    'declared_rank': None,
                    'exchanged_cards': [],
                    'gems': 0,
                    'bonuses': 0,
                },
                'private': {
                    'hand': [],
                    'suit_diversity': 0,
                    'chance_cards': [],
                    'exchange_used': False,
                },
                'faceup_cards': {
                    'collected_cards': [],
                },
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_deal(game_state, logger)
    return game_state

def init_deck() -> List[LLMCard]:
    """Initialize the deck with standard and chance cards."""
    deck = []
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    # Add standard cards
    for suit in suits:
        for rank in ranks:
            deck.append(LLMCard({'rank': rank, 'suit': suit, 'type': 'standard'}))
    # Add chance cards
    for _ in range(10):
        deck.append(LLMCard({'rank': None, 'suit': None, 'type': 'chance'}))
    random.shuffle(deck)
    return deck

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    """Deal cards to players until the deck is depleted."""
    logger.info("Dealing cards to players...")
    deck = game_state.common.facedown_cards.deck
    num_players = game_state.common.num_players
    while deck:
        for player in game_state.players:
            if deck:
                card = deck.pop()
                player.private.hand.append(card)
    for player in game_state.players:
        player.private.suit_diversity = len(set(card.suit for card in player.private.hand if card.suit))
    logger.info("Dealing complete.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    """Process the action and update the game state."""
    phase = game_state.common.phase_tracker
    current_player = game_state.common.current_player
    player = game_state.players[current_player]

    if phase == 'Accumulation':
        # Ensure phase transitions and legality of actions
        if len(player.private.hand) == 0 and len(game_state.common.central_pile) == 0:
            game_state.common.phase_tracker = 'ExchangeAlliances'
            logger.info("Transitioning to Exchange and Alliances phase.")
            return game_state
        if action['action'] == 'declare_and_place':
            rank = action['args']['rank']
            num_cards = action['args']['num_cards']
            if 1 <= num_cards <= 4 and len(player.private.hand) >= num_cards:
                placed_cards = []
                for _ in range(num_cards):
                    if player.private.hand:
                        card = player.private.hand.pop()
                        placed_cards.append(card)
                game_state.common.central_pile.extend(placed_cards)
                player.public.declared_rank = rank
                logger.info(f"Player {current_player} declares rank {rank} and places {num_cards} cards.")
                game_state.players[game_state.common.current_player].public.declared_rank = None
                game_state.common.current_player = (current_player + 1) % game_state.common.num_players
                player.public.declared_rank = None

        elif action['action'] == 'challenge':
            challenger = current_player
            challenged_player = (challenger + 1) % game_state.common.num_players
            declared_rank = game_state.players[challenged_player].public.declared_rank
            logger.info(f"Player {challenger} challenges Player {challenged_player}'s declaration of {declared_rank}.")

            actual = any(card.rank == declared_rank for card in game_state.common.central_pile)
            if actual:
                # If the challenge fails, challenger receives the pile
                logger.info(f"Player {challenger} failed to challenge Player {challenged_player}.")
                game_state.players[challenger].private.hand.extend(game_state.common.central_pile)
                game_state.common.central_pile = []
                game_state.common.current_player = challenged_player
            else:
                # If the challenge succeeds, challenged player receives the pile
                logger.info(f"Player {challenger} successfully challenged Player {challenged_player}.")
                game_state.players[challenged_player].private.hand.extend(game_state.common.central_pile)
                game_state.common.central_pile = []
                game_state.common.current_player = challenger

        # If the current player's hand is empty, move the turn to next player
        if not player.private.hand:
            game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    elif phase == 'ExchangeAlliances':
        if action['action'] == 'exchange':
            if not player.private.exchange_used:
                target_player = action['args']['target_player']
                if target_player != current_player:
                    card_indices = action['args']['card_indices']
                    if card_indices and all(0 <= idx < len(player.private.hand) for idx in card_indices):
                        exchanged_cards = [player.private.hand.pop(idx) for idx in sorted(card_indices, reverse=True)]
                        target = game_state.players[target_player]
                        target.private.hand.extend(exchanged_cards)
                        player.public.exchanged_cards.extend([card.get_str() for card in exchanged_cards])
                        player.private.exchange_used = True
                        logger.info(f"Player {current_player} exchanged cards with Player {target_player}.")
                        game_state.common.current_player = (current_player + 1) % game_state.common.num_players
                    else:
                        logger.info(f"Player {current_player} attempted an invalid card exchange.")
        elif action['action'] == 'form_alliance':
            allies = action['args']['allies']
            if len(allies) >= 1 and current_player not in allies:
                game_state.common.faceup_cards.alliances.append({
                    'player': current_player,
                    'allies': allies
                })
                logger.info(f"Player {current_player} formed alliances with Players {allies}.")
                game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    elif phase == 'GemCollectionFinalMoves':
        if game_state.common.is_over:
            return game_state  # Exit early if the game is over

        if action['action'] == 'collect_gems':
            num_gems = action['args']['num_gems']
            if num_gems > 0:
                player.public.gems += num_gems
                logger.info(f"Player {current_player} collected {num_gems} gems.")
                game_state.common.current_player = (current_player + 1) % game_state.common.num_players
        elif action['action'] == 'final_move':
            if player.private.hand:
                card = player.private.hand.pop()
                game_state.common.central_pile.append(card)
                logger.info(f"Player {current_player} passed a card to the central pile.")
                game_state.common.current_player = (current_player + 1) % game_state.common.num_players

        if not any(len(p.private.hand) > 0 for p in game_state.players):
            game_state.common.is_over = True
            logger.info("The game has concluded. Calculating final scores...")
            game_state.common.winner = determine_winner(game_state, logger)

    # Transition phases
    all_hands_empty = all(len(p.private.hand) == 0 for p in game_state.players)
    if phase == 'Accumulation' and all_hands_empty:
        game_state.common.phase_tracker = 'ExchangeAlliances'
        logger.info("Transitioning to Exchange and Alliances phase.")
    elif phase == 'ExchangeAlliances' and not any(len(p.private.hand) > 0 for p in game_state.players):
        game_state.common.phase_tracker = 'GemCollectionFinalMoves'
        logger.info("Transitioning to Gem Collection and Final Moves phase.")
    elif phase == 'GemCollectionFinalMoves' and not any(len(p.private.hand) > 0 for p in game_state.players):
        game_state.common.is_over = True
        logger.info("The game has concluded. Calculating final scores...")
        game_state.common.winner = determine_winner(game_state, logger)

    return game_state

def determine_winner(game_state: Dict, logger: EnvLogger) -> Optional[int]:
    """Determine the winner based on scoring rules."""
    max_score = -1
    winner = None
    for pid, player in enumerate(game_state.players):
        score = player.public.gems * 2 + player.public.bonuses * 5 + player.private.suit_diversity
        logger.info(f"Player {pid} has a score of {score}.")
        if score > max_score:
            max_score = score
            winner = pid
    if winner is not None:
        logger.info(f"Player {winner} wins with a score of {max_score}.")
    return winner

def get_legal_actions(game_state: Dict) -> List[dict]:
    """Get all legal actions given the current state."""
    phase = game_state.common.phase_tracker
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    legal_actions = []

    if game_state.common.is_over:
        return legal_actions

    if phase == 'Accumulation':
        # Add declare_and_place options for all ranks if the player has enough cards
        available_ranks = set(card.rank for card in player.private.hand)
        for rank in available_ranks:
            for num_cards in range(1, min(5, len(player.private.hand)+1)):  # Ensure that num_cards <= 4
                legal_actions.append({'action': 'declare_and_place', 'args': {'rank': rank, 'num_cards': num_cards}})
                
        # Find the player who declared a rank
        declared_rank_owner = None
        for idx, p in enumerate(game_state.players):
            if p.public.declared_rank is not None:
                declared_rank_owner = idx
                break
        
        if declared_rank_owner is not None and current_player == (declared_rank_owner + 1) % game_state.common.num_players:
            player_has_declared_rank = any(p.public.declared_rank is not None for p in game_state.players)
            if player_has_declared_rank:
                previous_player = (current_player - 1) % game_state.common.num_players
                if game_state.players[previous_player].public.declared_rank is not None:
                    legal_actions.append({'action': 'challenge', 'args': {}})
    elif phase == 'ExchangeAlliances':
        if not player.private.exchange_used and len(player.private.hand) >= 2:
            for pid in range(game_state.common.num_players):
                if pid != current_player:
                    legal_actions.append({'action': 'exchange', 'args': {'target_player': pid, 'card_indices': [0, 1]}})
        legal_actions.append({'action': 'form_alliance', 'args': {'allies': [pid for pid in range(game_state.common.num_players) if pid != current_player]}})
    elif phase == 'GemCollectionFinalMoves':
        if game_state.common.is_over:
            return legal_actions
        
        legal_actions.append({'action': 'collect_gems', 'args': {'num_gems': 1}})
        if player.private.hand:
            legal_actions.append({'action': 'final_move', 'args': {'card': player.private.hand[0]}})

    # Ensure at least one legal action is returned
    return legal_actions if legal_actions else [{'action': 'pass'}]


def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """Return the payoffs for each player."""
    payoffs = [0] * game_state.common.num_players
    if game_state.common.winner is not None:
        winner = game_state.common.winner
        for pid, player in enumerate(game_state.players):
            if pid == winner:
                payoffs[pid] += 10  # Base win
                payoffs[pid] += player.public.gems * 2
                payoffs[pid] += player.public.bonuses * 5
                payoffs[pid] += len(set(card.suit for card in player.private.hand))
                payoffs[pid] -= len(set(card.suit for card in player.private.hand))
        logger.info(f"Payoffs have been calculated: {payoffs}")
    return payoffs
"""End of the game code"""