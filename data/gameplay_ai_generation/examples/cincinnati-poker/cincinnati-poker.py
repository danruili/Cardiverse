"""Beginning of the game code"""
game_name = 'CommunityPoker'
recommended_num_players = 4
num_players_range = [2, 3, 4, 5, 6]

def initiation(num_players, logger):
    game_state = DotDict({
        'common': {
            'num_players': num_players,
            'current_player': 0,
            'pot': 0,
            'current_round': 0,  # Number of community cards revealed
            'current_bet': 0,
            'bets_in_round': {},
            'community_cards': {
                'facedown': [],
                'faceup': []
            },
            'folded_players': set(),
            'is_over': False,
            'winner': None,
            'players_to_act': list(range(num_players)),
            'last_raiser': None,
        },
        'players': [
            DotDict({
                'public': {
                    'bets_made': 0,
                    'chips': 1000
                },
                'private': {
                    'hand': []
                },
                'facedown_cards': {},
                'faceup_cards': {}
            }) for _ in range(num_players)
        ]
    })

    game_state = init_deck(game_state, logger)
    game_state = init_deal(game_state, logger)
    return game_state

def init_deck(game_state, logger):
    ranks = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    deck = [LLMCard({'rank': rank, 'suit': suit}) for suit in suits for rank in ranks]
    random.shuffle(deck)
    game_state.common.deck = deck
    logger.info("Deck initialized and shuffled.")
    return game_state

def init_deal(game_state, logger):
    deck = game_state.common.deck
    for i, player in enumerate(game_state.players):
        player.private.hand = [deck.pop() for _ in range(5)]
        logger.info(f"Player {i} is dealt 5 cards.")
    game_state.common.community_cards.facedown = [deck.pop() for _ in range(5)]
    logger.info("Community cards are set face down on the table.")
    return game_state

def proceed_round(action, game_state, logger):
    current_player = game_state.common.current_player
    player_state = game_state.players[current_player]
    logger.info(f"Player {current_player} action: {action}")

    if action['action'] == 'bet':
        amount = action['amount']
        if amount > player_state.public.chips:
            amount = player_state.public.chips
        player_state.public.bets_made += amount
        player_state.public.chips -= amount
        game_state.common.pot += amount
        game_state.common.current_bet = amount
        game_state.common.bets_in_round[current_player] = amount
        game_state.common.last_raiser = current_player
        logger.info(f"Player {current_player} bets {amount}.")
        game_state.common.players_to_act.remove(current_player)

    elif action['action'] == 'check':
        logger.info(f"Player {current_player} checks.")

    elif action['action'] == 'call':
        amount_to_call = game_state.common.current_bet - player_state.public.bets_made
        if amount_to_call > player_state.public.chips:
            amount_to_call = player_state.public.chips
        player_state.public.bets_made += amount_to_call
        player_state.public.chips -= amount_to_call
        game_state.common.pot += amount_to_call
        logger.info(f"Player {current_player} calls {amount_to_call}.")
        game_state.common.players_to_act.remove(current_player)

    elif action['action'] == 'raise':
        raise_amount = action['amount']
        amount_to_call = game_state.common.current_bet - player_state.public.bets_made
        total_amount = amount_to_call + raise_amount
        if total_amount > player_state.public.chips:
            total_amount = player_state.public.chips
            raise_amount = total_amount - amount_to_call
        player_state.public.bets_made += total_amount
        player_state.public.chips -= total_amount
        game_state.common.pot += total_amount
        game_state.common.current_bet = player_state.public.bets_made
        game_state.common.bets_in_round[current_player] = game_state.common.current_bet
        game_state.common.last_raiser = current_player
        logger.info(f"Player {current_player} raises to {total_amount}.")
        active_players = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]
        game_state.common.players_to_act = [i for i in active_players if i != current_player]

    elif action['action'] == 'fold':
        game_state.common.folded_players.add(current_player)
        logger.info(f"Player {current_player} folds.")
        game_state.common.players_to_act.remove(current_player)

    active_players = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]
    if len(active_players) == 1:
        game_state.common.is_over = True
        game_state.common.winner = active_players[0]
        logger.info(f"Only one player remains. Player {active_players[0]} wins the pot of {game_state.common.pot}.")
        return game_state

    # Skip turns and move to next phase if all players have no chips to bet
    if all(player.public.chips == 0 for player in game_state.players):
        logger.info("All players are out of chips. Forcing round progression.")
        game_state.common.current_round += 1
        if game_state.common.current_round <= 5:
            card = game_state.common.community_cards.facedown.pop(0)
            game_state.common.community_cards.faceup.append(card)
            logger.info(f"Revealed community card: {card.rank} of {card.suit}.")
        else:
            game_state.common.is_over = True
            logger.info("All betting rounds completed. Proceeding to showdown.")

        game_state.common.players_to_act = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]
    if not game_state.common.is_over:
        if all(player.public.chips == 0 for player in game_state.players) or all(action['action'] == 'check' for player_id in game_state.common.players_to_act for action in get_legal_actions(game_state)):
            # All players have no chips or all remaining players can only check, forcing round progression.
            logger.info("All players are checking or out of chips. Forcing round progression.")
            game_state.common.current_round += 1
            if game_state.common.current_round <= 5:
                card = game_state.common.community_cards.facedown.pop(0)
                game_state.common.community_cards.faceup.append(card)
                logger.info(f"Revealed community card: {card.rank} of {card.suit}.")
            else:
                game_state.common.is_over = True
                logger.info("All betting rounds completed. Proceeding to showdown.")
            game_state.common.current_bet = 0
            game_state.common.bets_in_round = {}
            game_state.common.last_raiser = None
            for player in game_state.players:
                player.public.bets_made = 0
            game_state.common.players_to_act = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]
        if not game_state.common.players_to_act:
            logger.info("Betting round is over.")
            game_state.common.current_bet = 0
            game_state.common.bets_in_round = {}
            game_state.common.last_raiser = None
            game_state.common.current_round += 1

            if game_state.common.current_round <= 5:
                card = game_state.common.community_cards.facedown.pop(0)
                game_state.common.community_cards.faceup.append(card)
                logger.info(f"Revealed community card: {card.rank} of {card.suit}.")
            else:
                game_state.common.is_over = True
                logger.info("All betting rounds completed. Proceeding to showdown.")

            for player in game_state.players:
                player.public.bets_made = 0
            game_state.common.players_to_act = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]

        next_player = (current_player + 1) % game_state.common.num_players
        while next_player in game_state.common.folded_players:
            next_player = (next_player + 1) % game_state.common.num_players
        game_state.common.current_player = next_player

    return game_state

