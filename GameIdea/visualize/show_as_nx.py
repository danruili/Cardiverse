import networkx as nx
import matplotlib.pyplot as plt
from adjustText import adjust_text
from GameIdea.base_type.graph import BaseGraph
from GameIdea.database.concept import get_concept_by_group_id
from GameIdea.database.node import get_node_by_id
from GameIdea.database.group import get_group_id_by_node


def visualize_networkx_graph(
        nx_graph: nx.DiGraph, 
        working_dir: str,
        figure_path: str = "game_graph.png",
        graph_color_map: dict = None,
        ):
    """
    Visualizes a networkx graph with node labels and configurable node colors based on types.

    :param nx_graph: A networkx graph to visualize.
    :param graph_color_map: A dictionary mapping specific colors.
    """
    plt.figure(figsize=(12, 8))

    # Define default colors if no color map is provided
    default_color_map = {

        # depth
        "depth_0": "red",
        "depth_1": "skyblue",
        "depth_2": "green",
        "depth_3": "purple",

        # edge types
        "Contribute": "g",
        "Hinder": "r",
    }
    graph_color_map = graph_color_map or default_color_map
    edge_color_map = graph_color_map or default_color_map

    # Extract node labels and colors
    node_labels = {node: nx_graph.nodes[node].get("name", "")[:50] for node in nx_graph.nodes}
    node_pop = {}
    node_group_ids = {}
    for node in nx_graph.nodes:
        node_obj = get_node_by_id(working_dir, node)
        if node_obj:
            depth = node_obj.depth
            table_name = f"depth_{depth}"
            group_id = get_group_id_by_node(working_dir, node_obj, "entity")
            node_group_ids[node] = group_id
            concept = get_concept_by_group_id(working_dir, table_name, group_id)
            if concept:
                node_pop[node] = concept.popularity
            else:
                node_pop[node] = 0
        else:
            node_pop[node] = 0
    node_colors = []

    for node in nx_graph.nodes:
        node_type = nx_graph.nodes[node].get("type", "")
        color_label = nx_graph.nodes[node].get("color_label", None)

        # Priority: entity_type > logic_type > type
        if color_label and color_label in graph_color_map:
            node_colors.append(graph_color_map[color_label])
        else:
            node_colors.append(graph_color_map.get(node_type, "gray"))

    # prepare edge colors
    edge_color_labels = [nx_graph.edges[edge].get("color_label", "black") for edge in nx_graph.edges]
    edge_colors = [edge_color_map.get(label, "black") for label in edge_color_labels]

    # Draw the graph
    try:
        pos = nx.planar_layout(nx_graph)
    except Exception:
        pos = nx.spring_layout(nx_graph, k=1, iterations=200)

    nx.draw(
        nx_graph, pos, with_labels=False, 
        node_color=node_colors, edge_color=edge_colors, font_size=10, 
    )

    # Add labels and avoid overlap
    texts = []
    for node, (x, y) in pos.items():
        # keep 2 decimal places
        popularity_str = str(round(node_pop[node]*100, 1))
        label = node_labels[node] + f" [{node_group_ids[node]}]={popularity_str}%"
        texts.append(plt.text(x, y, label, fontsize=10, ha='center', va='center'))

    adjust_text(texts, arrowprops=dict(arrowstyle='-', color='gray', lw=0.5))

    # Show the plot
    plt.savefig(figure_path, dpi=300)
    # clear and close
    plt.clf()
    plt.close()
