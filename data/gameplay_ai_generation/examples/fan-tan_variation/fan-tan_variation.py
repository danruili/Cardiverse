
"""Beginning of the game code"""
game_name = 'MasterSorcerer'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5, 6]

def initiation(num_players: int, logger) -> Dict:
    """Initialize the game state."""
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'winner': None,
            'is_over': False,
            'energy_pool': 0,
            'sacred_board': {
                'Earth': [],
                'Fire': [],
                'Water': [],
                'Air': [],
            },
            'player_order': list(range(num_players)),
            'faceup_cards': {
                'completed_confluences': [],
            },
            'facedown_cards': {
                'mystical_reserve': init_deck(),
            },
        },
        'players': [
            DotDict({
                'public': {
                    'visible_runes': [],
                    'confluences': [],
                },
                'private': {
                    'hand': [],
                    'mana_chips': 5,
                },
            }) for _ in range(num_players)
        ],
    })
    game_state = init_deal(game_state, logger)
    return game_state

def init_deck() -> List[LLMCard]:
    """Initialize the mystical reserve deck."""
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    elements = ['Earth', 'Fire', 'Water', 'Air']
    deck = [LLMCard({'rank': rank, 'element': element}) for element in elements for rank in ranks]
    random.shuffle(deck)
    return deck

