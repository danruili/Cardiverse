
"""Beginning of the game code"""
game_name = 'Baccarat'
recommended_num_players = 7
num_players_range = [7,8,9]

def initiation(num_players: int, logger) -> DotDict:
    """
    Initialize the game state. The game state contains all information of the game.
    """
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,  # mandatory field
            'winner': None,  # mandatory field
            'is_over': False,  # mandatory field
            'facedown_cards': {  # facedown cards such as deck
                'deck': init_deck(logger),
            },
            'faceup_cards': {  # faceup cards visible to all players
                'player_hand': [],
                'banker_hand': [],
            },
            'bets': {  # store all bets here
                'Player': {},
                'Banker': {},
                'Tie': {},
            },
            'betting_complete': False,
        },
        'players': [
            DotDict({
                'public': {
                    'bet_amount': 0,
                    'current_bet': None,
                },
                'private': {},
                'facedown_cards': {},
                'faceup_cards': {},
            }) for _ in range(num_players)
        ],
    })
    return game_state

def init_deck(logger) -> list[LLMCard]:
    """Initialize the deck with 8 shuffled decks."""
    deck = []
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['clubs', 'diamonds', 'hearts', 'spades']
    for _ in range(8):
        for suit in suits:
            for rank in ranks:
                deck.append(LLMCard({'rank': rank, 'suit': suit}))
    random.shuffle(deck)
    logger.info("Deck initialized and shuffled with 8 decks.")
    return deck

def init_deal(game_state: DotDict, logger) -> DotDict:
    """Deal the initial cards to player and banker."""
    logger.info("Dealing initial cards...")
    deck = game_state.common.facedown_cards.deck
    game_state.common.faceup_cards.player_hand = [deck.pop() for _ in range(2)]
    game_state.common.faceup_cards.banker_hand = [deck.pop() for _ in range(2)]
    logger.info(f"Player's hand: {cards2list(game_state.common.faceup_cards.player_hand)}")
    logger.info(f"Banker's hand: {cards2list(game_state.common.faceup_cards.banker_hand)}")
    return check_for_naturals(game_state, logger)

def card_value(card: LLMCard) -> int:
    """Get the value of a card in Baccarat."""
    rank = card['rank']
    if rank in ['10', 'J', 'Q', 'K']:
        return 0
    elif rank == 'A':
        return 1
    else:
        return int(rank)

def hand_total(hand: list[LLMCard]) -> int:
    """Calculate the total of a hand."""
    return sum(card_value(card) for card in hand) % 10

def check_for_naturals(game_state: DotDict, logger) -> DotDict:
    """Check for natural totals of 8 or 9 for either player or banker."""
    player_total = hand_total(game_state.common.faceup_cards.player_hand)
    banker_total = hand_total(game_state.common.faceup_cards.banker_hand)
    if player_total in [8, 9] or banker_total in [8, 9]:
        logger.info("Natural total of 8 or 9. Game over.")
        game_state.common.is_over = True
        game_state = determine_winner(game_state, logger)
    else:
        logger.info("No natural total of 8 or 9. Proceeding to draw phase...")
        game_state = deal_third_card(game_state, logger)
        # After dealing third card, determine winner
        game_state = determine_winner(game_state, logger)
    return game_state

def deal_third_card(game_state: DotDict, logger) -> DotDict:
    """Deal a third card if necessary according to Baccarat rules."""
    deck = game_state.common.facedown_cards.deck
    player_hand = game_state.common.faceup_cards.player_hand
    banker_hand = game_state.common.faceup_cards.banker_hand

    player_total = hand_total(player_hand)
    banker_total = hand_total(banker_hand)

    player_drew = False
    if player_total <= 5:
        player_hand.append(deck.pop())
        logger.info("Player draws a third card.")
        player_drew = True

    # Banker drawing rules depending on player's third card
    banker_total = hand_total(banker_hand)  # recalculate after possible player draw
    if banker_total <= 5:
        if player_drew:
            player_third_card_value = card_value(player_hand[2])
            if (banker_total == 3 and player_third_card_value != 8) or \
               (banker_total == 4 and player_third_card_value in [2,3,4,5,6,7]) or \
               (banker_total == 5 and player_third_card_value in [4,5,6,7]):
                banker_hand.append(deck.pop())
                logger.info("Banker draws a third card based on player's third card value.")
        else:
            # Player did not draw, banker simply draws if ≤5
            banker_hand.append(deck.pop())
            logger.info("Banker draws a third card.")

    return game_state

