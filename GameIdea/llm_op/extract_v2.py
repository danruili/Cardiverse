import json
from retrying import retry
from collections import deque
import os

from GameIdea.llm_op.prompt_v2 import PROMPTS
from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from GameIdea.base_type.graph import BaseNode, BaseGraph, RelatedNode
from GameCode.utils.formatting import extract_from_json


def read_game_desc(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines)

@retry(stop_max_attempt_number=3)
def chat_and_parse_with_retry(llm_handler: LLMHandler, chat_seq):
    raw_response = llm_handler.chat(chat_seq)
    response = extract_from_json(raw_response)
    dict_response = json.loads(response)
    return dict_response, response  # return both dict and string response

def extract_entity_graph(
        game_desc_file_path: str,
        llm_handler: LLMHandler,
        entity_num: int = 20,
        max_depth: int = 4
    ) -> BaseGraph:
    """
    Extracts a graph of entities from a game description using a language model handler.
        Args:
            game_desc_file_path (str): The file path to the game description.
            llm_handler (LLMHandler): The language model handler used for extracting entities.
            entity_num (int, optional): The maximum number of entities to extract. Defaults to 20.
            max_depth (int, optional): The maximum depth for BFS expansion. Defaults to 4.
        Returns:
            BaseGraph: A graph representing the entities and their relationships.
    """

    game_name = os.path.basename(game_desc_file_path).split(".")[0]
    game_desc = read_game_desc(game_desc_file_path)
    visited = set()
    queue = deque()

    # create a graph
    game_graph = BaseGraph(
        name=game_name,
        description=game_desc
    )

    # add a ending node
    end_node = BaseNode(
        name="End Game",
        description="End of the game"
    )
    game_graph.nodes.append(end_node)
    
    # First get all initial entities
    chat_seq = ChatSequence()
    prompt = PROMPTS["chain_extraction_init"].replace("{game_description}", game_desc)
    chat_seq.append(Message('user', prompt))
    first_entities, response = chat_and_parse_with_retry(llm_handler, chat_seq)
    chat_seq.append(Message('assistant', response))
    chat_seq.append(Message('user', PROMPTS["chain_extraction_init_check"]))
    first_entities, response = chat_and_parse_with_retry(llm_handler, chat_seq)
    
    # parse initial entities
    if first_entities and len(first_entities) > 0:
        for entity in first_entities:
            node = BaseNode(
                name=entity['name'],
                description=entity['description'],
                color_label=f"depth_{0}",
                depth = 0
            )
            game_graph.nodes.append(node)
            game_graph.add_edge(
                source=node,
                target=end_node,
                edge_type=entity['type'],
                reasoning=entity['reasoning']
            )
            entity_name = entity['name']
            visited.add(entity_name)
            queue.append((node, chat_seq, response, 0))
    
    def bfs_expand_entities() -> None:
        while queue and len(visited) < entity_num:
            
            parent_node, parent_chat_seq, parent_response, depth = queue.popleft()
            print(f"Expanding entity {parent_node.name} at depth {depth}")
            
            if depth >= max_depth:
                continue

            # Get all visited entities using visited set
            visited_entity_name_str = ", ".join(list(visited))
            
            # Create new chat sequence branching from parent
            new_chat_seq = ChatSequence()
            for msg in parent_chat_seq.messages:
                new_chat_seq.append(msg)
            new_chat_seq.append(Message('assistant', parent_response))
            new_chat_seq.append(Message('user', 
                PROMPTS["chain_extraction_subsequent"].replace("{goal}", parent_node.name).\
                    replace("{previous_mechanics}", visited_entity_name_str)))
            new_entity_list, new_response = chat_and_parse_with_retry(llm_handler, new_chat_seq)
            
            if new_entity_list and len(new_entity_list) > 0:
                for new_entity in new_entity_list:
                    new_entity_name = new_entity['name']
                    if new_entity_name not in visited:
                        child_node = BaseNode(
                            name=new_entity_name,
                            description=new_entity['description'],
                            color_label=f"depth_{depth + 1}",
                            depth = depth + 1
                        )
                        game_graph.nodes.append(child_node)
                        game_graph.add_edge(
                            source=child_node,
                            target=parent_node,
                            edge_type=new_entity['type'],
                            reasoning=new_entity['reasoning']
                        )
                        visited.add(new_entity_name)
                        queue.append((child_node, new_chat_seq, new_response, depth + 1))
                    else:
                        # Find the node and add edge
                        for child_node in game_graph.nodes:
                            if child_node.name == new_entity_name:
                                game_graph.add_edge(
                                    source=child_node,
                                    target=parent_node,
                                    edge_type=new_entity['type'],
                                    reasoning=new_entity['reasoning']
                                )
            else:
                print(f"No new entities found for {parent_node.name}")
                
    
    # Start BFS expansion from all initial entities
    bfs_expand_entities()

    # Cache the neighbor nodes and edges
    game_graph = cache_neighbor_nodes_and_edges(game_graph)
    
    return game_graph


def cache_neighbor_nodes_and_edges(graph: BaseGraph) -> BaseGraph:
    for node in graph.nodes:
        upstream = []
        downstream = []
        for edge in graph.edges:
            if edge.source_id == node.node_id:
                downstream.append(RelatedNode(node_id=edge.target_id, reasoning=edge.reasoning))
            if edge.target_id == node.node_id:
                upstream.append(RelatedNode(node_id=edge.source_id, reasoning=edge.reasoning))
        node.upstream = upstream
        node.downstream = downstream
    return graph