def init_deal(game_state: Dict, logger) -> Dict:
    """Deal the initial runes to each player and handle additional mana ante."""
    logger.info("Dealing initial runes to players...")
    deck = game_state.common.facedown_cards.mystical_reserve
    for player in game_state.players:
        player.private.hand = [deck.pop() for _ in range(7)]
        if len(deck) < game_state.common.num_players * 7:
            player.private.mana_chips -= 1
            game_state.common.energy_pool += 1
            logger.info("A player has fewer runes and antes an additional mana chip.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    """Process the action and update the game state."""
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    deck = game_state.common.facedown_cards.mystical_reserve
    sacred_board = game_state.common.sacred_board

    # Ensure that the game does not end in an infinite loop
    if game_state.common.is_over:
        logger.info("Game already over.")
        return game_state

    if action['action'] == 'play_rune':
        rune = player.private.hand.pop(action['args']['rune_idx'])
        element = rune.element
        if can_play_rune(rune, sacred_board[element]):
            sacred_board[element].append(rune)
            player.public.visible_runes.append(rune)
            logger.info(f"Player {current_player} plays {rune}.")
            if can_create_confluence(sacred_board[element]):
                game_state.common.faceup_cards.completed_confluences.append(current_player)
                player.public.confluences.append('Confluence Spell')
                logger.info(f"Player {current_player} completes a Confluence Spell.")
        else:
            logger.info(f"Player {current_player} could not legally play {rune}.")

    elif action['action'] == 'merge_runes':
        idx1, idx2 = action['args']['rune_indices']
        rune1 = player.private.hand[idx1]
        rune2 = player.private.hand[idx2]
        player.private.hand.pop(idx2)
        player.private.hand.pop(idx1)
        merged_rune = merge_runes(rune1, rune2)
        sacred_board[merged_rune.element].append(merged_rune)
        player.public.visible_runes.append(merged_rune)
        logger.info(f"Player {current_player} merges {rune1} and {rune2} into {merged_rune}.")
        if can_create_confluence(sacred_board[merged_rune.element]):
            game_state.common.faceup_cards.completed_confluences.append(current_player)
            player.public.confluences.append('Confluence Spell')
            logger.info(f"Player {current_player} completes a Confluence Spell.")
            if deck:
                new_rune = deck.pop()
                player.private.hand.append(new_rune)
                logger.info(f"Player {current_player} draws a new rune after merging.")

    elif action['action'] == 'create_confluence':
        element = action['args']['element']
        if can_create_confluence(sacred_board[element]):
            game_state.common.faceup_cards.completed_confluences.append(current_player)
            player.public.confluences.append('Confluence Spell')
            logger.info(f"Player {current_player} creates a Confluence Spell in {element}.")

    elif action['action'] == 'aid_opponent':
        target_player = action['args']['target_player']
        rune_idx = action['args']['rune_idx']
        rune = player.private.hand.pop(rune_idx)
        game_state.players[target_player].private.hand.append(rune)
        logger.info(f"Player {current_player} aids Player {target_player} with {rune}.")

    elif action['action'] == 'pass':
        player.private.mana_chips -= 3
        game_state.common.energy_pool += 3
        logger.info(f"Player {current_player} passes and contributes 3 mana chips to the energy pool.")
    
    check_end_conditions(game_state, logger)

    # Check if the game ends and update the game state
    if not game_state.common.is_over:
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players
        logger.info(f"Next player's turn: Player {game_state.common.current_player}.")
    return game_state

def get_legal_actions(game_state: Dict) -> List[dict]:
    """Get all legal actions for the current player."""
    legal_actions = []
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    sacred_board = game_state.common.sacred_board

    # Plays any rune that aligns with previously played runes
    for idx, rune in enumerate(player.private.hand):
        if can_play_rune(rune, sacred_board[rune.element]):
            legal_actions.append({'action': 'play_rune', 'args': {'rune_idx': idx}})
    
    # Merges any two adjacent runes of the same element
    same_element_runes = {}
    for idx, rune in enumerate(player.private.hand):
        same_element_runes.setdefault(rune.element, []).append((idx, rune))
    for element, runes in same_element_runes.items():
        if len(runes) >= 2:
            for i in range(len(runes) - 1):
                for j in range(i + 1, len(runes)):
                    legal_actions.append({'action': 'merge_runes', 'args': {'rune_indices': [runes[i][0], runes[j][0]]}})
    
    # Can create confluence spells
    for element in sacred_board:
        if can_create_confluence(sacred_board[element]):
            legal_actions.append({'action': 'create_confluence', 'args': {'element': element}})

    # Aid opponents by donating a rune, for any rune
    for idx, rune in enumerate(player.private.hand):
        for target in range(game_state.common.num_players):
            if target != current_player:
                legal_actions.append({'action': 'aid_opponent', 'args': {'target_player': target, 'rune_idx': idx}})

    # Option to pass
    legal_actions.append({'action': 'pass', 'args': {}})

    assert legal_actions is not None and len(legal_actions) > 0, "No legal actions available."
    return legal_actions

def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[int]:
    """Calculate and return payoffs for each player."""
    payoffs = [0] * game_state.common.num_players
    for i, player in enumerate(game_state.players):
        payoffs[i] = len(player.private.hand)
        logger.info(f"Player {i} has {payoffs[i]} unplayed runes.")
    return payoffs

def can_play_rune(rune: LLMCard, played_runes: List[LLMCard]) -> bool:
    """Check if a rune can be played on the sacred board."""
    if not played_runes:
        return True
    last_rune = played_runes[-1]
    return rune.rank == last_rune.rank or is_consecutive(rune.rank, last_rune.rank)

def is_consecutive(rank1: str, rank2: str) -> bool:
    """Check if rank1 is consecutive to rank2."""
    order = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    try:
        idx1 = order.index(rank1)
        idx2 = order.index(rank2)
        return abs(idx1 - idx2) == 1
    except ValueError:
        return False

def merge_runes(rune1: LLMCard, rune2: LLMCard) -> LLMCard:
    """Merge two runes to create a Fusion Power rune."""
    new_rank = 'Fusion'
    new_element = rune1.element
    return LLMCard({'rank': new_rank, 'element': new_element})

def can_create_confluence(sacred_runes: List[LLMCard]) -> bool:
    """Check if a Confluence Spell can be created."""
    if len(sacred_runes) < 4:
        return False
    consecutive = 0
    for i in range(len(sacred_runes)-3):
        subset = sacred_runes[i:i+4]
        ranks = [r.rank for r in subset]
        if 'Fusion' in ranks:
            sorted_ranks = sorted([rank_order(r) for r in ranks if r != 'Fusion'])
            if sorted_ranks and sorted_ranks == list(range(sorted_ranks[0], sorted_ranks[0]+len(sorted_ranks))):
                return True
    return False

def rank_order(rank: str) -> int:
    """Return the order value of a rank."""
    order = {'A':1, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'Fusion':14}
    return order.get(rank, 0)

def check_end_conditions(game_state: Dict, logger: EnvLogger) -> None:
    """Check if the game has ended."""
    for i, player in enumerate(game_state.players):
        # Check if a player has an overwhelming number of confluence spells
        if len(player.public.confluences) > 20:
            game_state.common.is_over = True
            game_state.common.winner = i
            logger.info(f"Game over. Player {i} wins by creating the most confluence spells!")
    for i, player in enumerate(game_state.players):
        score = sum(1 for _ in player.private.hand)
        if score >= 100:
            game_state.common.is_over = True
            game_state.common.winner = min(range(game_state.common.num_players), key=lambda x: len(game_state.players[x].private.hand))
            logger.info(f"Game over. Player {game_state.common.winner} is crowned as Master Sorcerer with the fewest points!")

    for i, player in enumerate(game_state.players):
        if not player.private.hand:
            game_state.common.is_over = True
            game_state.common.winner = i
            logger.info(f"Game over. Player {i} has no more runes in hand and becomes Master Sorcerer!")

    if not game_state.common.facedown_cards.mystical_reserve:
        logger.info("Mystical reserve exhausted with no opportunity for further play. The game ends!")
        game_state.common.is_over = True

def reshuffle_mystical_reserve(game_state: Dict, logger: EnvLogger) -> None:
    """Reshuffle the sacred board's runes back into the mystical reserve."""
    logger.info("Reshuffling mystical reserve from the sacred board.")
    discarded = []
    for element in game_state.common.sacred_board:
        discarded.extend(game_state.common.sacred_board[element])
        game_state.common.sacred_board[element] = []
    game_state.common.facedown_cards.mystical_reserve = discarded
    random.shuffle(game_state.common.facedown_cards.mystical_reserve)
"""End of the game code"""