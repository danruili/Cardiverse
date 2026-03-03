import argparse
import os

from Utils.LLMHandler import LLMHandler
from GameIdea.database.group import create_group_ids, save_group_id_db
from GameIdea.database.embedding import load_embedding_db, build_embedding_db, create_projection


def run_grouping(
    working_dir: str,
    node_type: str = "entity",
    build_embeddings: bool = True,
    build_projection: bool = True,
    grouping_fig_path: str | None = None,
) -> None:
    if grouping_fig_path is None:
        grouping_fig_path = os.path.join(working_dir, "database", f"{node_type}_cluster.png")

    if build_embeddings:
        llm_handler = LLMHandler()
        print("Fetching embeddings...")
        build_embedding_db(working_dir, llm_handler)

    if build_projection:
        print("Projecting embeddings...")
        create_projection(working_dir, node_type)

    print("Grouping nodes...")
    emb_dict = load_embedding_db(working_dir, node_type)
    group_ids = create_group_ids(emb_dict, node_type, grouping_fig_path)
    save_group_id_db(working_dir, node_type, emb_dict, group_ids)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build embedding clusters and group IDs.")
    parser.add_argument(
        "--working-dir",
        default="outputs/graph",
        help="Working directory containing database files.",
    )
    parser.add_argument(
        "--node-type",
        choices=["entity", "logic"],
        default="entity",
        help="Embedding table/node type to cluster.",
    )
    parser.add_argument(
        "--grouping-fig-path",
        default=None,
        help="Optional explicit output path for dendrogram image.",
    )
    parser.add_argument(
        "--skip-build-embeddings",
        action="store_true",
        help="Skip refreshing embeddings from LLM.",
    )
    parser.add_argument(
        "--skip-projection",
        action="store_true",
        help="Skip UMAP/PCA projection generation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_grouping(
        working_dir=args.working_dir,
        node_type=args.node_type,
        build_embeddings=not args.skip_build_embeddings,
        build_projection=not args.skip_projection,
        grouping_fig_path=args.grouping_fig_path,
    )


if __name__ == "__main__":
    main()
