
"""Beginning of the game code"""
game_name = 'InBetween'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5, 6, 7]

def initiation(num_players, logger) -> DotDict:
    initial_chips = 10
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': None,
            'dealer': None,
            'pot': 0,
            'community_cards': {
                'faceup_cards': [],
            },
            'facedown_cards': {
                'deck': [],
            },
            'is_over': False,
            'winner': None,
        },
        'players': [
            DotDict({
                'public': {
                    'chips': initial_chips,
                },
            }) for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return game_state

def init_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state.common.facedown_cards.deck = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    num_players = game_state.common.num_players
    for player in game_state.players:
        player.public['chips'] -= 1
        game_state.common.pot += 1
    logger.info(f"Each player antes one chip. Pot is now {game_state.common.pot}.")
    deck = game_state.common.facedown_cards.deck
    initial_cards = []
    for i, player in enumerate(game_state.players):
        card = deck.pop()
        player.public['initial_card'] = card
        initial_cards.append((i, card))
        logger.info(f"Player {i} draws {card} as initial card.")
    def card_value(card):
        rank_order = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8,
                      '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
        return rank_order[card.rank]
    highest_value = -1
    dealer = None
    for i, card in initial_cards:
        value = card_value(card)
        if value > highest_value:
            highest_value = value
            dealer = i
    game_state.common.dealer = dealer
    logger.info(f"Player {dealer} is the dealer.")
    game_state.common.current_player = (dealer + 1) % num_players
    logger.info(f"Player {game_state.common.current_player} will start.")
    for player in game_state.players:
        del player.public['initial_card']
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    logger.info(f"Player {current_player}'s action: {action}")
    if action['action'] == 'bet':
        bet_amount = action['args']['bet']
        logger.info(f"Player {current_player} bets {bet_amount} chips.")
        player.public['chips'] -= bet_amount
        if not game_state.common.community_cards.faceup_cards:
            deck = game_state.common.facedown_cards.deck
            if len(deck) < 2:
                logger.info("Deck has become too small for drawing initial community cards, ending the game.")
                game_state.common.is_over = True
                return game_state
            card1 = deck.pop()
            card2 = deck.pop()
            game_state.common.community_cards.faceup_cards = [card1, card2]
            logger.info(f"Community cards are {card1} and {card2}.")
        else:
            card1, card2 = game_state.common.community_cards.faceup_cards
        card_values = [card_value(card1), card_value(card2)]
        card_values.sort()
        if card_values[0] == card_values[1]:
            win_amount = min(2, bet_amount)
            player.public['chips'] += win_amount
            game_state.common.pot -= win_amount
            logger.info(f"Duplicate cards! Player {current_player} wins {win_amount} chips.")
        elif card_values[1] - card_values[0] == 1:
            game_state.common.pot += bet_amount
            logger.info(f"Consecutive cards! Player {current_player} loses {bet_amount} chips.")
        else:
            deck = game_state.common.facedown_cards.deck
            if not deck:
                logger.info("Deck is empty, ending the game as no more cards can be drawn.")
                game_state.common.is_over = True
                return game_state
            third_card = deck.pop()
            logger.info(f"Third card drawn is {third_card}.")
            third_value = card_value(third_card)
            if card_values[0] < third_value < card_values[1]:
                win_amount = bet_amount
                player.public['chips'] += bet_amount + win_amount
                game_state.common.pot -= win_amount
                logger.info(f"Player {current_player} wins {bet_amount + win_amount} chips from the pot.")
            else:
                game_state.common.pot += bet_amount
                logger.info(f"Player {current_player} loses {bet_amount} chips to the pot.")
        num_players = game_state.common.num_players
        game_state.common.current_player = (current_player + 1) % num_players
        if game_state.common.current_player == game_state.common.dealer:
            game_state.common.dealer = (game_state.common.dealer + 1) % num_players
            game_state.common.current_player = (game_state.common.dealer + 1) % num_players
            game_state.common.community_cards.faceup_cards = []
            logger.info(f"Dealer moves to player {game_state.common.dealer}. Next player is {game_state.common.current_player}.")
        if game_state.common.pot <= 0:
            ante_total = 0
            for player in game_state.players:
                if player.public['chips'] > 0:
                    player.public['chips'] -= 1
                    ante_total += 1
            game_state.common.pot += ante_total
            logger.info(f"Pot was empty. Each player antes one chip. Pot is now {game_state.common.pot}.")
        for i, player in enumerate(game_state.players):
            if player.public['chips'] <= 0:
                logger.info(f"Player {i} has run out of chips.")
                game_state.common.is_over = True
                break
    return game_state

def get_legal_actions(game_state: Dict) -> list[dict]:
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    pot = game_state.common.pot
    player_chips = player.public['chips']
    legal_actions = []
    if player_chips > 0 and pot > 0:
        max_bet = min(player_chips, pot)
        for bet_amount in range(1, max_bet + 1):
            legal_actions.append({'action': 'bet', 'args': {'bet': bet_amount}})
    else:
        legal_actions.append({'action': 'pass'})
    return legal_actions

def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[Union[int, float]]:
    payoffs = [player.public['chips'] for player in game_state.players]
    logger.info(f"Final chip counts: {payoffs}")
    return payoffs

def card_value(card):
    rank_order = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8,
                  '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
    return rank_order[card.rank]
"""End of the game code"""