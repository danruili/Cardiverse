import argparse
import os
from GameIdea.base_type.graph import BaseNode
from GameIdea.base_type.concept import BaseConcept
from GameIdea.database.concept import get_concept_by_group_id
from GameIdea.database.node import get_node_by_id, get_nodes_by_query
from GameIdea.database.group import get_group_id_by_node
from tinydb import Query
import hashlib

NEW_BREED_PROMPT = """
Orginal game logic: {source_node}
Target game logic: {target_node}
"""

COUNTERPART_PROMPT = """
Orginal game logic: {source_node}, which serves for "{downstream_node}"
Target game logic: {target_node}
"""

def create_report(
        newly_breeded_instances: list[BaseNode],
        counterpart_dict: dict[int, list[tuple[BaseNode, BaseNode]]],
        node: BaseNode,
        node_pop_dict: dict[BaseNode, float]
        ):
    report = ""
    report += f"## {node.name}\n{node.description}\n\n"

    # print basic info
    report += f"### Basic Info\n"
    popularity_str = str(round(node_pop_dict[node] * 100, 2)) + "%"
    report += f"- Popularity: {popularity_str}\n"
    report += f"- Depth: {node.depth}\n"
    report += "\n"

    # print newly-breeded instances
    if len(newly_breeded_instances) > 0:
        report += "### Newly-breeded instances:\n"
        for instance in newly_breeded_instances:
            report += f"- {instance.embedding_str()}\n"
    report += "\n"

    # print counterparts
    if len(counterpart_dict) > 0:
        report += "### Counterparts:\n"
        for group_id, nodes in counterpart_dict.items():
            report += f"#### Group {group_id}\n"
            for counterpart_node_tuple in nodes:
                counterpart_node, downstream_node = counterpart_node_tuple
                report += f"- {counterpart_node.embedding_str()} ---> {downstream_node.embedding_str()}\n"
    report += "\n"

    return report

def get_newly_breeded_instances(
        working_dir: str,
        concept: BaseConcept
        ) -> list[BaseNode]:
    newly_breeded_instances: list[BaseNode] = []
    if len(concept.instances) > 0:
        for instance in concept.instances:
            similar_node = get_node_by_id(working_dir, instance)
            if similar_node and not similar_node.game_id:
                newly_breeded_instances.append(similar_node)
    return newly_breeded_instances

def get_counterparts(
        working_dir: str,
        node: BaseNode,
        excluded_group_ids: set[int]
        ) -> dict[int, list[tuple[BaseNode, BaseNode]]]:
    if node.depth != 1:
        return {}  # experiments show that only depth 1 nodes have meaningful counterparts

    downstream_nodes = node.downstream
    if node.depth > 2:
        target_depth = 2
    else:
        target_depth = node.depth - 1
    counterpart_dict: dict[int, list[BaseNode]] = {}  # group_id -> nodes
    for downstream_related_node in downstream_nodes:
        downstream_node = get_node_by_id(working_dir, downstream_related_node.node_id)
        downstream_group_id = get_group_id_by_node(working_dir, downstream_node, "entity")
        downstream_concept = get_concept_by_group_id(working_dir, f"depth_{target_depth}", downstream_group_id)
        if not downstream_concept:
            print(f"Cannot find concept for {downstream_node.name} [{downstream_group_id}]")
            continue
        for instance in downstream_concept.instances:
            downstream_neighbour = get_node_by_id(working_dir, instance)
            if downstream_neighbour.game_id:
                for upstream_related_node in downstream_neighbour.upstream:
                    upstream_id = upstream_related_node.node_id
                    counterpart_node = get_node_by_id(working_dir, upstream_id)
                    counterpart_node_group_id = get_group_id_by_node(working_dir, counterpart_node, "entity")
                    if counterpart_node_group_id not in excluded_group_ids:
                        counterpart_dict.setdefault(counterpart_node_group_id, []).append((counterpart_node, downstream_node))
    return counterpart_dict

