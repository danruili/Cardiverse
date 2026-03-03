import os
import numpy as np
import pandas as pd
from Utils.LLMHandler import LLMHandler
import matplotlib.pyplot as plt
from GameIdea.evaluation.sim_within import read_all_md, read_all_embs
import argparse

def similarity_to_db(
        game_name: str,
        working_dir: str,
        db_embeddings: np.ndarray,
        game_names: list[str],
        
        ):
    group_1_folder = os.path.join(working_dir, 'variations', game_name, "cardiverse")
    group_2_folder = os.path.join(working_dir, 'variations', game_name, "prompt_breeder")
    group_3_folder = os.path.join(working_dir, 'variations', game_name, "naive")
    fig_path = os.path.join(working_dir, 'variations', game_name, f"{game_name}_similarity_to_db.png")

    group_1_embeddings, group_1_file_names = read_all_embs(group_1_folder)
    group_2_embeddings, _ = read_all_embs(group_2_folder)
    group_3_embeddings, _ = read_all_embs(group_3_folder)

    quantile_index = 1
    # print(f"Quantile index: {quantile_index}")
    exclude_id = 0
    for i, name in enumerate(game_names):
        if name == game_name+".md":
            exclude_id = i
            break

    # for each entry in group 1, calculate the similarity with all entries in db_embeddings
    sim_matrix_group1 = np.dot(group_1_embeddings, db_embeddings.T)
    # mask the similarity with the same game
    sim_matrix_group1[:, exclude_id] = -1
    # get the max similarity for each entry in group 1
    max_sim_group1 = np.sort(sim_matrix_group1, axis=1)[:, -quantile_index]
    # get the smallest index in max_sim_group1
    min_index = np.argmin(max_sim_group1)
    # print(f"Least similar entry in group 1: {group_1_file_names[min_index]}")
    # print(f"Its cosine similarity: {max_sim_group1[min_index]}")
    # copy this entry to "candidate" in the working directory, create the folder if not exists
    candidate_folder = os.path.join(working_dir, 'candidate')
    if not os.path.exists(candidate_folder):
        os.makedirs(candidate_folder)
    with open(os.path.join(candidate_folder, f"{game_name}_variation.md"), "w", encoding="utf-8") as f:
        with open(os.path.join(group_1_folder, group_1_file_names[min_index]), "r", encoding="utf-8") as f2:
            f.write(f2.read())

    # for each entry in group 2, calculate the similarity with all entries in db_embeddings
    sim_matrix_group2 = np.dot(group_2_embeddings, db_embeddings.T)
    sim_matrix_group2[:, exclude_id] = -1
    max_sim_group2 = np.sort(sim_matrix_group2, axis=1)[:, -quantile_index]

    # for each entry in group 3, calculate the similarity with all entries in db_embeddings
    sim_matrix_group3 = np.dot(group_3_embeddings, db_embeddings.T)
    sim_matrix_group3[:, exclude_id] = -1
    max_sim_group3 = np.sort(sim_matrix_group3, axis=1)[:, -quantile_index]

    # use swarm plot to show the similarity distribution between group 1 and group 2
    import pandas as pd
    df = pd.DataFrame({
        'Method':  ['Naive']*len(max_sim_group3) + ['PromptBreeder']*len(max_sim_group2) + ['Ours']*len(max_sim_group1),
        'Cosine Similarity': list(max_sim_group3) + list(max_sim_group2) + list(max_sim_group1),
        'game': [game_name]*(len(max_sim_group3)+len(max_sim_group2)+len(max_sim_group1))
    })
    import seaborn as sns
    sns.violinplot(x='Method', y='Cosine Similarity', data=df, palette="Set2", common_norm=True, hue='Method')
    # add title
    plt.title(f"Maximum similarities between {game_name} variations and db")
    plt.tight_layout()
    plt.savefig(fig_path)
    plt.clf()

    return df

def eval_all_sim_to_db(
        working_dir: str,
        db_desc_folder: str
    ):
    db_emb_path = os.path.join(working_dir, "db_desc_embeddings.pkl")

    # read all the descriptions from md files
    db_descs, game_names = read_all_md(db_desc_folder)
    if not os.path.exists(db_emb_path):
        llm_handler = LLMHandler()
        db_embeddings = llm_handler.get_text_embeddings_multi(db_descs)
        db_embeddings = np.array(db_embeddings)
        # save embeddings to pkl file
        with open(db_emb_path, "wb") as f:
            np.save(f, db_embeddings)
    else:
        with open(db_emb_path, "rb") as f:
            db_embeddings = np.load(f, allow_pickle=True)

    # iterate over all games in variations folder
    folder_path = os.path.join(working_dir, 'variations')
    result_dfs = []
    for game_name in os.listdir(folder_path):
        # print(f"Processing game {game_name}...")
        df = similarity_to_db(game_name, working_dir, db_embeddings, game_names)
        result_dfs.append(df)

    # concatenate all the dataframes
    result_df = pd.concat(result_dfs)
    result_df.to_csv(os.path.join(working_dir, "similarity_to_db.csv"), index=False)

    return result_df

