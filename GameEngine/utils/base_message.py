class BaseMsg:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg

    def __str__(self):
        return self.msg

    def __json__(self):
        return self.msg

class InfoMsg(BaseMsg):
    def __init__(self, msg, role=None):
        self.msg = msg
        self.role = role

class ActMsg(BaseMsg):
    def __init__(self, player_id, action):
        self.msg = f"Player {player_id} decides to: {action_to_str(action)}"
        self.player_id = player_id
        self.action = action

class CreateAnimMsg(BaseMsg):
    def __init__(self, card, path, visible):
        self.msg = f"Create animation for card {card} at {path} with visibility {visible}"
        self.card = card
        self.path = path
        self.visible = visible

class MoveAnimMsg(BaseMsg):
    def __init__(self, card, from_pos, to_pos, visible):
        self.msg = f"Move animation for card {card} from {from_pos} to {to_pos} with visibility {visible}"
        try:
            self.card = card.__json__()
        except:
            self.card = card
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.visible = visible

class RecordMsg(BaseMsg):
    pass

class DecisionMsg(BaseMsg):
    def __init__(self, player_id, action: dict):
        self.msg = f"Player {player_id} decides to: {action_to_str(action)}"
        self.player_id = player_id
        self.action = action

class ObservationMsg(BaseMsg):
    def __init__(self, player_id: int, observation: dict):
        if 'recent_history' in observation:
            # remove history to avoid too long message
            observation.pop('recent_history')
        self.msg = f"Player {player_id} observes: {observation_to_str(observation)}"
        self.player_id = player_id
        self.observation = observation

class TurnEndMsg(BaseMsg):
    def __init__(self, player_id: int=-1):
        self.msg = f"---------- End of Player {player_id}'s turn ----------"
        self.player_id = player_id

class PayoffMsg(BaseMsg):
    def __init__(self, payoff: list[float]):
        self.msg = f"Game over. Payoffs for each player: {payoff}"
        self.payoff = payoff

def action_to_str(action: dict):
    try:
        if 'display_args' in action:
            return action['action'] + '-(' + ', '.join([str(k) + ': ' + str(v) for k, v in action['display_args'].items()]) + ')'
        elif 'args' in action:
            return action['action'] + '-(' + ', '.join([str(k) + ': ' + str(v) for k, v in action['args'].items()]) + ')'
        else:
            return action['action']
    except:
        return str(action)
    
def history_to_str(history: list[dict]):
    result_str = ""
    for i, history in enumerate(history):
        if history["type"] not in ['turn_end']:
            result_str += f"{history["msg"]}\n"
    return result_str

def observation_to_str(observation: dict):
    
    if 'common' not in observation:
        return str(observation)
    
    result_str = ""
    
    if 'recent_history' in observation:
        recent_history = observation['recent_history']
        result_str += f"# Gameplay since your last decision\n"
        result_str += history_to_str(recent_history)
    
    result_str += f"\n# Common Information\n"
    common = observation['common']
    if isinstance(common, dict):
        for k, v in common.items():
            if k == 'faceup_cards' and isinstance(v, dict):
                for k1, v1 in v.items():
                    if (('discard' in k1) or ('played_card' in k1)) and (isinstance(v1, list) and len(v1) > 10):
                        # only show last 10 cards
                        result_str += f"{k1} (shown lastest few cards): {v1[-10:]}\n"
                    else:
                        result_str += f"{k1}: {v1}\n"
            elif isinstance(v, dict):
                for k1, v1 in v.items():
                    result_str += f"{k1}: {v1}\n"
            elif k in ['is_over', 'winner']:
                continue  # do not show
            else:
                result_str += f"{k}: {v}\n"

    if 'players' in observation:
        result_str += "\n# Player Information\n"
        if not isinstance(observation['players'], list):
            result_str += str(observation['players'])
        else:
            for i, player in enumerate(observation['players']):
                if isinstance(player, dict) and player.get('public', {}).get('current_player', False):
                    result_str += f"\n## Player {i} (Self)\n"
                else:
                    result_str += f"\n## Player {i}\n"
                if isinstance(player, dict):
                    for k, v in player.items():
                        if isinstance(v, dict):
                            for k1, v1 in v.items():
                                result_str += f"{k1}: {v1}\n"
                        elif k == 'current_player':
                            continue  # do not show current player field
                        else:
                            result_str += f"{k}: {v}\n"
                else:
                    result_str += str(player)
    
    if 'legal_actions' in observation:
        result_str += "\n# Legal Actions\n"
        for i, legal_action in enumerate(observation['legal_actions']):
            result_str += f"{i}: {action_to_str(legal_action)}\n"

    return "\n```\n"+result_str+"```\n"