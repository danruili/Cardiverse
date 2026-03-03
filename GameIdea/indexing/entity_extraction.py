import os
import argparse
from retrying import retry

from GameIdea.llm_op.extract_v2 import extract_entity_graph
from GameIdea.database.node import save_graph_to_node_db
from GameIdea.database.game import save_graph_to_game_db
from GameIdea.visualize.show_as_nx import visualize_networkx_graph
from Utils.LLMHandler import LLMHandler

@retry(stop_max_attempt_number=3)
def build_graph_from_llm(
        game_desc_file_path, 
        llm_handler
    ):
    game_graph = extract_entity_graph(game_desc_file_path, llm_handler)
    return game_graph

def extract_game(
        game_desc_file_path: str,
        working_dir: str,
        llm_handler: LLMHandler
    ):
    game_name = os.path.basename(game_desc_file_path).split(".")[0]
    print(f"Extracting game {game_name}...")
    figure_path = os.path.join(working_dir, "games", f"{game_name}.png")
    # make directory if not exist
    os.makedirs(os.path.join(working_dir, "games"), exist_ok=True)

    game_graph = build_graph_from_llm(game_desc_file_path, llm_handler)
    save_graph_to_game_db(working_dir, game_name, game_graph)
    save_graph_to_node_db(working_dir, game_name, game_graph)

    # Visualize the graph
    nx_graph = game_graph.to_networkx()
    visualize_networkx_graph(nx_graph, figure_path=figure_path, working_dir=working_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract entity graphs from game descriptions.")
    parser.add_argument(
        "--working-dir",
        default="outputs/graph",
        help="Working directory for output databases and figures.",
    )
    parser.add_argument(
        "--game-desc-folder",
        default="data/game_ideation/examples",
        help="Folder containing .md game description files.",
    )
    parser.add_argument(
        "--game-desc-file",
        default=None,
        help="Single .md file to process. If set, --game-desc-folder is ignored.",
    )
    parser.add_argument(
        "--llm-model",
        "--llm_model",
        dest="llm_model",
        default="gpt-4o-2024-08-06",
        help="LLM model to use for extraction.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    llm_handler = LLMHandler(llm_model=args.llm_model)
    os.makedirs(args.working_dir, exist_ok=True)

    if args.game_desc_file:
        extract_game(args.game_desc_file, args.working_dir, llm_handler)
        return

    for game_desc_file in sorted(os.listdir(args.game_desc_folder)):
        if not game_desc_file.endswith(".md"):
            continue
        game_desc_file_path = os.path.join(args.game_desc_folder, game_desc_file)
        extract_game(game_desc_file_path, args.working_dir, llm_handler)


if __name__ == "__main__":
    main()
