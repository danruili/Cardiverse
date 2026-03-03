import argparse
import os

from tinydb import Query
from Utils.LLMHandler import LLMHandler

from GameIdea.database.concept import (
    build_concepts_in_between,
    build_concepts_within,
    create_depth_based_cluster,
    create_upstream_concept_cluster,
)
from GameIdea.database.node import clear_nodes_without_game_id


def _depth_gt(min_depth: int):
    """Safe TinyDB predicate for numeric depth comparisons."""
    return Query().depth.test(lambda v: isinstance(v, (int, float)) and v > min_depth)


def run_concept_build(
    working_dir: str,
    llm_model: str,
    clear_concept_db: bool = True,
    within_threshold_depth0: int = 5,
    within_threshold_depth1: int = 5,
    within_threshold_depth2: int = 5,
    in_between_threshold_depth0: int = 9,
    in_between_threshold_depth1: int = 3,
    in_between_threshold_depth2: int = 5,
) -> None:
    llm_handler = LLMHandler(llm_model=llm_model)

    clear_nodes_without_game_id(working_dir)

    if clear_concept_db:
        concept_db_path = os.path.join(working_dir, "database", "concept_db.json")
        if os.path.exists(concept_db_path):
            os.remove(concept_db_path)

    # Build clusters for all nodes where depth == 0.
    print("Building clusters (depth=0)...")
    query = (Query().depth == 0) & (Query().game_id.exists()) & (~(Query().game_id == None))
    instance_dict, popularity_dict = create_depth_based_cluster(
        working_dir, query, summarize_threshold=within_threshold_depth0
    )
    build_concepts_within(working_dir, 0, instance_dict, popularity_dict, llm_handler)
    instance_dict, _ = create_upstream_concept_cluster(
        working_dir, summarize_threshold=in_between_threshold_depth0
    )
    build_concepts_in_between(working_dir, 0, instance_dict, llm_handler)

    # Build clusters for all nodes where depth == 1.
    print("Building clusters (depth=1)...")
    query = (Query().depth == 1) & (Query().game_id.exists()) & (~(Query().game_id == None))
    instance_dict, popularity_dict = create_depth_based_cluster(
        working_dir, query, summarize_threshold=within_threshold_depth1
    )
    build_concepts_within(working_dir, 1, instance_dict, popularity_dict, llm_handler)
    base_query = (Query().depth == 0) & (Query().game_id.exists()) & (~(Query().game_id == None))
    instance_dict, _ = create_upstream_concept_cluster(
        working_dir,
        base_depth=0,
        base_query=base_query,
        summarize_threshold=in_between_threshold_depth1,
    )
    build_concepts_in_between(working_dir, 1, instance_dict, llm_handler)

    # Build clusters for all nodes where depth > 1.
    print("Building clusters (depth>1)...")
    query = _depth_gt(1) & (Query().game_id.exists()) & (~(Query().game_id == None))
    instance_dict, popularity_dict = create_depth_based_cluster(
        working_dir, query, summarize_threshold=within_threshold_depth2
    )
    build_concepts_within(working_dir, 2, instance_dict, popularity_dict, llm_handler)
    base_query = (Query().depth == 1) & (Query().game_id.exists()) & (~(Query().game_id == None))
    instance_dict, _ = create_upstream_concept_cluster(
        working_dir,
        base_depth=1,
        base_query=base_query,
        summarize_threshold=in_between_threshold_depth2,
    )
    build_concepts_in_between(working_dir, 2, instance_dict, llm_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build concept clusters and concept graph layers.")
    parser.add_argument(
        "--working-dir",
        default="outputs/graph",
        help="Working directory containing database files.",
    )
    parser.add_argument(
        "--skip-clear-concept-db",
        action="store_true",
        help="Do not reset concept_db.json before rebuilding concepts.",
    )
    parser.add_argument(
        "--llm-model",
        "--llm_model",
        dest="llm_model",
        default="gpt-4o-2024-08-06",
        help="LLM model to use for concept generation.",
    )
    parser.add_argument(
        "--within-threshold-depth0",
        type=int,
        default=5,
        help="Minimum cluster size for within-concept summaries at depth=0.",
    )
    parser.add_argument(
        "--within-threshold-depth1",
        type=int,
        default=5,
        help="Minimum cluster size for within-concept summaries at depth=1.",
    )
    parser.add_argument(
        "--within-threshold-depth2",
        type=int,
        default=5,
        help="Minimum cluster size for within-concept summaries at depth>1 (saved as depth=2 layer).",
    )
    parser.add_argument(
        "--in-between-threshold-depth0",
        type=int,
        default=9,
        help="Minimum upstream-group size for in-between summaries at depth=0.",
    )
    parser.add_argument(
        "--in-between-threshold-depth1",
        type=int,
        default=3,
        help="Minimum upstream-group size for in-between summaries at depth=1.",
    )
    parser.add_argument(
        "--in-between-threshold-depth2",
        type=int,
        default=5,
        help="Minimum upstream-group size for in-between summaries at depth>1 (saved as depth=2 layer).",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_concept_build(
        working_dir=args.working_dir,
        clear_concept_db=not args.skip_clear_concept_db,
        llm_model=args.llm_model,
        within_threshold_depth0=args.within_threshold_depth0,
        within_threshold_depth1=args.within_threshold_depth1,
        within_threshold_depth2=args.within_threshold_depth2,
        in_between_threshold_depth0=args.in_between_threshold_depth0,
        in_between_threshold_depth1=args.in_between_threshold_depth1,
        in_between_threshold_depth2=args.in_between_threshold_depth2,
    )


if __name__ == "__main__":
    main()
