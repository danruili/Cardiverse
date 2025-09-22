import random
from GameEngine.utils.base_agents import BaseAgent

class LeducHoldemRuleAgent(BaseAgent):
    ''' Leduc Hold'em Rule agent adapted for the new game engine.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_raw = True

    def step(self, state):
        ''' Predict the action given the structured state from the new game engine.
        
        Args:
            state (dict): Structured state from the game.

        Returns:
            (dict, dict): A tuple containing the chosen action dictionary
                          and an info dictionary for analysis.
        '''
        legal_actions = state['legal_actions']

        # Get the agent's current hand from the state
        current_player_id = state['common']['current_player']
        hand = state['players'][current_player_id]['facedown_cards']['hand'][0]['rank']
        public_card = state['common']['faceup_cards']['public_card']

        # import ipdb; ipdb.set_trace()
        
        if public_card:
            if public_card['rank'] == hand:
                action = {'action': 'raise'}
            else:
                action = {'action': 'fold'}
        else:
            if hand == 'K':
                action = {'action': 'raise'}
            elif hand == 'Q':
                action = {'action': 'check'}
            else:
                action = {'action': 'fold'}

        if action in legal_actions:
            return action, None
        else:
            if action['action'] == 'raise':
                return {'action': 'call'}, None
            if action['action'] == 'check':
                return {'action': 'fold'}, None
            if action['action'] == 'call':
                return {'action': 'raise'}, None
            else:
                # randomly choose a legal action if the preferred action is not available
                action = random.choice(legal_actions)
                return action, None

    def eval_step(self, state):
        return self.step(state)

