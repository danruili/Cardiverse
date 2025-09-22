import random
from GameEngine.utils.base_agents import BaseAgent

class UnoRuleAgent(BaseAgent):
    ''' UNO Rule agent adapted for the new game engine.
    
    This agent's strategy is a direct translation of the original rule-based agent:
    1. If drawing is a legal option, it will always choose to draw.
    2. If it cannot draw but can play a 'wild_draw_4', it will do so and choose the 
       color that it holds the most of.
    3. Otherwise, it will randomly play a non-wild card.
    4. If it can only play wild cards, it will play one randomly.
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
        hand = state['players'][current_player_id]['facedown_cards']['hand']

        # --- Original Strategy 1: Always draw if possible ---
        # The original agent's logic was to draw if 'draw' was in the legal actions list.
        draw_action = next((a for a in legal_actions if a['action'] == 'draw'), None)
        if draw_action:
            info = {'legal_actions': legal_actions, 'probs': [1.0 if a == draw_action else 0 for a in legal_actions]}
            return draw_action, info

        # If we reach here, drawing is not an option. All legal_actions are 'play'.
        play_actions = legal_actions

        # --- Original Strategy 2: Prioritize Wild Draw 4 ---
        wd4_actions = [a for a in play_actions if hand[a['args']['card_idx']]["trait"] == 'wild_draw_4']
        if wd4_actions:
            non_wild_cards = self._filter_wild(hand, remove_wd4=False) # Keep regular wilds for color counting
            color_counts = self._count_colors(non_wild_cards)
            
            if not color_counts:
                best_color = random.choice(['red', 'green', 'blue', 'yellow'])
            else:
                best_color = max(color_counts, key=color_counts.get)
            
            chosen_action = None
            for action in wd4_actions:
                if action['args']['chosen_color'] == best_color:
                    chosen_action = action
                    break
            
            info = {'legal_actions': legal_actions, 'probs': [1.0 if a == chosen_action else 0 for a in legal_actions]}
            return chosen_action, info

        # --- Original Strategy 3: Play a random non-wild card ---
        # The original agent filtered out wild cards and chose randomly from the rest.
        non_wild_play_actions = self._filter_wild_actions(play_actions, hand)

        if non_wild_play_actions:
            chosen_action = random.choice(non_wild_play_actions)
            info = {'legal_actions': legal_actions, 'probs': [1.0 if a == chosen_action else 0 for a in legal_actions]}
            return chosen_action, info
        
        # --- Fallback: If only wild cards are playable, play one randomly ---
        # This mirrors the original filter_wild returning the whole hand if it's all wilds.
        chosen_action = random.choice(play_actions)
        info = {'legal_actions': legal_actions, 'probs': [1.0 if a == chosen_action else 0 for a in legal_actions]}
        return chosen_action, info

    def eval_step(self, state):
        return self.step(state)

    @staticmethod
    def _filter_wild_actions(actions, hand):
        ''' Filters out actions that involve playing any type of wild card. '''
        non_wild_actions = []
        for action in actions:
            card_played = hand[action['args']['card_idx']]
            if card_played["type"] != 'wild':
                non_wild_actions.append(action)
        return non_wild_actions
        
    @staticmethod
    def _filter_wild(hand, remove_wd4=True):
        ''' Filters wild cards from a hand of LLMCard objects.
            If remove_wd4 is False, it will only remove regular wild cards.
        '''
        if remove_wd4:
            return [card for card in hand if card["type"] != 'wild']
        else:
            return [card for card in hand if card["trait"] != 'wild']

    @staticmethod
    def _count_colors(hand):
        ''' Count the number of cards of each color in a hand of LLMCard objects.
        '''
        color_nums = {}
        for card in hand:
            if card["color"] != 'black':
                color_nums.setdefault(card["color"], 0)
                color_nums[card["color"]] += 1
        return color_nums