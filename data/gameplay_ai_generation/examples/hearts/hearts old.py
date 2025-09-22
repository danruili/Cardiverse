
"""Beginning of the game code"""
game_name = 'Hearts'
recommended_num_players = 4
num_players_range = [3, 4, 5]

def initiation(num_players, logger) -> DotDict:
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': None,
            'direction': 1,
            'winner': None,
            'is_over': False,
            'scores': [0] * num_players,
            'hearts_broken': False,
            'facedown_cards': {
                'deck': [],
            },
            'faceup_cards': {
                'current_trick': [],
                'trick_history': [],
            },
        },
        'players': [
            DotDict({
                'public': {
                    'tricks_won_count': 0,
                },
                'private': {},
                'facedown_cards': {
                    'hand': [],
                },
                'faceup_cards': {
                    'collected_cards': [],
                },
            })
            for _ in range(num_players)
        ],
    })
    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return DotDict(game_state)

def init_deck(game_state: Dict, logger: EnvLogger) -> Dict:
    num_players = game_state.common.num_players
    deck = []
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    for suit in suits:
        for rank in ranks:
            deck.append(LLMCard({'rank': rank, 'suit': suit}))
    if num_players == 3:
        deck = [card for card in deck if not (card['rank'] == '2' and card['suit'] == 'diamonds')]
    elif num_players == 5:
        deck = [card for card in deck if not (card['rank'] == '2' and card['suit'] == 'clubs')]
    random.shuffle(deck)
    logger.info("Deck initialized and shuffled.")
    game_state.common.facedown_cards['deck'] = deck
    return game_state

def init_deal(game_state: Dict, logger: EnvLogger) -> Dict:
    num_players = game_state.common.num_players
    deck = game_state.common.facedown_cards['deck']
    cards_per_player = {3: 17, 4: 13, 5: 10}[num_players]
    for _ in range(cards_per_player):
        for player in game_state.players:
            card = deck.pop()
            player.facedown_cards['hand'].append(card)
    logger.info("Cards dealt to players.")
    start_player = None
    for i, player in enumerate(game_state.players):
        for card in player.facedown_cards['hand']:
            if card['rank'] == '2' and card['suit'] == 'clubs':
                start_player = i
                break
    if start_player is None:
        for i, player in enumerate(game_state.players):
            for card in player.facedown_cards['hand']:
                if card['rank'] == '3' and card['suit'] == 'clubs':
                    start_player = i
                    break
    game_state.common['current_player'] = start_player if start_player is not None else 0
    logger.info(f"Player {game_state.common['current_player']} starts first.")
    return game_state

def proceed_round(action: dict, game_state: Dict, logger: EnvLogger) -> Dict:
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    hand = player.facedown_cards['hand']
    card_played = None
    for i, card in enumerate(hand):
        if card['rank'] == action['args']['rank'] and card['suit'] == action['args']['suit']:
            card_played = hand.pop(i)
            break
    if card_played:
        game_state.common.faceup_cards.current_trick.append({'player': current_player, 'card': card_played})
        logger.info(f"Player {current_player} plays {card_played.get_str()}.")
        if card_played['suit'] == 'hearts' or (card_played['rank'] == 'Q' and card_played['suit'] == 'spades'):
            game_state.common.hearts_broken = True
            logger.info("Hearts broken!")
    else:
        logger.info(f"Invalid play by player {current_player}.")
        return game_state

    if len(game_state.common.faceup_cards.current_trick) == game_state.common.num_players:
        winning_player = determine_trick_winner(game_state)
        game_state.players[winning_player].faceup_cards.collected_cards.extend(
            [item['card'] for item in game_state.common.faceup_cards.current_trick]
        )
        game_state.players[winning_player].public.tricks_won_count += 1
        game_state.common.faceup_cards.trick_history.append(
            game_state.common.faceup_cards.current_trick.copy()
        )
        game_state.common.faceup_cards.current_trick = []
        game_state.common.current_player = winning_player
        logger.info(f"Player {winning_player} wins the trick and will lead the next.")
    else:
        game_state.common.current_player = (current_player + 1) % game_state.common.num_players

    if all(len(p.facedown_cards.hand) == 0 for p in game_state.players):
        game_state = calculate_scores(game_state, logger)
        game_state.common.is_over = True
        logger.info("Round over. Scores updated.")
    
    return game_state

def determine_trick_winner(game_state: Dict) -> int:
    trick = game_state.common.faceup_cards.current_trick
    lead_suit = trick[0]['card']['suit']
    highest_card = trick[0]['card']
    winning_player = trick[0]['player']
    for t in trick[1:]:
        card = t['card']
        if card['suit'] == lead_suit and card_value(card['rank']) > card_value(highest_card['rank']):
            highest_card = card
            winning_player = t['player']
    return winning_player

def card_value(rank: str) -> int:
    order = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
    return order[rank]

def get_legal_actions(game_state: Dict) -> list:
    current_player = game_state.common.current_player
    player = game_state.players[current_player]
    hand = player.facedown_cards['hand']
    trick = game_state.common.faceup_cards.current_trick
    legal_actions = []
    
    if not trick:
        if not game_state.common.hearts_broken:
            non_hearts = [card for card in hand if card['suit'] != 'hearts']
            if non_hearts:
                hand = non_hearts
        for card in hand:
            if game_state.common.faceup_cards.trick_history or (card['rank'] == '2' and card['suit'] == 'clubs'):
                legal_actions.append({'action': 'play', 'args': {'rank': card['rank'], 'suit': card['suit']}})
    else:
        lead_suit = trick[0]['card']['suit']
        matching_suit = [card for card in hand if card['suit'] == lead_suit]
        if matching_suit:
            for card in matching_suit:
                legal_actions.append({'action': 'play', 'args': {'rank': card['rank'], 'suit': card['suit']}})
        else:
            for card in hand:
                legal_actions.append({'action': 'play', 'args': {'rank': card['rank'], 'suit': card['suit']}})
    return legal_actions

def calculate_scores(game_state: Dict, logger: EnvLogger) -> Dict:
    num_players = game_state.common.num_players
    scores = game_state.common.scores
    
    for i in range(num_players):
        collected = game_state.players[i].faceup_cards.collected_cards
        heart_points = sum(1 for card in collected if card['suit'] == 'hearts')
        q_spades_points = sum(13 for card in collected if card['rank'] == 'Q' and card['suit'] == 'spades')
        total_points = heart_points + q_spades_points
        scores[i] += total_points
    
    moon_shot = [i for i in range(num_players) if scores[i] - total_points == 0 and total_points == 26]
    if moon_shot:
        shooter = moon_shot[0]
        for i in range(num_players):
            scores[i] += 26 if i != shooter else -26
        logger.info(f"Player {shooter} shoots the moon!")
    else:
        logger.info("No one shot the moon this round.")
    
    game_state.common.scores = scores
    logger.info(f"Updated scores: {scores}")
    return game_state

def get_payoffs(game_state: Dict, logger: EnvLogger) -> List[int]:
    lowest_score = min(game_state.common.scores)
    payoffs = [lowest_score - score for score in game_state.common.scores]
    logger.info(f"Game over. Final payoffs: {payoffs}")
    return payoffs
"""End of the game code"""