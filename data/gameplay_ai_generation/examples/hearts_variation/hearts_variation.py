
"""Beginning of the game code"""
game_name = 'HeartsOfTime'
recommended_num_players = 4
num_players_range = [3, 4, 5, 6]

def initiation(num_players: int, logger) -> DotDict:
    """
    Initialize the game state for Hearts of Time.
    """
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': None,
            'current_leader': None,
            'is_over': False,
            'trick_history': [],
            'current_trick': [],
            'temporary_trump': None,
            'won_tricks': {pid: 0 for pid in range(num_players)},
            'disturbance_scores': {pid: 0 for pid in range(num_players)},
            'temporal_shift_status': {pid: False for pid in range(num_players)},
        },
        'players': [
            DotDict({
                'public': {
                    'scores': 0,
                    'trick_wins': 0,
                },
                'private': {
                    'hand': [],
                    'temporal_shift_used': False,
                },
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    game_state = set_starting_player(game_state, logger)
    return game_state

def init_deck(game_state: Dict, logger) -> Dict:
    """
    Initialize the deck, adjusting for number of players if necessary.
    """
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    
    num_players = game_state.common.num_players
    if num_players < 4:
        # Remove lowest ranks to balance the deck
        remove_ranks = []
        cards_per_player = 13
        total_cards = num_players * cards_per_player
        if total_cards < 52:
            num_remove = 52 - total_cards
            remove_ranks = ['2', '3'][:max(0, num_remove // 4)]
            deck = [card for card in deck if card.field['rank'] not in remove_ranks]
    random.shuffle(deck)
    game_state.common.facedown_cards = {'deck': deck}
    logger.info(f"Deck initialized with {len(deck)} cards.")
    return game_state

def init_deal(game_state: Dict, logger) -> Dict:
    """
    Deal 13 cards to each player.
    """
    num_players = game_state.common.num_players
    deck = game_state.common.facedown_cards['deck']
    assert len(deck) >= num_players * 13, "Not enough cards to deal 13 to each player."
    for pid in range(num_players):
        player_hand = [deck.pop() for _ in range(13)]
        game_state.players[pid].private.hand = player_hand
        logger.info(f"Player {pid} has been dealt 13 cards.")
    return game_state

def set_starting_player(game_state: Dict, logger) -> Dict:
    """
    Set the player with the 2 of Clubs as the starting player.
    """
    for pid, player in enumerate(game_state.players):
        for card in player.private.hand:
            if card.field['rank'] == '2' and card.field['suit'] == 'clubs':
                game_state.common.current_player = pid
                logger.info(f"Player {pid} starts the game with the 2 of Clubs.")
                return game_state
    # If 2 of Clubs not found, default to player 0
    game_state.common.current_player = 0
    logger.info("2 of Clubs not found. Player 0 starts the game.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger) -> Dict:
    """
    Process the player's action and update the game state.
    """
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    
    if action['action'] == 'declare_shift' and not player.private.temporal_shift_used:
        chosen_suit = action['args']['suit']
        game_state.common.temporary_trump = chosen_suit
        player.private.temporal_shift_used = True
        game_state.common.temporal_shift_status[current_player] = True
        logger.info(f"Player {current_player} declared a temporal suit shift to {chosen_suit}.")
    
    if action['action'] == 'play_card':
        suit = action['args']['suit']
        rank = action['args']['rank']
        card_to_play = None
        for card in player.private.hand:
            if card.field['suit'] == suit and card.field['rank'] == rank:
                card_to_play = card
                break
        if card_to_play:
            player.private.hand.remove(card_to_play)
            game_state.common.current_trick.append({'player': current_player, 'card': card_to_play})
            logger.info(f"Player {current_player} played {card_to_play.get_str()}.")
        
        if len(game_state.common.current_trick) == game_state.common.num_players:
            winner = determine_trick_winner(game_state, logger)
            game_state.common.trick_history.append(game_state.common.current_trick)
            game_state.players[winner].public.trick_wins += 1
            game_state.common.current_leader = winner
            update_disturbance(game_state, logger)
            game_state.common.current_leader = winner
            game_state.common.current_trick = []
            game_state.common.temporary_trump = None
            logger.info(f"Player {winner} won the trick.")
        
        game_state = check_game_over(game_state, logger)

    if not game_state.common.is_over:
        next_player = (current_player + 1) % game_state.common.num_players
        game_state.common.current_player = next_player
        logger.info(f"Next player is Player {next_player}.")
        
    return game_state

def determine_trick_winner(game_state: Dict, logger) -> int:
    """
    Determine the winner of the current trick.
    """
    trick = game_state.common.current_trick
    temporary_trump = game_state.common.temporary_trump
    led_suit = trick[0]['card'].field['suit']
    
    winning_card = trick[0]['card']
    winner = trick[0]['player']
    
    for play in trick[1:]:
        card = play['card']
        player = play['player']
        if temporary_trump and card.field['suit'] == temporary_trump:
            if winning_card.field['suit'] != temporary_trump or get_rank_value(card.field['rank']) > get_rank_value(winning_card.field['rank']):
                winning_card = card
                winner = player
        elif card.field['suit'] == led_suit and get_rank_value(card.field['rank']) > get_rank_value(winning_card.field['rank']):
            winning_card = card
            winner = player
    
    logger.info(f"The winner of the trick is Player {winner} with {winning_card.get_str()}.")
    return winner

def get_rank_value(rank: str) -> int:
    """
    Get numerical value of card rank.
    """
    rank_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                 '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    return rank_order.get(rank, 0)

def update_disturbance(game_state: Dict, logger) -> None:
    """
    Update disturbance scores based on the trick winner's collected cards.
    """
    winner = game_state.common.current_leader
    logger.info(f"Updating disturbance scores for Player {winner}.")
    for play in game_state.common.current_trick:
        card = play['card']
        if card.field['suit'] == 'hearts':
            game_state.common.disturbance_scores[winner] += 1
        if card.field['rank'] == 'Q' and card.field['suit'] == 'spades':
            game_state.common.disturbance_scores[winner] += 13
    logger.info(f"Player {winner} disturbance score is now {game_state.common.disturbance_scores[winner]}.")

def check_game_over(game_state: Dict, logger) -> Dict:
    """
    Check if any player has reached the disturbance threshold.
    """
    for pid, score in game_state.common.disturbance_scores.items():
        if score >= 100:
            game_state.common.is_over = True
            logger.info(f"Player {pid} has reached {score} disturbance points. Game over.")
            return game_state
    
    # Game is also over if all cards have been played
    if all(len(player.private.hand) == 0 for player in game_state.players):
        game_state.common.is_over = True
        logger.info("All cards have been played. Game over.")

    if game_state.common.is_over:
        lowest_score = min(game_state.common.disturbance_scores.values())
        winner = [pid for pid, score in game_state.common.disturbance_scores.items() if score == lowest_score]
        logger.info(f"Player {winner[0]} has the lowest disturbance score. Declared as the winner.")
    return game_state

def get_legal_actions(game_state: Dict) -> list[dict]:
    """
    Get all legal actions for the current player.
    """
    if game_state.common.is_over:
        return []
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    actions = []
    
    # Option to declare temporal suit shift if not used
    if not player.private.temporal_shift_used:
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        actions.extend([{'action': 'declare_shift', 'args': {'suit': suit}} for suit in suits])
    
    hand = player.private.hand
    led_suit = game_state.common.current_trick[0]['card'].field['suit'] if game_state.common.current_trick else None
    follow_suit_cards = [card for card in hand if card.field['suit'] == led_suit] if led_suit else []
    
    if follow_suit_cards:
        # Player must follow the led suit if possible
        actions.extend([{'action': 'play_card', 'args': {'suit': card.field['suit'], 'rank': card.field['rank']}} for card in follow_suit_cards])
    else:
        # No cards of led suit, or no led suit, or temporal trump, can play any card
        # Ensure first trick rules are considered
        if len(game_state.common.trick_history) == 0:
            # Can't play hearts or the Queen of Spades on the first trick
            non_penalty_cards = [card for card in hand if card.field['suit'] != 'hearts' and not (card.field['suit'] == 'spades' and card.field['rank'] == 'Q')]
            actions.extend([{'action': 'play_card', 'args': {'suit': card.field['suit'], 'rank': card.field['rank']}} for card in non_penalty_cards])
        
        # If first trick constraints do not apply, or all cards are penalty cards
        if len(actions) == 0:
            actions.extend([{'action': 'play_card', 'args': {'suit': card.field['suit'], 'rank': card.field['rank']}} for card in hand])
        # Ensure first trick rules are considered
        if len(game_state.common.trick_history) == 0:
            # Can't play hearts or the Queen of Spades on the first trick
            non_penalty_cards = [card for card in hand if card.field['suit'] != 'hearts' and not (card.field['suit'] == 'spades' and card.field['rank'] == 'Q')]
            actions.extend([{'action': 'play_card', 'args': {'suit': card.field['suit'], 'rank': card.field['rank']}} for card in non_penalty_cards])
        
        # If first trick constraints do not apply, or all cards are penalty cards
        if len(actions) == 0:
            actions.extend([{'action': 'play_card', 'args': {'suit': card.field['suit'], 'rank': card.field['rank']}} for card in hand])
    assert actions is not None and len(actions) > 0, "No legal actions available."
    return list(actions)

def get_payoffs(game_state: Dict, logger) -> List[int]:
    """
    Return the payoffs for each player based on disturbance scores.
    """
    for pid, score in game_state.common.disturbance_scores.items():
        logger.info(f"Player {pid} has a disturbance score of {score}.")
    # Payoffs are negative disturbance scores (less disturbance is better)
    return [-score for score in game_state.common.disturbance_scores.values()]
"""End of the game code"""