def get_legal_actions(game_state):
    current_player = game_state.common.current_player
    player_state = game_state.players[current_player]
    legal_actions = []
    if game_state.common.current_bet == 0:
        legal_actions.append({'action': 'check'})
        if player_state.public.chips > 0:
            legal_actions.append({'action': 'bet', 'amount': player_state.public.chips})
    else:
        amount_to_call = game_state.common.current_bet - player_state.public.bets_made
        if amount_to_call <= player_state.public.chips:
            legal_actions.append({'action': 'call'})
            if player_state.public.chips > amount_to_call:
                legal_actions.append({'action': 'raise', 'amount': player_state.public.chips - amount_to_call})
        legal_actions.append({'action': 'fold'})
    return legal_actions

def get_payoffs(game_state, logger):
    payoffs = [0] * game_state.common.num_players
    if game_state.common.winner is not None:
        payoffs[game_state.common.winner] = game_state.common.pot
        logger.info(f"Player {game_state.common.winner} wins the pot of {game_state.common.pot}.")
    else:
        active_players = [i for i in range(game_state.common.num_players) if i not in game_state.common.folded_players]
        best_hand_rank = None
        best_players = []
        for i in active_players:
            player_cards = game_state.players[i].private.hand + game_state.common.community_cards.faceup
            hand_rank = evaluate_hand(player_cards)
            logger.info(f"Player {i}'s hand rank is {hand_rank}.")
            if best_hand_rank is None or hand_rank > best_hand_rank:
                best_hand_rank = hand_rank
                best_players = [i]
            elif hand_rank == best_hand_rank:
                best_players.append(i)
        if len(best_players) == 1:
            payoffs[best_players[0]] = game_state.common.pot
            logger.info(f"Player {best_players[0]} wins the pot of {game_state.common.pot}.")
        else:
            split_pot = game_state.common.pot / len(best_players)
            for winner in best_players:
                payoffs[winner] = split_pot
            logger.info(f"Players {best_players} split the pot of {game_state.common.pot}.")
    return payoffs

def evaluate_hand(cards):
    rank_values = {'2': 2, '3': 3, '4': 4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
    suits = {}
    ranks = {}
    for card in cards:
        rank = card.rank
        suit = card.suit
        ranks[rank] = ranks.get(rank, 0) + 1
        suits[suit] = suits.get(suit, 0) + 1
    is_flush = max(suits.values()) >= 5
    sorted_ranks = sorted([rank_values[r] for r in ranks.keys()], reverse=True)
    is_straight = False
    for i in range(len(sorted_ranks)-4):
        if sorted_ranks[i] - sorted_ranks[i+4] == 4:
            is_straight = True
            break
    max_count = max(ranks.values())
    if is_flush and is_straight:
        return 9
    elif max_count == 4:
        return 8
    elif max_count == 3 and 2 in ranks.values():
        return 7
    elif is_flush:
        return 6
    elif is_straight:
        return 5
    elif max_count == 3:
        return 4
    elif list(ranks.values()).count(2) >= 2:
        return 3
    elif 2 in ranks.values():
        return 2
    else:
        return 1
"""End of the game code"""