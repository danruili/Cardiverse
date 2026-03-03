import os
import hashlib
from tinydb import TinyDB, Query

from GameIdea.base_type.graph import BaseGraph, BaseNode, NODE_TYPE, stringify_related_node_list, RelatedNode

"""
Node Database:

    Tables:
        - entity: Entity nodes

    Fields:
        - name: str
        - description: str
        - game_id: str
        - node_id: str
        - depth: int
        - upstream: str
        - downstream: str
        
"""

def save_graph_to_node_db(
        working_dir: str,
        game_name: str,
        graph: BaseGraph
        ):
    """
    Save the graph to the database.
    """
    node_db_path = os.path.join(working_dir, "database", "node_db.json")
    game_id = hashlib.md5(game_name.encode()).hexdigest()

    # extract nodes as entities and logics
    entities: list[BaseNode] = graph.nodes

    # save nodes to the node database
    node_db = TinyDB(node_db_path)
    node_table = node_db.table('entity')
    # clear nodes where game_id is the same
    node_table.remove(Query().game_id == game_id)
    # insert new nodes
    for entity in entities:
        node_table.insert({
            'name': entity.name,
            'description': entity.description,
            'game_id': game_id, 
            'node_id': entity.node_id,
            'depth': getattr(entity, 'depth', None),
            'upstream': stringify_related_node_list(entity.upstream),
            'downstream': stringify_related_node_list(entity.downstream),
            })
        
    node_db.close()


def get_all_nodes_from_db(working_dir: str, node_type: NODE_TYPE) -> list[BaseNode]:
    """
    Get all nodes of the given type from the database.
    """
    db_path = os.path.join(working_dir, "database", "node_db.json")
    db = TinyDB(db_path)
    table = db.table(node_type)
    nodes = [BaseNode(**node) for node in table.all()]
    db.close()
    return nodes

def get_nodes_by_query(working_dir: str, query: Query) -> list[BaseNode]:
    """
    Get the nodes by the query.
    """
    db_path = os.path.join(working_dir, "database", "node_db.json")
    db = TinyDB(db_path)
    entity_table = db.table('entity')
    entities = entity_table.search(query)
    db.close()
    return [BaseNode(**entity) for entity in entities]

def get_node_by_id(working_dir: str, node_id: str) -> BaseNode:
    """
    Get the node by its ID.
    """
    db_path = os.path.join(working_dir, "database", "node_db.json")
    db = TinyDB(db_path)
    entity_table = db.table('entity')
    entity = entity_table.get(Query().node_id == node_id)
    db.close()
    if entity:
        return BaseNode(**entity)
    return None

def save_nodes_to_db(
        working_dir: str,
        nodes: list[BaseNode],
):
    """
    Save the nodes to the database.
    """
    node_db_path = os.path.join(working_dir, "database", "node_db.json")
    node_db = TinyDB(node_db_path)
    node_table = node_db.table('entity')

    # insert new nodes
    for entity in nodes:
        node_table.insert({
            'name': entity.name,
            'description': entity.description,
            'node_id': entity.node_id,
            'depth': getattr(entity, 'depth', None),
            'upstream': stringify_related_node_list(entity.upstream),
            'downstream': stringify_related_node_list(entity.downstream),
            })
        
    node_db.close()

def clear_nodes_without_game_id(
        working_dir: str,
):
    """
    Clear nodes without game_id.
    """
    node_db_path = os.path.join(working_dir, "database", "node_db.json")
    node_db = TinyDB(node_db_path)
    node_table = node_db.table('entity')
    node_table.remove((Query().game_id == None) | (~Query().game_id.exists()))
    node_db.close()

def find_nodes_without_game_id(
        working_dir: str,
):
    """
    Find all nodes without game_id or does not contain the field.
    """
    node_db_path = os.path.join(working_dir, "database", "node_db.json")
    node_db = TinyDB(node_db_path)
    node_table = node_db.table('entity')
    nodes = node_table.search((Query().game_id == None) | (~Query().game_id.exists()))
    node_db.close()
    return [BaseNode(**node) for node in nodes]

if __name__ == "__main__":
    working_dir = 'MVC/workingSpace/graph_dec_3'
    clear_nodes_without_game_id(working_dir)
