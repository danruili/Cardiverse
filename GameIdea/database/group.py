import os
from tinydb import TinyDB, Query
from GameIdea.base_type.graph import NODE_TYPE, BaseNode
from typing import List, Dict, Tuple, Any, Union
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from GameIdea.base_type.graph import NODE_TYPE


def create_group_ids(
        embedding_dict: Dict[str, List[float]],
        type: NODE_TYPE,
        figure_path: str
    ) -> List[int]:
    """
    Build clusters from the embeddings.

    Parameters:
        embedding_dict (Dict[str, List[float]]): A dictionary mapping node descriptions to embeddings.
        type (NODE_TYPE): The type of the nodes.
        figure_path (str): The path to save the dendrogram figure.

    Returns:
        List[int]: A list of cluster IDs for each node.
    """
    
    labels = list(embedding_dict.keys())
    embeddings = list(embedding_dict.values())
    threshold_map = {
        'entity': 0.4,
        'logic': 0.4,
    }
    threshold = threshold_map[type]
    cluster_ids, Z = hierarchical_clustering(embeddings, threshold)
    draw_dendrogram(Z, labels, threshold, figure_path)
    return [int(cluster_id) for cluster_id in cluster_ids]

def hierarchical_clustering(embeddings: List[np.ndarray], 
                            threshold: float,
                            ) -> Tuple[List[int], Any]:
    """
    Perform hierarchical clustering on the embeddings.
    """
    embeddings = np.array(embeddings)
    Z = linkage(embeddings, metric='cosine', method='average')
    h_clusters = fcluster(Z, threshold, criterion='distance')
    h_clusters -= 1 # fix h_clusters to 0-indexed
    return h_clusters, Z

def draw_dendrogram(Z: np.ndarray, labels: List[str], threshold: float,
                    save_path: str):
    """
    Draw a dendrogram of the hierarchical clustering.
    """
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import dendrogram

    plt.figure(figsize=(40, 4))
    dn = dendrogram(Z, leaf_rotation=90, leaf_font_size=8, color_threshold=threshold)
    plt.subplots_adjust(bottom=0.5, top=0.99, right=0.99, left=0.02)
    labels = [labels[int(i)][:40] for i in dn['leaves']]
    plt.gca().set_xticklabels(labels, fontsize=5)
    plt.savefig(save_path, dpi=300)


def save_group_id_db(working_dir: str, table_name: str, emb_dict: dict, group_ids: list):
    """
    Assigns a group_id to each item in the specified table sequentially.

    Parameters:
        db_path (str): Path to the TinyDB database file.
        table_name (str): Name of the table in the TinyDB database.
        group_ids (list): List of integers to be added as 'group_id'.
    """
    group_db_path = os.path.join(working_dir, 'database', 'group_ids.json')

    db = TinyDB(group_db_path)
    table = db.table(table_name)
    for i, (key, value) in enumerate(emb_dict.items()):
        table.upsert({'description': key, 'group_id': group_ids[i]}, Query().description == key)
    
    db.close()

def add_description_to_group_db(working_dir: str, table_name: str, descriptions: List[str], group_ids: List[int]):
    """
    Add descriptions and group_ids to the group database.

    Parameters:
        working_dir (str): Path to the working directory.
        table_name (str): Name of the table in the TinyDB database.
        descriptions (List[str]): List of descriptions.
        group_ids (List[int]): List of group IDs.
    """
    db_path = os.path.join(working_dir, "database", "group_ids.json")
    db = TinyDB(db_path)
    table = db.table(table_name)
    for i in range(len(descriptions)):
        table.upsert({'description': descriptions[i], 'group_id': group_ids[i]}, Query().description == descriptions[i])
    db.close()

def get_group_id_by_node(
        working_dir: str, 
        node: BaseNode,
        table_name: str = 'entity'
        ) -> Union[int, None]:
    """
    Get the group_id of the specified item in the table.

    Parameters:
        working_dir (str): Path to the working directory. 
        node (BaseNode): Node object.

    Returns:
        int: Group ID of the specified item.
    """
    db_path = os.path.join(working_dir, "database", "group_ids.json")
    db = TinyDB(db_path)
    table = db.table(table_name)
    item = table.get(Query().description == node.embedding_str())
    db.close()
    
    if item is None:
        return None
    return item['group_id']