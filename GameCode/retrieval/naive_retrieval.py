import os
import pickle
import logging
import numpy as np
from Utils.LLMHandler import LLMHandler
from typing import List
from GameCode.utils.structure_description import structurize_description
from tqdm import tqdm


def get_embeddings(
        index_dir: str,
        llm_handler: LLMHandler,
    ) -> dict[str, list[float]]:
    """
    Explore all text files in a directory to do the following:

    (1) Read the content of the text file
    (2) Use LLMHandler.get_text_embeddings() to get the embeddings of the content
    (3) Save all embeddings into a dictionary with the key being the filename and the value being the embeddings
    """
    embeddings = {}
    for file in tqdm(os.listdir(index_dir)):
        if file.endswith('.md'):
            with open(os.path.join(index_dir, file), 'r', encoding='utf-8') as f:
                content = f.read()
            embeddings[file] = llm_handler.get_text_embeddings(content)
    return embeddings

def save_embeddings(embeddings: dict[str, list[float]], filename: str):
    with open(filename, 'wb') as f:
        pickle.dump(embeddings, f)

def get_similar_texts(text: str, 
                      llm_handler: LLMHandler,
                      index_dir: str,
                      ) -> List[str]:
    """
    Reads a pickle file containing embeddings
    and return the filenames of the text file with the descending cosine similarity to a given text.
    """
    embeddings_file_path = os.path.join(index_dir, 'embeddings.pkl')
    if not os.path.exists(embeddings_file_path):
        embeddings = get_embeddings(index_dir, llm_handler)
        save_embeddings(embeddings, embeddings_file_path)

    with open(embeddings_file_path, 'rb') as f:
        embeddings = pickle.load(f)
    
    text_embedding = llm_handler.get_text_embeddings(text)
    np_text_embedding = np.array(text_embedding)
    similarities = {filename: np.dot(np_text_embedding, np.array(embedding)) for filename, embedding in embeddings.items()}

    logging.info(f"Similarities: {similarities}")     
    return sorted(similarities, key=similarities.get, reverse=True)


