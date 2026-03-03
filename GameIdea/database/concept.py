from GameIdea.database.node import get_node_by_id, save_nodes_to_db, get_nodes_by_query
from GameIdea.database.group import get_group_id_by_node, add_description_to_group_db
from GameIdea.llm_op.variate import summarize_and_variate_concept, concept_breed_in_between
from GameIdea.base_type.concept import BaseConcept
from GameIdea.base_type.graph import BaseNode, RelatedNode
from Utils.LLMHandler import LLMHandler
import os
from tinydb import TinyDB, Query
from tqdm import tqdm
import random
import json
from typing import Union


global_working_dir = 'MVC/workingSpace/graph_dec_2'

REPORT_TEMPLATE = """
# Concept {group_id}: {name}

## Abstraction
{description_common}

## Variation
{description_variation}

## Instances
{node_descriptions}
"""


def create_depth_based_cluster(
        working_dir: str,
        query: Query = Query().depth == 0,
        summarize_threshold: int = 14
    )-> tuple[dict[int, list[BaseNode]], dict[int, float]]:
    """
    Cluster the nodes where their descriptions are similar.
    """

    # Fundatmental concepts are nodes with depth == 0
    nodes = get_nodes_by_query(working_dir, query)
    print(f"Found {len(nodes)} nodes for clustering.")

    # Restrucutre the nodes by group id
    instance_dict: dict[int, list[BaseNode]] = {}
    for node in nodes:
        group_id = get_group_id_by_node(working_dir, node)
        instance_dict.setdefault(group_id, []).append(node)

    # Construct dict: groud_id -> group size
    group_size_dict = {group_id: len(nodes) for group_id, nodes in instance_dict.items()}

    # Sort the dict by group size, ascending order
    sorted_group_size_dict = dict(sorted(group_size_dict.items(), key=lambda x: x[1]))

    # For each group, calculate the popularity
    total_size = sum(group_size_dict.values())
    popularity_dict = {}
    for group_id, group_size in sorted_group_size_dict.items():
        popularity_dict[group_id] = group_size / total_size

    # Remove groups with less than summarize_threshold nodes
    instance_dict = {group_id: nodes for group_id, nodes in instance_dict.items() if len(nodes) >= summarize_threshold}

    return instance_dict, popularity_dict

def create_upstream_concept_cluster(
        working_dir: str,
        base_depth: int = -1,
        base_query: Query = Query().depth == 0,
        summarize_threshold: int = 9
    )-> tuple[dict[int, list[BaseNode]], dict[int, list[BaseNode]]]:
    """
    Cluster the nodes where they share the same downstream concepts.
    To reduce the number of nodes, only one node is selected from each concept group.
    """
    up_instance_dict: dict[int, list[BaseNode]] = {}
    if base_depth == -1:
        # when base_depth is -1, the base concept has only one value: root node (win/lose condition)
        up_nodes = get_nodes_by_query(working_dir, Query().depth == 0)
        up_instance_dict[-1] = {}
        for node in up_nodes:
            up_node_group_id = get_group_id_by_node(working_dir, node)
            # output <-1, <up_group_id, [up_node1, up_node2, ...]>>
            up_instance_dict[-1].setdefault(up_node_group_id, []).append(node)

    else:
        # Find base nodes, organized by group id. output <group_id, [base_node1, base_node2, ...]>
        nodes = get_nodes_by_query(working_dir, base_query)
        base_instance_dict: dict[int, list[BaseNode]] = {}
        for node in nodes:
            group_id = get_group_id_by_node(working_dir, node)
            base_concept = get_concept_by_group_id(working_dir, f"depth_{base_depth-1}", group_id)
            if base_concept:
                base_instance_dict.setdefault(group_id, []).append(node)

        # For each group, collect their upstream nodes. output <group_id, <up_group_id, [up_node1, up_node2, ...]>>
        for group_id, nodes in base_instance_dict.items():
            for node in nodes:
                for up_node in node.upstream:
                    up_node_content = get_node_by_id(working_dir, up_node.node_id)
                    up_node_group_id = get_group_id_by_node(working_dir, up_node_content)
                    up_instance_dict.setdefault(group_id, {}).setdefault(up_node_group_id, []).append(up_node_content)

    # Remove groups with less than summarize_threshold nodes
    new_up_instance_dict = {}
    for group_id, nodes in up_instance_dict.items():
        for up_group_id, up_nodes in nodes.items():
            if len(up_nodes) >= summarize_threshold:
                new_up_instance_dict.setdefault(group_id, {})[up_group_id] = up_nodes
    up_instance_dict = new_up_instance_dict

    # For each group, ramdomly select one node from each upstream group
    for group_id, nodes in up_instance_dict.items():
        if isinstance(nodes, dict):
            for up_group_id, up_nodes in nodes.items():
                random_idx = random.randint(0, len(up_nodes)-1)
                up_instance_dict[group_id][up_group_id] = [up_nodes[random_idx]]
    
    # flatten the dict
    for group_id, nodes in up_instance_dict.items():
        up_instance_dict[group_id] = [node for up_nodes in nodes.values() for node in up_nodes]

    return up_instance_dict, None

