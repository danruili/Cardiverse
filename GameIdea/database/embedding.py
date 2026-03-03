from typing import List, Dict, Tuple
import os
from tinydb import TinyDB, Query
from GameIdea.base_type.graph import NODE_TYPE
from GameIdea.database.node import get_all_nodes_from_db
from Utils.LLMHandler import LLMHandler
from tqdm import tqdm
import numpy as np

from sklearn.decomposition import PCA
import joblib

"""
Embedding database.

Tables:
    - entity: Entity embeddings
    - logic: Logic embeddings

Fields:
    - description: str
    - embedding: List[float]
    - group_id: int

"""


def get_embeddings(
        texts: List[str], 
        llm_handler: LLMHandler
        ) -> Dict[str, List[float]]:
    """
    Build a mapping from node description to its embedding.
    """
    # replace none with None string
    texts = [text if (text is not None) and (text != "") else "None" for text in texts]

    # build embeddings for the nodes
    batch_size = 50
    embeddings = []
    for i in tqdm(range(0, len(texts), batch_size)):
        batch_text = texts[i:i+batch_size]
        embeddings.extend(llm_handler.get_text_embeddings_multi(batch_text))

    return {node: embedding for node, embedding in zip(texts, embeddings)}

def build_embedding_db(
        working_dir: str, 
        llm_handler: LLMHandler,
        ):
    """
    Build embeddings for all nodes in the given graphs.
    """
    emb_db_path = os.path.join(working_dir, 'database', 'embeddings.json')

    entity_nodes = get_all_nodes_from_db(working_dir, 'entity')
    entity_node_texts = [node.embedding_str() for node in entity_nodes]

    entity_embedding_dict = load_embedding_db(working_dir, 'entity')
    entity_nodes_add = [node_text for node_text in entity_node_texts if node_text not in entity_embedding_dict]
    print(f"Get {len(entity_nodes_add)} new embeddings...")
    entity_embedding_dict_add = get_embeddings(entity_nodes_add, llm_handler)
    print(f"Add {len(entity_embedding_dict_add)} new embeddings to the database...")
    entity_embedding_dict.update(entity_embedding_dict_add)
    save_embeddings_to_db(emb_db_path, entity_embedding_dict, 'entity')
    print("Entity embeddings saved.")

def save_embeddings_to_db(
        db_path: str, 
        embedding_dict: Dict[str, List[float]], 
        node_type: NODE_TYPE
        ):
    """
    Save embeddings to TinyDB.
    """
    db = TinyDB(db_path)
    table = db.table(node_type)  # Use a separate table for each node type
    table.truncate()  # Clear existing data in the table

    table.insert_multiple(
        [{'description': description, 'embedding': embedding} for description, embedding in embedding_dict.items()]
    )
    db.close()

def load_embedding_db(
        working_dir: str, 
        node_type: NODE_TYPE = 'entity'
        ) -> Dict[str, List[float]]:
    """
    Load embeddings from TinyDB.
    """
    emb_db_path = os.path.join(working_dir, 'database', 'embeddings.json')
    db = TinyDB(emb_db_path)
    table = db.table(node_type)
    embedding_dict = {entry['description']: entry['embedding'] for entry in table.all()}
    db.close()
    return embedding_dict

def create_projection(working_dir: str, node_type: NODE_TYPE):
    """
    Create UMAP projection for the given node type. store the projection in the database as 'umap'.
    """
    from umap import UMAP

    emb_db_path = os.path.join(working_dir, 'database', 'embeddings.json')
    db = TinyDB(emb_db_path)
    table = db.table(node_type)
    embedding_dict = {entry['description']: entry['embedding'] for entry in table.all()}
    db.close()

    umap = UMAP(n_components=2,
                n_neighbors=100,
                min_dist=0.25,
                metric='cosine',
                random_state=42,
    )
    embeddings = np.array(list(embedding_dict.values()))
    umap_proj = umap.fit_transform(embeddings)

    # Save UMAP model to file
    umap_model_path = os.path.join(working_dir, 'database', f'{node_type}_umap_model.pkl')
    joblib.dump(umap, umap_model_path)

    # create PCA projection
    pca = PCA(n_components=2)
    pca_proj = pca.fit_transform(embeddings)

    # save PCA model to file
    pca_model_path = os.path.join(working_dir, 'database', f'{node_type}_pca_model.pkl')
    joblib.dump(pca, pca_model_path)

    # save UMAP projection to the database
    db = TinyDB(emb_db_path)
    table = db.table(node_type)
    umap_projections = {description: [float(umap_proj[i][0]), float(umap_proj[i][1])] for i, description in enumerate(embedding_dict.keys())}
    pca_projections = {description: [float(pca_proj[i][0]), float(pca_proj[i][1])] for i, description in enumerate(embedding_dict.keys())}
    table.update_multiple([({'umap': projection, 'pca': pca_projections[description]}, Query().description == description) 
                           for description, projection in umap_projections.items()])
    db.close()


class Projector:
    def __init__(self, working_dir: str, node_type: NODE_TYPE = "entity"):
        # load UMAP and PCA models
        self.umap_model = joblib.load(os.path.join(working_dir, 'database', f'{node_type}_umap_model.pkl'))
        # self.umap_model = None
        self.pca_model = joblib.load(os.path.join(working_dir, 'database', f'{node_type}_pca_model.pkl'))

    def project(self, embeddings: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if self.umap_model:
            umap_proj = self.umap_model.transform(embeddings)
        else:
            umap_proj = None
        pca_proj = self.pca_model.transform(embeddings)
        return umap_proj, pca_proj


def get_desc_proj_dict(working_dir: str, node_type: NODE_TYPE = "entity"
                       ) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
    """
    Get UMAP and PCA projections for the given node type.
    """
    emb_db_path = os.path.join(working_dir, 'database', 'embeddings.json')
    db = TinyDB(emb_db_path)
    table = db.table(node_type)
    umap_dict = {entry['description']: entry['umap'] for entry in table.all()}
    pca_dict = {entry['description']: entry['pca'] for entry in table.all()}
    db.close()
    return umap_dict, pca_dict