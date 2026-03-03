import os
import numpy as np
from Utils.LLMHandler import LLMHandler
import matplotlib.pyplot as plt
import argparse


def read_all_md(
        working_dir,
    ) -> list[str]:
    results = []
    file_names = []
    # iterate over all md files in the folder
    for root, dirs, files in os.walk(working_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                file_names.append(os.path.basename(file_path))
                with open(file_path, "r", encoding="utf-8") as f:
                    results.append(f.read())
    return results, file_names

def read_all_embs(
        working_dir,
        overwrite: bool = False
    ) -> tuple[np.ndarray, list[str]]:
    # try to read all the embeddings from pkl files
    pkl_path = os.path.join(working_dir, "embeddings.pkl")
    # read all the descriptions from md
    descs, file_names = read_all_md(working_dir)
    if (not os.path.exists(pkl_path)) or overwrite:
        llm_handler = LLMHandler()
        all_embs = llm_handler.get_text_embeddings_multi(descs)
        all_embs = np.array(all_embs)
        with open(pkl_path, "wb") as f:
            np.save(f, all_embs)
    with open(pkl_path, "rb") as f:
        all_embs = np.load(f, allow_pickle=True)
    return all_embs, file_names

def intra_group_similarity (
        working_dir: str,
        inspire_embs: np.ndarray,
        mutated_embs: np.ndarray,
        naive_embs: np.ndarray,
        game_name: str
    ):

    fig_path = os.path.join(working_dir, 'variations', game_name, "intra_similarity.png")
    # calculate the similarity matrix within each group
    inspire_sim_matrix = np.dot(inspire_embs, inspire_embs.T)
    mutated_sim_matrix = np.dot(mutated_embs, mutated_embs.T)
    naive_sim_matrix = np.dot(naive_embs, naive_embs.T)

    # keep the upper triangle only
    inspire_sim_matrix = np.triu(inspire_sim_matrix, k=1)
    mutated_sim_matrix = np.triu(mutated_sim_matrix, k=1)
    naive_sim_matrix = np.triu(naive_sim_matrix, k=1)

    # keep positive values only
    inspire_sim_matrix = inspire_sim_matrix[inspire_sim_matrix > 0]
    mutated_sim_matrix = mutated_sim_matrix[mutated_sim_matrix > 0]
    naive_sim_matrix = naive_sim_matrix[naive_sim_matrix > 0]

    import seaborn as sns
    import pandas as pd
    pd_data = pd.DataFrame({
        "naive": naive_sim_matrix.flatten(),
        "prompt_breeder": mutated_sim_matrix.flatten(),
        "inspired": inspire_sim_matrix.flatten(),
    })
    pd_data['game'] = game_name
    # use violin to show the distribution
    sns.violinplot(data=pd_data, density_norm='area', common_norm=True)
    # add title
    plt.title(f"Similarity distribution within {game_name} variations")
    plt.tight_layout()
    plt.savefig(fig_path)
    plt.clf()

    # expand the data where method is a column
    pd_data = pd_data.melt(id_vars=["game"], var_name="method", value_name="similarity")

    return pd_data

def inter_group_similarity(
        group_1_embeddings: np.ndarray,
        group_2_embeddings: np.ndarray,
        group_3_embeddings: np.ndarray,
        group_4_embeddings: np.ndarray

    ):
    naive_emb_np = np.concatenate([group_2_embeddings, group_4_embeddings])
    inspired_emb_np = np.concatenate([group_1_embeddings, group_3_embeddings])

    naive_sim_matrix = np.dot(naive_emb_np, naive_emb_np.T)
    inspired_sim_matrix = np.dot(inspired_emb_np, inspired_emb_np.T)

    # top-right tile mask to capture inter-group similarities
    mask = np.zeros_like(naive_sim_matrix)
    mask_size = naive_emb_np.shape[0]
    mask[:mask_size//2, mask_size//2:] = True

    # apply the mask
    naive_sim_matrix_between = naive_sim_matrix * mask
    inspired_sim_matrix_between = inspired_sim_matrix * mask

    # visualize the distribution of the two halves in one fig, ignoring the diagonal and zeros
    naive_sim_matrix_between = naive_sim_matrix_between[naive_sim_matrix_between > 0]
    inspired_sim_matrix_between = inspired_sim_matrix_between[inspired_sim_matrix_between > 0]
    import seaborn as sns
    import pandas as pd
    # use cdfplot to show the distribution
    pd_data = pd.DataFrame({
        "naive": naive_sim_matrix_between,
        "inspired": inspired_sim_matrix_between
    })
    sns.ecdfplot(data=pd_data, palette="Set2", 
                 legend=True)
    plt.savefig(f"naive_vs_ours_similarity_distribution.png")
    plt.clf()

    # t-test the average similarity of the two halves
    from scipy.stats import ttest_ind
    t_stat, p_val = ttest_ind(naive_sim_matrix_between, inspired_sim_matrix_between)
    print(f"t-statistic: {t_stat}, p-value: {p_val}")
    print(f"Mean similarity of the naive group: {np.mean(naive_sim_matrix_between)}")
    print(f"Mean similarity of the inspired group: {np.mean(inspired_sim_matrix_between)}")


def run_intra_similarity_eval(
        working_dir: str,
        overwrite_group1: bool = False,
        percentiles: list[float] | None = None
    ):
    import pandas as pd
    if percentiles is None:
        percentiles = [0.75, 0.5, 0.25, 0.05]

    game_variation_folder = os.path.join(working_dir, 'variations')

    all_pd_data = None
    for game_name in os.listdir(game_variation_folder):
        group_1_folder = os.path.join(working_dir, 'variations', game_name, "cardiverse")
        group_2_folder = os.path.join(working_dir, 'variations', game_name, "prompt_breeder")
        group_3_folder = os.path.join(working_dir, 'variations', game_name, "naive")
        group_1_embeddings, _ = read_all_embs(group_1_folder, overwrite=overwrite_group1)
        group_2_embeddings, _ = read_all_embs(group_2_folder)
        group_3_embeddings, _ = read_all_embs(group_3_folder)
        pd_data = intra_group_similarity(working_dir, group_1_embeddings, group_2_embeddings, group_3_embeddings, game_name)
        if all_pd_data is None:
            all_pd_data = pd_data
        else:
            all_pd_data = pd.concat([all_pd_data, pd_data])

    # exclude games where methods are not complete
    all_methods = all_pd_data['method'].unique()
    for game in all_pd_data['game'].unique():
        if len(all_pd_data[all_pd_data['game'] == game]['method'].unique()) != len(all_methods):
            all_pd_data = all_pd_data[all_pd_data['game'] != game]
            print(f"Excluding game {game} due to incomplete methods")

    for percentile in percentiles:
        # for each game and each method, get the top percentile of the similarity
        quantile_data = all_pd_data.groupby(['game', 'method']).quantile(percentile)

        # for each method, plot the distribution of the top percentile of similarity
        import seaborn as sns
        sns.violinplot(data=quantile_data, x='method', y='similarity', common_norm=True)
        plt.title(f"Top {percentile} percentile of similarity distribution")
        plt.tight_layout()
        plt.savefig(os.path.join(working_dir, f"intra_similarity_{percentile}.png"))
        plt.clf()

        # print the mean and std of the top percentile of similarity for each method, format: method, mean $\pm$ std
        print(f"Top {percentile} percentile of similarity distribution") 
        print(quantile_data.groupby('method').agg(['mean', 'std']))

        # expand quantile_data where method is a column
        quantile_data = quantile_data.reset_index()

        # conduct pairwise t-test between methods
        from scipy.stats import ttest_rel
        for method1 in quantile_data['method'].unique():
            for method2 in quantile_data['method'].unique():
                if method1 == method2:
                    continue
                data1 = quantile_data[quantile_data['method'] == method1]['similarity']
                data2 = quantile_data[quantile_data['method'] == method2]['similarity']
                t_stat, p_val = ttest_rel(data1, data2)
                print(f"t-statistic between {method1} and {method2}: {t_stat}, p-value: {p_val}")

    return all_pd_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate intra-group similarity among generated game variations."
    )
    parser.add_argument(
        "--working-dir",
        default="outputs/graph",
        help="Workspace directory that contains the variations folder.",
    )
    parser.add_argument(
        "--overwrite-group1-embs",
        action="store_true",
        help="Recompute embeddings for the cardiverse group instead of reusing cached embeddings.pkl.",
    )
    parser.add_argument(
        "--percentiles",
        type=float,
        nargs="+",
        default=[0.75, 0.5, 0.25, 0.05],
        help="Percentiles to summarize for each game and method.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_intra_similarity_eval(
        working_dir=args.working_dir,
        overwrite_group1=args.overwrite_group1_embs,
        percentiles=args.percentiles,
    )


if __name__ == "__main__":
    main()