def run_similarity_to_db_eval(
        working_dir: str,
        db_desc_folder: str,
        quantile: float = 0.5
    ):

    result_df = eval_all_sim_to_db(working_dir, db_desc_folder)

    # for each game and each method, calculate the median similarity
    # calculate the quantile of the similarity
    quantile_df = result_df.groupby(['game', 'Method']).quantile(quantile)
    metric_df = quantile_df
    
    import seaborn as sns
    sns.set_palette("Set2")
    fig, ax = plt.subplots(figsize=(5, 2.5))

    # draw line plot for median similarity for each method
    # connect the dots for the same game
    print(len(metric_df.index.levels[0]))
    line_styles = ['-', '--', '-.', ':',]
    for game in metric_df.index.levels[0]:
        game_df = metric_df.loc[game]
        # set game_df index order
        game_df = game_df.reindex(['Naive', 'PromptBreeder', 'Ours'])
        ax.plot(game_df.index, game_df['Cosine Similarity'], label=game, marker='o', 
                markersize=3, linewidth=0.7, linestyle=line_styles[metric_df.index.levels[0].get_loc(game) % len(line_styles)])

    # draw box plot for the similarity, no fill color
    sns.boxplot(x='Method', y='Cosine Similarity', data=metric_df, ax=ax, color='black', linewidth=1.2,
                order=['Naive', 'PromptBreeder', 'Ours'], width=0.3, fill=False)

    
    # hide legend
    ax.legend_.remove()

    ax.set_ylabel("Cosine Similarity")
    ax.set_xlabel(None)
    # ax.set_title("Median Max Similarity between Variations and DB")
    plt.tight_layout()
    plt.savefig(os.path.join(working_dir, "median_similarity_to_db.png"), dpi=300)
    plt.clf()

    # print mean and std of the median similarity
    print(metric_df.groupby('Method').mean())
    print(metric_df.groupby('Method').std())
    
    # conduct paired t-test for the median similarity, paired by game
    from scipy.stats import ttest_rel
    inspired = metric_df.loc[(slice(None), 'Ours'), 'Cosine Similarity'].unstack()
    mutated = metric_df.loc[(slice(None), 'PromptBreeder'), 'Cosine Similarity'].unstack()
    naive = metric_df.loc[(slice(None), 'Naive'), 'Cosine Similarity'].unstack()

    # test if they are normally distributed
    from scipy.stats import shapiro
    print("Shapiro-Wilk test for normality")
    print("Inspired:", shapiro(inspired))
    print("Mutated:", shapiro(mutated))
    print("Naive:", shapiro(naive))

    t_stat1, p_value1 = ttest_rel(inspired, mutated)
    t_stat2, p_value2 = ttest_rel(inspired, naive)
    t_stat3, p_value3 = ttest_rel(mutated, naive)
    print(f"paired t-statistic between inspired and mutated: {t_stat1}, p-value: {p_value1}")
    print(f"paired t-statistic between inspired and naive: {t_stat2}, p-value: {p_value2}")
    print(f"paired t-statistic between mutated and naive: {t_stat3}, p-value: {p_value3}")

    # calculate paired wilcoxon signed rank test
    from scipy.stats import wilcoxon
    wilcoxon_stat1, wilcoxon_p1 = wilcoxon(inspired, mutated)
    wilcoxon_stat2, wilcoxon_p2 = wilcoxon(inspired, naive)
    wilcoxon_stat3, wilcoxon_p3 = wilcoxon(mutated, naive)
    print(f"Wilcoxon signed rank test between inspired and mutated: {wilcoxon_stat1}, p-value: {wilcoxon_p1}")
    print(f"Wilcoxon signed rank test between inspired and naive: {wilcoxon_stat2}, p-value: {wilcoxon_p2}")
    print(f"Wilcoxon signed rank test between mutated and naive: {wilcoxon_stat3}, p-value: {wilcoxon_p3}")

    # for each game, calculate the difference between inspired and mutated, only keep the common items
    common_games = set(inspired.index) & set(mutated.index)
    common_games = list(common_games)
    common_inspired = inspired.loc[common_games]["Ours"]
    common_mutated = mutated.loc[common_games]["PromptBreeder"]
    diff_df = common_inspired - common_mutated

    # draw a bar plot for the difference
    # create a tall figure
    fig, ax = plt.subplots(figsize=(7, 7))
    # horizontal bar plot
    ax.barh(common_games, diff_df.values)
    ax.set_xlabel("Reduced Cosine Similarity by our method")
    ax.set_ylabel("Game")
    plt.tight_layout()
    plt.savefig(os.path.join(working_dir, "inspiration_diff.png"))
    plt.clf()

    return metric_df


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate maximum similarity of game variations against database game descriptions."
    )
    parser.add_argument(
        "--working-dir",
        default="outputs/graph",
        help="Workspace directory that contains variations/ and stores output artifacts.",
    )
    parser.add_argument(
        "--db-desc-folder",
        default="data/game_ideation/examples",
        help="Folder containing database .md game descriptions used to build/load embeddings.",
    )
    parser.add_argument(
        "--quantile",
        type=float,
        default=0.5,
        help="Quantile to summarize per-game method similarity (e.g., 0.5 for median).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_similarity_to_db_eval(
        working_dir=args.working_dir,
        db_desc_folder=args.db_desc_folder,
        quantile=args.quantile,
    )


if __name__ == "__main__":
    main()
