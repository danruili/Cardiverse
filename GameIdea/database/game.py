import os
import hashlib
from tinydb import TinyDB, Query

from GameIdea.base_type.graph import BaseGraph

"""
Game Database:

    Tables:
        - graph: Game graphs

    Fields:
        - game_id: str
        - game_name: str
        - graph_file_path: str
"""

def save_graph_to_game_db(
        working_dir: str,
        game_name: str,
        graph: BaseGraph
        ):
    """
    Save the graph to the database.
    """
    game_db_path = os.path.join(working_dir, "database", "game_db.json")
    # make directory if not exists
    os.makedirs(os.path.dirname(game_db_path), exist_ok=True)
    graph_file_path = os.path.join(working_dir, "games", f"{game_name}.json")
    os.makedirs(os.path.dirname(graph_file_path), exist_ok=True)
    game_id = hashlib.md5(game_name.encode()).hexdigest()

    game_db = TinyDB(game_db_path)
    table = game_db.table('graph')

    # save graph to file
    graph.save(graph_file_path)

    # overwrite/add game info to the game database
    table.upsert({'game_id': game_id, 'game_name': game_name, 'graph_file_path': graph_file_path}, Query().game_id == game_id)
    game_db.close()

def load_all_graphs_from_db(working_dir: str) -> dict[str, BaseGraph]:
    """
    Load all graphs from the database.
    """
    game_db_path = os.path.join(working_dir, "database", "game_db.json")
    game_db = TinyDB(game_db_path)
    table = game_db.table('graph')
    graph_dict = {}
    for row in table.all():
        game_name = row['game_name']
        graph_file_path = row['graph_file_path']
        graph = BaseGraph().read(graph_file_path)
        graph_dict[game_name] = graph
    game_db.close()
    return graph_dict


def add_depth_to_node_db(
        working_dir: str,
    ):
    """
    Add the depth of the node to the database.
    """
    # get all graphs
    graph_dict = load_all_graphs_from_db(working_dir)

    node_db_path = os.path.join(working_dir, "database", "node_db.json")
    node_db = TinyDB(node_db_path)
    node_table = node_db.table('entity')

    # iterate through all nodes in all graphs
    for _, graph in graph_dict.items():
        # save nodes to the node database
        for entity in graph.nodes:
            depth_str = entity.color_label
            if depth_str is None:
                continue
            depth = int(depth_str.split("_")[1])
            node_table.update({'depth': depth}, Query().node_id == entity.node_id)

    node_db.close()