def get_popular_nodes(
        working_dir: str,
        game_id: str,
        top_k: int
        ) -> tuple[list[BaseNode], set[int], dict[BaseNode, float], dict[BaseNode, BaseConcept]]:
    nodes = get_nodes_by_query(working_dir, Query().game_id == game_id)
    node_pop: dict[BaseNode, float] = {}
    node_concept: dict[BaseNode, BaseConcept] = {}
    group_ids = set()
    for node in nodes:
        depth = node.depth
        table_name = f"depth_{depth}"
        group_id = get_group_id_by_node(working_dir, node, "entity")
        concept = get_concept_by_group_id(working_dir, table_name, group_id)
        node_concept[node] = concept
        group_ids.add(group_id)
        if concept:
            node_pop[node] = concept.popularity
        else:
            node_pop[node] = 0

    # sort nodes by popularity, descending
    nodes = sorted(nodes, key=lambda x: node_pop[x], reverse=True)

    # get top k nodes
    top_nodes = nodes[:top_k]
    return top_nodes, group_ids, node_pop, node_concept


def get_mutation_candidates_for_node(
        working_dir: str,
        node: BaseNode,
        concept: BaseConcept,
        group_ids: set[int],
        node_pop: dict[BaseNode, float]
        ) -> tuple[str, list[dict]]:
    # get newly-breeded instances and counterparts
    if concept:
        newly_breeded_instances = get_newly_breeded_instances(working_dir, concept)
    else:
        newly_breeded_instances = []
    counterpart_dict = get_counterparts(working_dir, node, group_ids)
    
    # format results
    results = []
    for instance in newly_breeded_instances:
        results.append({
            "base_node": node,
            "type": "newly_breeded",
            "target_node": instance
        })
    for group_id, nodes in counterpart_dict.items():
        # randomly select one counterpart from nodes
        import random
        counterpart_node_tuple = random.choice(nodes)
        counterpart_node, downstream_node = counterpart_node_tuple
        results.append({
            "base_node": node,
            "type": "counterpart",
            "target_node": counterpart_node,
            "downstream_node": downstream_node
        })

    report = create_report(newly_breeded_instances, counterpart_dict, node, node_pop)
    return report, results


def get_inspiration_prompts_for_game(
        working_dir: str,
        game_name: str,
        top_k: int = 5,
        report_path: str = "report.md"
        ) -> list[str]:
    # get popular nodes in the game
    game_id = hashlib.md5(game_name.encode()).hexdigest()
    top_nodes, group_ids, node_pop, node_concept = get_popular_nodes(working_dir, game_id, top_k)

    # create report for popular nodes, and generate results
    report = ""
    results = []
    for node in top_nodes:
        concept = node_concept[node]
        report_seg, node_results = get_mutation_candidates_for_node(
            working_dir, node, concept, group_ids, node_pop)
        results.extend(node_results)
        report += report_seg
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # generate prompts
    prompts = []
    for i, result in enumerate(results):
        prompt = ""
        if result["type"] == "newly_breeded":
            prompt += NEW_BREED_PROMPT.format(
                source_node=result["base_node"].embedding_str(),
                target_node=result["target_node"].embedding_str()
            )
        # elif result["type"] == "counterpart":
        #     prompt += NEW_BREED_PROMPT.format(
        #         source_node=result["base_node"].embedding_str(),
        #         downstream_node=result["downstream_node"].embedding_str(),
        #         target_node=result["target_node"].embedding_str()
        #     )
        prompts.append(prompt)
    
    return prompts

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate inspiration prompts for mutating a specific game."
    )
    parser.add_argument(
        "--working-dir",
        default="outputs/graph",
        help="Working directory containing graph databases.",
    )
    parser.add_argument(
        "--game-name",
        required=True,
        help="Game name to query (used to derive game_id).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of most-popular nodes to inspect.",
    )
    parser.add_argument(
        "--report-path",
        default="report.md",
        help="Output path for the analysis report markdown.",
    )
    parser.add_argument(
        "--save-prompts",
        default=None,
        help="Optional path to save prompts as a markdown file.",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    os.makedirs(os.path.dirname(args.report_path) or ".", exist_ok=True)
    prompts = get_inspiration_prompts_for_game(
        working_dir=args.working_dir,
        game_name=args.game_name,
        top_k=args.top_k,
        report_path=args.report_path,
    )
    for prompt in prompts:
        print(prompt)

    if args.save_prompts:
        os.makedirs(os.path.dirname(args.save_prompts) or ".", exist_ok=True)
        with open(args.save_prompts, "w", encoding="utf-8") as f:
            for i, prompt in enumerate(prompts):
                f.write(f"## Prompt {i}\n{prompt.strip()}\n\n")


if __name__ == "__main__":
    main()
