import os
import json
import argparse
from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from GameIdea.ideation.get_inspiration import get_inspiration_prompts_for_game
from GameCode.utils.structure_description import extract_from_language, structurize_description
import threading
from retrying import retry


GAME_MUTATION_PROMPT_CORE = """You are a good card game designer, and you are asked to mutate a given card game description."""

GAME_MUTATION_PROMPT_INS = """
{core_prompt}
- You should incorporate the given inspiration into the given game.
- Make sure the new logic is coherent with the original game.
- Reply in compelete description of the game.
- You should only change one single part of the logic.
- Only modify the necessary parts of the game, retaining as much of the original game as possible.
- Wrap your answer in a markdown block.

# Game Description
{game_description}

# Inspiration Prompt
{instruction_prompt}
"""

GAME_MUTATION_PROMPT = """
{core_prompt}
- Reply in compelete description of the game.
- You should only change one single part of the logic.
- Only modify the necessary parts of the game, retaining as much of the original game as possible.
- Wrap your answer in a markdown block.

# Game Description
{game_description}
"""

REFLECT_PROMPT = """Critically analysis if there is any unclear or self-conflicting part in the game description"""

REFINE_PROMPT = """Based on the reflection, refine the game description. Follow the same format as the your previous response."""

@retry(stop_max_attempt_number=3)
def mutate_with_instruction(
        core_prompt: str,
        game_description: str,
        instruction: str,
        llm_handler: LLMHandler
        ):
    if not instruction or (len(instruction) < 10):
        mutate_prompt = GAME_MUTATION_PROMPT.format(
        core_prompt=core_prompt,
        game_description=game_description
        )
    else:
        mutate_prompt = GAME_MUTATION_PROMPT_INS.format(
            core_prompt=core_prompt,
            game_description=game_description,
            instruction_prompt=instruction
        )
    chat_seq = ChatSequence()
    chat_seq.append(Message("system", mutate_prompt))
    response = llm_handler.chat(chat_seq)
    mutated_game_description = extract_from_language(response, "markdown")
    structured_desc = structurize_description(mutated_game_description, llm_handler)
    if len(structured_desc) < 1000:
        print(f"The mutated game description is too short: {len(structured_desc)}")
        raise ValueError("The mutated game description is too short")
    chat_seq.append(Message("assistant", structured_desc))
    chat_seq.append(Message("user", REFLECT_PROMPT))
    response = llm_handler.chat(chat_seq)
    chat_seq.append(Message("assistant", response))
    chat_seq.append(Message("user", REFINE_PROMPT))
    response = llm_handler.chat(chat_seq)
    refined_desc = extract_from_language(response, "markdown")
    return refined_desc

def mutate_and_save(core_prompt, game_description, instruction, llm_handler, target_folder, game_name, index):
    new_desc = mutate_with_instruction(core_prompt, game_description, instruction, llm_handler)
    with open(os.path.join(target_folder, f"{game_name}_{index}.md"), "w", encoding="utf-8") as f:
        f.write(new_desc)

