from copy import deepcopy
import logging
from typing import List, Union
from GameEngine.utils.base_message import BaseMsg, InfoMsg, CreateAnimMsg, MoveAnimMsg, DecisionMsg, TurnEndMsg


class EnvLogger:
    total_turn_limit = 1000
    last_n = 15
    max_log_length = 5000

    def __init__(self, config):
        self.state_trajectory: List[dict] = []
        self.log_items: List[Union[str, BaseMsg]] = []
        self.gameplay_logger = None
        self.console_logger = None
        self.enable_info = True

        if 'enable_info' in config:
            self.enable_info = config['enable_info']

        # gameplay logger for recording the games
        if 'log_path' in config:
            logger_name = config['log_path'].split('/')[-1].split('.')[0]
            self.gameplay_logger = logging.getLogger(logger_name)
            self.gameplay_logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(config['log_path'], encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.name = "file_handler"
            # not propagate to root logger
            self.gameplay_logger.propagate = False
            self.gameplay_logger.addHandler(file_handler)

        # console logger for displaying sys msg in PvE mode
        if 'pve' in config and config['pve']:
            if 'log_path' in config:
                logger_name = f"{config['log_path'].split('/')[-1].split('.')[0]}_console"
            else:
                import uuid
                logger_name = f"{uuid.uuid4().hex}_console"
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.name = "console_handler"
            self.console_logger = logging.getLogger(logger_name)
            self.console_logger.setLevel(logging.INFO)
            self.console_logger.addHandler(console_handler)

    def reset(self):
        self.state_trajectory = []
        self.log_items = []

    def info(self, msg, role=None):
        if not self.enable_info:
            return
        if self.console_logger:
            self.console_logger.info(msg)
        if self.gameplay_logger:
            self.gameplay_logger.info(msg)
        self.log_items.append(InfoMsg(msg, role))

    def warning(self, msg):
        self.info(msg)

    def create_anim(self, card, path, visible):
        self.log_items.append(CreateAnimMsg(card, path, visible))

    def move_anim(self, card, from_pos, to_pos, visible):
        self.log_items.append(MoveAnimMsg(card, from_pos, to_pos, visible))

    def record(self, msg):
        if self.gameplay_logger:
            self.gameplay_logger.info(msg)
        self.log_items.append(msg)

    def act(self, player_id, action):
        decision_msg = DecisionMsg(player_id, action)
        self.log_items.append(decision_msg)
        if self.gameplay_logger:
            self.gameplay_logger.info(decision_msg.__str__())
        if self.console_logger:
            self.console_logger.info(decision_msg.__str__())
        return decision_msg.__str__()
    
    def append(self, state):
        """
        Append game state to the state trajectory.
        """
        self.state_trajectory.append(deepcopy(state))
        if len(self.state_trajectory) > self.total_turn_limit:
            front_index = max(0, len(self.state_trajectory) - self.last_n)
            last_n_logs = self.log_items[front_index:]
            # convert all items in last_n_logs to string
            last_n_logs = [str(item) for item in last_n_logs]
            # repeat poping the first element until the total character length of the last_n_logs is less than 1000
            while len(''.join(last_n_logs)) > self.max_log_length:
                last_n_logs.pop(0)
            last_logs = '\n'.join(last_n_logs)
            raise Exception('The game environment reaches the turn limit. Please check if there is infinite loop.\nLast few turns: \n{}'.format(last_logs))
    
    def get_history(self, player_id: int, for_display=False) -> List[dict]:
        """
        Get the history messages for a specific player.
        Starting from the last decision message of the player. Ending with the lastest message.
        """
        msg_list = []
        for msg in reversed(self.log_items):
            if isinstance(msg, DecisionMsg) and msg.player_id == player_id:
                msg_list.append(msg)
                break
            msg_list.append(msg)

        # reverse the list to make it in the right order
        msg_list.reverse()

        # clip the log items to the last 100 items
        self.log_items = self.log_items[-100:]

        # parse the messages
        final_msg_list = []
        for i, msg in enumerate(msg_list):
            if isinstance(msg, DecisionMsg):
                final_msg_list.append({
                    "type": "action",
                    "player_id": msg.player_id,
                    "action": msg.action,
                    "msg": msg.msg
                })
            elif isinstance(msg, InfoMsg):
                final_msg_list.append({
                    "type": "info",
                    "msg": msg.msg,
                    "role": msg.role
                })
            elif isinstance(msg, TurnEndMsg):
                final_msg_list.append({
                    "type": "turn_end",
                    "player_id": msg.player_id,
                    "msg": msg.msg
                })
            elif isinstance(msg, CreateAnimMsg) and for_display:
                final_msg_list.append({
                    "type": "create_anim",
                    "card": msg.card,
                    "path": msg.path,
                    "visible": msg.visible
                })
            elif isinstance(msg, MoveAnimMsg) and for_display:
                final_msg_list.append({
                    "type": "move_anim",
                    "card": msg.card,
                    "from_pos": msg.from_pos,
                    "to_pos": msg.to_pos,
                    "visible": msg.visible
                })
            
        return final_msg_list
        