def determine_winner(game_state: DotDict, logger) -> DotDict:
    """Determine the winner based on final totals."""
    player_total = hand_total(game_state.common.faceup_cards.player_hand)
    banker_total = hand_total(game_state.common.faceup_cards.banker_hand)
    logger.info(f"Player total: {player_total}, Banker total: {banker_total}")

    if player_total > banker_total:
        game_state.common.winner = 'Player'
    elif banker_total > player_total:
        game_state.common.winner = 'Banker'
    else:
        game_state.common.winner = 'Tie'

    logger.info(f"Game over. Winner: {game_state.common.winner}")
    game_state.common.is_over = True
    return game_state

def proceed_round(action: dict, game_state: DotDict, logger) -> DotDict:
    """
    Process the action, update the state: 
    The action is expected to be a betting action before dealing starts.
    
    Actions:
    - {'action': 'bet', 'args': {'bet_type': str, 'amount': int}}
    After all players have bet, we deal cards and proceed through the game.
    """
    current_player = game_state.common.current_player
    if game_state.common.is_over:
        # If game is already over, no more actions needed.
        return game_state

    # If bets not complete:
    if not game_state.common.betting_complete:
        if action['action'] == 'bet':
            bet_type = action['args']['bet_type']
            amount = action['args']['amount']
            # Record the bet
            game_state.common.bets[bet_type][current_player] = amount
            game_state.players[current_player].public.bet_amount = amount
            game_state.players[current_player].public.current_bet = bet_type
            logger.info(f"Player {current_player} bets {amount} on {bet_type}.")

            # Move to next player
            next_player = (current_player + 1) % game_state.common.num_players
            game_state.common.current_player = next_player

            # Check if all players have bet
            total_bets = sum(len(v) for v in game_state.common.bets.values())
            if total_bets == game_state.common.num_players:
                logger.info("All players have placed their bets. Dealing initial cards...")
                game_state.common.betting_complete = True
                game_state = init_deal(game_state, logger)

    return game_state

def get_legal_actions(game_state: DotDict) -> list[dict]:
    """
    Get all legal actions given the current state.
    Before betting phase ends, players can only bet.
    After betting completes and cards are dealt, no further actions (game plays itself out).
    """
    actions = []
    if game_state.common.is_over:
        return actions  # No further actions after game over

    if not game_state.common.betting_complete:
        # Players can place bets from 10 to 30 chips, multiples of 10
        bet_types = ['Player', 'Banker', 'Tie']
        for bt in bet_types:
            for amt in range(10, 31, 10):
                actions.append({'action': 'bet', 'args': {'bet_type': bt, 'amount': amt}})
    # After betting, the game just resolves automatically.

    return actions

def get_payoffs(game_state: DotDict, logger) -> list[Union[int, float]]:
    """Calculate the payoffs for each player based on bets and the winner."""
    payoffs = [0] * game_state.common.num_players
    if game_state.common.winner is not None:
        odds_map = {
            'Player': 1.0,
            'Banker': 0.95,  # Banker wins pay 0.95:1
            'Tie': 8.0       # Tie pays 8:1
        }
        winner = game_state.common.winner
        for player_id, player_state in enumerate(game_state.players):
            bet_type = player_state.public.current_bet
            bet_amount = player_state.public.bet_amount
            if bet_type is not None:
                if winner == bet_type:
                    # Win
                    winnings = bet_amount * odds_map[bet_type]
                    payoffs[player_id] += winnings
                    logger.info(f"Player {player_id} wins {winnings} chips on {bet_type} bet")
                elif winner == 'Tie' and bet_type != 'Tie':
                    # If tie but bet not tie, player gets bet back if it's a "push"? 
                    # Traditional baccarat: Player/Banker bets are a push on Tie.
                    # They don't lose their bet. Let's assume push returns bet_amount.
                    if bet_type in ['Player', 'Banker']:
                        payoffs[player_id] += 0  # Typically player just doesn't lose. They get their stake back.
                        logger.info(f"Player {player_id}'s {bet_type} bet is a push on Tie. No gain, no loss.")
                    # If strictly losing bets on tie, just do nothing:
                    # pass
                else:
                    # Lose bet, payoffs remain 0 for this player
                    logger.info(f"Player {player_id} loses {bet_amount} chips on {bet_type} bet")
    return payoffs

"""End of the game code"""