def mutate_game(
        working_dir,
        source_desc_folder,
        game_name,
        llm_handler,
        core_prompt_mutated_path="GameIdea/llm_op/mutated_game_prompts.json",
        parallel_llm_call_limit=20,
        source_desc_ext=".md",
    ):
    """
    Create variations of a game description by various methods: Inspired mutation, prompt-breeded mutation, and naive mutation.
    """

    # get game description
    game_desc_path = os.path.join(source_desc_folder, f"{game_name}{source_desc_ext}")
    with open(game_desc_path, "r", encoding="utf-8") as f:
        game_description = f.read()

    # load core prompts
    with open(core_prompt_mutated_path, "r", encoding="utf-8") as f:
        core_prompts = json.load(f)

    # mutate the game with inspiration
    print(f"Mutating game {game_name} using Cardiverse...")
    inspirations = get_inspiration_prompts_for_game(working_dir, game_name)
    if len(inspirations) > 0:
        target_folder = os.path.join(working_dir, 'variations', game_name, "cardiverse")
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        threads = []
        for i, core_prompt in enumerate(core_prompts):
            prompt = inspirations[i % len(inspirations)]
            t = threading.Thread(target=mutate_and_save, args=(core_prompt, game_description, prompt, llm_handler, target_folder, game_name, i))
            threads.append(t)
        for i in range(0, len(threads), parallel_llm_call_limit):
            for t in threads[i:i+parallel_llm_call_limit]:
                t.start()
            for t in threads[i:i+parallel_llm_call_limit]:
                t.join()

    # mutate the game with prompt variation
    print(f"Mutating game {game_name} using PromptBreeder...")
    target_folder = os.path.join(working_dir, 'variations', game_name, "prompt_breeder")
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    threads2 = []
    for i, core_prompt in enumerate(core_prompts):
        t = threading.Thread(target=mutate_and_save, args=(core_prompt, game_description, None, llm_handler, target_folder, game_name, i))
        threads2.append(t)
    for i in range(0, len(threads2), parallel_llm_call_limit):
        for t in threads2[i:i+parallel_llm_call_limit]:
            t.start()
        for t in threads2[i:i+parallel_llm_call_limit]:
            t.join()

    # mutate the game naively
    print(f"Mutating game {game_name} naively...")
    target_folder = os.path.join(working_dir, 'variations', game_name, "naive")
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    threads3 = []
    for i in range(len(core_prompts)):
        t = threading.Thread(target=mutate_and_save, 
                             args=(GAME_MUTATION_PROMPT_CORE, game_description, None, llm_handler, target_folder, game_name, i))
        threads3.append(t)
    for i in range(0, len(threads3), parallel_llm_call_limit):
        for t in threads3[i:i+parallel_llm_call_limit]:
            t.start()
        for t in threads3[i:i+parallel_llm_call_limit]:
            t.join()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mutate game descriptions with inspired and baseline prompts."
    )
    parser.add_argument(
        "--working-dir",
        default="outputs/graph",
        help="Working directory containing graph data and output variations.",
    )
    parser.add_argument(
        "--source-desc-folder",
        default="data/game_ideation/examples",
        help="Folder containing source game description files.",
    )
    parser.add_argument(
        "--source-desc-ext",
        default=".md",
        help="File extension of source game descriptions (e.g. .md, .txt).",
    )
    parser.add_argument(
        "--game-name",
        default=None,
        help="Single game name to mutate. If omitted, all files in source folder are processed.",
    )
    parser.add_argument(
        "--llm-model",
        "--llm_model",
        dest="llm_model",
        default="gpt-4o-2024-08-06",
        help="LLM model used for mutation.",
    )
    parser.add_argument(
        "--core-prompts-path",
        default="GameIdea/llm_op/mutated_game_prompts.json",
        help="JSON file containing mutation core prompts.",
    )
    parser.add_argument(
        "--parallel-llm-call-limit",
        type=int,
        default=20,
        help="Max number of concurrent mutation calls per batch.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing variation folders. By default, existing games are skipped.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    llm_handler = LLMHandler(llm_model=args.llm_model)

    if args.game_name:
        mutate_game(
            working_dir=args.working_dir,
            source_desc_folder=args.source_desc_folder,
            game_name=args.game_name,
            llm_handler=llm_handler,
            core_prompt_mutated_path=args.core_prompts_path,
            parallel_llm_call_limit=args.parallel_llm_call_limit,
            source_desc_ext=args.source_desc_ext,
        )
        return

    for file in sorted(os.listdir(args.source_desc_folder)):
        if not file.endswith(args.source_desc_ext):
            continue
        game_name = os.path.basename(file)[: -len(args.source_desc_ext)]
        variation_dir = os.path.join(args.working_dir, "variations", game_name)
        if (not args.overwrite) and os.path.exists(variation_dir):
            continue
        mutate_game(
            working_dir=args.working_dir,
            source_desc_folder=args.source_desc_folder,
            game_name=game_name,
            llm_handler=llm_handler,
            core_prompt_mutated_path=args.core_prompts_path,
            parallel_llm_call_limit=args.parallel_llm_call_limit,
            source_desc_ext=args.source_desc_ext,
        )


if __name__ == "__main__":
    main()
