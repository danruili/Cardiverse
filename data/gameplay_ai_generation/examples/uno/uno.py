"""Beginning of the code template"""
game_name = 'uno' # TODO: specify the game name
recommended_num_players: int = 4 # TODO: specify the recommended number of players
num_players_range: List[int] = [2, 3, 4, 5, 6] # TODO: specify the range of number of players

# Define card values for scoring
CARD_VALUES = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'skip': 20, 'reverse': 20, 'draw_2': 20,
    'wild': 50, 'wild_draw_4': 50
}

def initiation(num_players, logger) -> DotDict:
    """
    Initialize the game state. The game state contains all information of the game.
    """
    # TODO: initialize the game state
    game_state = DotDict({
        'common':  # mandatory field, store non-player-related information
        {
            'num_players': num_players,
            'current_player': 0,  # mandatory field
            'direction': 1,
            'winner': None,  # mandatory field
            'is_over': False,  # mandatory field
            'facedown_cards':  # facedown cards such as deck go here
            {
                'deck': [],
            },
            'faceup_cards':  # faceup cards such as played cards go here
            {
                'played_cards': [],
                'target_card': None,
            },
        },
        'players': [  # mandatory field
            DotDict({
                'public': {}, # mandatory field, card-related fields shall not be included here
                'private': {},  # private information of the player
                'facedown_cards': {
                    'hand': [],
                },
                'faceup_cards': {
                    # cards in the faceup are visible to all players
                },
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return DotDict(game_state)


def init_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Initialize the deck for an Uno game.
    """
    # TODO: initialize the deck
    colors = ['red', 'yellow', 'green', 'blue']
    traits_with_one_card = ['0']
    traits_with_two_cards = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'skip', 'reverse', 'draw_2']
    
    deck = []
    for color in colors:
        for trait in traits_with_one_card:
            deck.append(LLMCard({'color': color, 'trait': trait, 'type': 'number'}))
        for trait in traits_with_two_cards:
            deck.extend([
                LLMCard({'color': color, 'trait': trait, 'type': 'action' if not trait.isdigit() else 'number'}),
                LLMCard({'color': color, 'trait': trait, 'type': 'action' if not trait.isdigit() else 'number'})
            ])
    
    # Add wild cards
    for _ in range(4):
        deck.append(LLMCard({'color': 'black', 'trait': 'wild', 'type': 'wild'}))
        deck.append(LLMCard({'color': 'black', 'trait': 'wild_draw_4', 'type': 'wild'}))

    random.shuffle(deck)
    game_state.common.facedown_cards.deck = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Deal cards to players and set up the initial game state.
    """
    # TODO: deal cards to players
    deck = game_state.common.facedown_cards.deck
    for i in range(game_state.common.num_players):
        game_state.players[i].facedown_cards.hand = deck[:7]
        deck = deck[7:]
    
    # Flip the top card
    top_card = deck.pop(0)
    
    # A wild card cannot be the first card
    while top_card.type == 'wild':
        deck.append(top_card)
        random.shuffle(deck)
        top_card = deck.pop(0)

    game_state.common.faceup_cards.target_card = top_card
    game_state.common.faceup_cards.played_cards.append(top_card)
    game_state.common.facedown_cards.deck = deck
    
    logger.info(f"Initial card is {top_card.get_str()}.")

    # Apply the effect of the first card
    if top_card.trait == 'skip':
        game_state.common.current_player = (game_state.common.current_player + game_state.common.direction) % game_state.common.num_players
        logger.info("First card is a skip. Player 0 is skipped.")
    elif top_card.trait == 'reverse':
        game_state.common.direction = -1
        game_state.common.current_player = (game_state.common.num_players - 1)
        logger.info("First card is a reverse. Direction is reversed.")
    elif top_card.trait == 'draw_2':
        player = game_state.players[game_state.common.current_player]
        drawn_cards = game_state.common.facedown_cards.deck[:2]
        player.facedown_cards.hand.extend(drawn_cards)
        game_state.common.facedown_cards.deck = game_state.common.facedown_cards.deck[2:]
        game_state.common.current_player = (game_state.common.current_player + game_state.common.direction) % game_state.common.num_players
        logger.info("First card is a Draw 2. Player 0 draws 2 cards and is skipped.")
    
    return game_state

def _replace_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Reshuffle the played cards to form a new deck when the deck runs out.
    """
    logger.info("Deck is empty. Reshuffling played cards.")
    played = game_state.common.faceup_cards.played_cards
    # The current target card remains on top
    new_deck = played[:-1]
    random.shuffle(new_deck)
    game_state.common.facedown_cards.deck = new_deck
    game_state.common.faceup_cards.played_cards = [played[-1]] # Keep only the target card
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    """
    Process the action, update the state: the played cards, target, current player, direction, is_over, winner.
    Remember to check if the game is over.
    """
    # TODO: process the action, update the state, check if the game is over
    current_player_idx = game_state.common.current_player
    player = game_state.players[current_player_idx]
    direction = game_state.common.direction
    num_players = game_state.common.num_players

    if action['action'] == 'draw':
        logger.info(f"Player {current_player_idx} draws a card.")
        if not game_state.common.facedown_cards.deck:
            game_state = _replace_deck(game_state, logger)
            if not game_state.common.facedown_cards.deck:
                 logger.info("No cards to draw. Ending turn.") # Should not happen with proper reshuffle
            else:
                 player.facedown_cards.hand.append(game_state.common.facedown_cards.deck.pop(0))
        else:
            player.facedown_cards.hand.append(game_state.common.facedown_cards.deck.pop(0))
        game_state.common.current_player = (current_player_idx + direction) % num_players
        return game_state

    # Handle 'play' action
    card_idx = action['args']['card_idx']
    card_to_play = player.facedown_cards.hand.pop(card_idx)
    
    logger.info(f"Player {current_player_idx} plays {card_to_play.get_str()}.")
    
    if card_to_play.type == 'wild':
        card_to_play.color = action['args']['chosen_color']
        logger.info(f"Player {current_player_idx} chose the color {card_to_play.color}.")

    game_state.common.faceup_cards.played_cards.append(card_to_play)
    game_state.common.faceup_cards.target_card = card_to_play
    
    if not player.facedown_cards.hand:
        game_state.common.is_over = True
        game_state.common.winner = current_player_idx
        logger.info(f"Player {current_player_idx} has no cards left and wins the game!")
        return game_state

    # Apply card effects
    next_player_idx = (current_player_idx + direction) % num_players
    
    if card_to_play.trait == 'skip':
        game_state.common.current_player = (next_player_idx + direction) % num_players
    elif card_to_play.trait == 'reverse':
        game_state.common.direction *= -1
        # With new direction, calculate next player from current
        game_state.common.current_player = (current_player_idx + game_state.common.direction) % num_players
    elif card_to_play.trait == 'draw_2':
        if len(game_state.common.facedown_cards.deck) < 2: game_state = _replace_deck(game_state, logger)
        game_state.players[next_player_idx].facedown_cards.hand.extend(game_state.common.facedown_cards.deck[:2])
        game_state.common.facedown_cards.deck = game_state.common.facedown_cards.deck[2:]
        game_state.common.current_player = (next_player_idx + direction) % num_players
    elif card_to_play.trait == 'wild_draw_4':
        if len(game_state.common.facedown_cards.deck) < 4: game_state = _replace_deck(game_state, logger)
        game_state.players[next_player_idx].facedown_cards.hand.extend(game_state.common.facedown_cards.deck[:4])
        game_state.common.facedown_cards.deck = game_state.common.facedown_cards.deck[4:]
        game_state.common.current_player = (next_player_idx + direction) % num_players
    else: # Number or regular wild card
        game_state.common.current_player = next_player_idx
        
    return game_state


def get_legal_actions(game_state: Dict) -> list[dict]:
    """
    Get all legal actions given the current state.
    """
    # TODO: get legal actions
    current_player_idx = game_state.common.current_player
    player = game_state.players[current_player_idx]
    hand = player.facedown_cards.hand
    target = game_state.common.faceup_cards.target_card
    
    legal_actions = []
    wild_draw_4_actions = []
    can_play_non_wild_draw_4 = False
    
    for i, card in enumerate(hand):
        # Wild cards are always legal to play
        if card.trait == 'wild':
            for color in ['red', 'yellow', 'green', 'blue']:
                legal_actions.append({'action': 'play', 'args': {'card_idx': i, 'chosen_color': color}})
            can_play_non_wild_draw_4 = True
        # Wild Draw 4 has a special condition
        elif card.trait == 'wild_draw_4':
            for color in ['red', 'yellow', 'green', 'blue']:
                wild_draw_4_actions.append({'action': 'play', 'args': {'card_idx': i, 'chosen_color': color}})
        # Regular card matching
        elif card.color == target.color or card.trait == target.trait:
            legal_actions.append({'action': 'play', 'args': {'card_idx': i}})
            can_play_non_wild_draw_4 = True

    # A player can only play Wild Draw 4 if they have no other playable cards
    if not can_play_non_wild_draw_4:
        legal_actions.extend(wild_draw_4_actions)
        
    # If no card can be played, drawing is the only option
    if not legal_actions:
        legal_actions.append({'action': 'draw'})
        
    assert legal_actions is not None and len(legal_actions) > 0, "get_legal_actions should not return None or an empty list."
    return legal_actions


def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    """ Return the payoffs for each player."""
    # TODO: get payoffs at the end of the game
    winner = game_state.common.winner
    payoffs = []
    
    if winner is None: # Should not happen in a normal game end
        return [0] * game_state.common.num_players

    logger.info(f"Calculating payoffs. Winner is Player {winner}.")
    
    for i, player in enumerate(game_state.players):
        if i == winner:
            payoffs.append(0)
        else:
            score = sum(CARD_VALUES[card.trait] for card in player.facedown_cards.hand)
            payoffs.append(-score)
            logger.info(f"Player {i} has a score of {-score}.")
            
    return payoffs

"""End of the code template"""