def build_concepts_within(
        working_dir: str,
        depth: int,
        instance_dict: dict[int, list[BaseNode]],
        popularity_dict: dict[int, float],
        llm_handler: LLMHandler, 
    ):
    global global_working_dir
    global_working_dir = working_dir

    # Set up concepts
    concept_list: list[BaseConcept] = []
    report = ""
    for group_id, nodes in tqdm(instance_dict.items()):
        node_descriptions = [describe_node(node, idx, simple=True) for idx, node in enumerate(nodes)]
        instance_ids = [node.node_id for node in nodes]

        # call LLMs to design new logic units
        abstraction, new_entity_dicts = summarize_and_variate_concept('\n'.join(node_descriptions), llm_handler)

        report += REPORT_TEMPLATE.format(
            group_id=group_id,
            name=abstraction['name'],
            description_common=abstraction['description']['common'],
            description_variation=abstraction['description']['variation'],
            node_descriptions='\n'.join(node_descriptions)
        )

        # parse new entities
        new_entities: list[BaseNode] = []
        for entity_dict in new_entity_dicts:
            new_entity = BaseNode(
                name=entity_dict['name'],
                description=entity_dict['description'],
                depth=depth
            )
            report += f"\n### {new_entity.name} (New)\n{new_entity.description}\n"
            instance_ids.append(new_entity.node_id)
            new_entities.append(new_entity)
        # save new entities to database
        save_nodes_to_db(working_dir, new_entities)
        add_description_to_group_db(working_dir, 'entity', 
                            [node.embedding_str() for node in new_entities], 
                            [group_id]*len(new_entities))

        concept = BaseConcept(
            name=abstraction['name'],
            description_common=abstraction['description']['common'],
            description_variation=abstraction['description']['variation'],
            group_id=group_id,
            depth=depth,
            instances=instance_ids,
            popularity=popularity_dict.get(group_id, None)
        )
        concept_list.append(concept)

    # print to a file
    report_path = os.path.join(working_dir, 'database', f'entity_report_depth_{depth}_within.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Entity report saved to {report_path}")
    
    # refresh database
    db_path = os.path.join(working_dir, 'database', 'concept_db.json')
    db = TinyDB(db_path)
    table = db.table(f"depth_{depth}")
    table.truncate()  # clear the table
    concept_dicts = [concept.model_dump() for concept in concept_list]
    table.insert_multiple(concept_dicts)
    db.close()

def build_concepts_in_between(
        working_dir: str,
        depth: int,
        instance_dict: dict[int, list[BaseNode]],
        llm_handler: LLMHandler, 
    ):
    global global_working_dir
    global_working_dir = working_dir

    # Set up concepts
    report = ""
    for group_id, nodes in tqdm(instance_dict.items()):

        # Get the theme of the downstream concept
        if depth == 0:
            theme = f"Fundamental concept: Win / Lose condition for the game"
        else:
            mother_concept = get_concept_by_group_id(working_dir, f"depth_{depth-1}", group_id)
            if not mother_concept:
                print(f"Group {group_id} has no concept in depth_0, skipped.")
                continue
            theme = f"{mother_concept.name}: {mother_concept.description_common}"
        # Get descriptions of the nodes
        node_descriptions = [describe_node(node, idx, simple=True) for idx, node in enumerate(nodes)]
        # Breed new concepts given the theme
        abstraction, entities = concept_breed_in_between(theme, '\n'.join(node_descriptions), llm_handler)

        report += REPORT_TEMPLATE.format(
            group_id=group_id,
            name=theme,
            description_common=abstraction['variation_summary'],
            description_variation=json.dumps(abstraction['category'], indent=4),
            node_descriptions='\n'.join(node_descriptions)
        )

        entitie_node_list = []
        for entity in entities:
            node = BaseNode(
                name=entity['name'],
                description=entity['description'],
                depth=depth,
                upstream=[],
                downstream=[]
            )
            report += f"\n### {node.name} (breeded)\n{node.description}\n"
            entitie_node_list.append(node)
        save_nodes_to_db(working_dir, entitie_node_list)

    # print report
    report_path = os.path.join(working_dir, 'database', f'entity_report_depth_{depth}_in_between.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Entity report saved to {report_path}")


def get_concept_by_group_id(
        working_dir: str,
        table_name: str,
        group_id: int
    ) -> Union[BaseConcept, None]:
    db_path = os.path.join(working_dir, 'database', 'concept_db.json')
    db = TinyDB(db_path)
    table = db.table(table_name)
    query = Query()
    result = table.get(query.group_id == group_id)
    db.close()
    if not result:
        return None
    return BaseConcept(**result)
    
def describe_node(
        node: BaseNode, 
        list_idx: int = None,
        simple: bool = False
        ) -> str:
    
    result = ""
    if list_idx is not None:
        result += f"### Instance {list_idx}: {node.name}\n{node.description}\n"
    else:
        result += f"### {node.name}\n{node.description}\n"

    if not simple:
        if len(node.upstream) > 0:
            result += "\nUpstream concepts:\n"
            for up_item in node.upstream:
                result += f"    - {describe_related_node(up_item)}\n"
        if len(node.downstream) > 0:
            result += "\nDownstream concepts:\n"
            for down_item in node.downstream:
                result += f"    - {describe_related_node(down_item)}\n"
    return result


def describe_related_node(
        related_node: RelatedNode
        ) -> str:
    working_dir = global_working_dir
    node = get_node_by_id(working_dir, related_node.node_id)
    return f"**{node.name}**: {node.description} ({related_node.reasoning})"
    
def load_entity_cluster_dict(
        working_dir: str
    ):
    db_path = os.path.join(working_dir, 'database', 'concept_db.json')
    db = TinyDB(db_path)
    table = db.table('entity')
    cluster_dict = {}
    for row in table.all():
        group_id = row['group_id']
        node_id = row['node_id']
        if group_id not in cluster_dict:
            cluster_dict[group_id] = []
        cluster_dict[group_id].append({
            'node_id': node_id,
        })
    db.close()
    return cluster_dict


if __name__ == "__main__":
    working_dir: str = 'MVC/workingSpace/graph_dec_2'

    # build_entity_cluster()
    entity_cluster_dict = load_entity_cluster_dict(working_dir)

    # get the occurence of each entity cluster
    cluster_occurence = {}
    for group_id, nodes in entity_cluster_dict.items():
        cluster_occurence[group_id] = len(nodes)

    # sort by occurence
    sorted_cluster_occurence = dict(sorted(cluster_occurence.items(), key=lambda x: x[1], reverse=True))
    x_labels = [f"{group_id}" for group_id in sorted_cluster_occurence.keys()]
    y_values = list(sorted_cluster_occurence.values())
    
    # draw histogram of occurence
    import matplotlib.pyplot as plt
    plt.figure(figsize=(20, 5))
    plt.bar(x_labels, y_values)
    plt.ylabel('Occurence')
    plt.title('Entity Cluster Occurence')
    plt.xticks(rotation=45)
    plt.tight_layout()
    occurance_path = os.path.join(working_dir, 'database', 'concept_occurence.png')
    plt.savefig(occurance_path)

    # get the group ids with the occurence in top 25% - 50% quantile
    occurence_values = list(cluster_occurence.values())
    import numpy as np
    q1_value = np.quantile(occurence_values, 0.8)
    q2_value = np.quantile(occurence_values, 0.65)
    second_quantile_group_ids = [group_id for group_id, occurence in cluster_occurence.items() if q2_value <= occurence <= q1_value]

    # create pairs
    import itertools
    pairs = list(itertools.combinations(second_quantile_group_ids, 2))

    # randomly select 3 pairs from pairs
    import random
    selected_pairs = random.sample(pairs, 2)
    for group_id1, group_id2 in selected_pairs:

        # get the nodes in the selected group
        nodes1 = entity_cluster_dict[group_id1]
        nodes2 = entity_cluster_dict[group_id2]

        print(f"Concept {group_id1}")
        for node_idx, node in enumerate(nodes1):
            node_content = get_node_by_id(working_dir, node['node_id'])
            print(node_content.describe(node_idx+1))

        print(f"Concept {group_id2}")
        for node_idx, node in enumerate(nodes2):
            node_content = get_node_by_id(working_dir, node['node_id'])
            print(node_content.describe(node_idx+1))
