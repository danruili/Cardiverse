from GameIdea.llm_op.prompt_v2 import PROMPTS
from Utils.LLMHandler import LLMHandler, ChatSequence, Message
from GameCode.utils.formatting import extract_from_json
import json5
from retrying import retry
import random


def parse_one_entity(entity: str) -> dict:
    entity = extract_from_json(entity)
    entity_dict = json5.loads(entity)
    return entity_dict


@retry(stop_max_attempt_number=3)
def chat_and_parse_with_retry(llm_handler: LLMHandler, chat_seq):
    response = llm_handler.chat(chat_seq)
    dict_response = parse_one_entity(response)
    return dict_response, response  # return both dict and string response

def summarize_and_variate_concept(
        instances: str,
        llm_handler: LLMHandler,
        entity_num: int = 6
    ) -> tuple[dict, list[dict]]:

    entities = []

    prefix_prompts_path = "GameIdea/llm_op/mutated_design_prompts.json"
    # load prefix prompts
    with open(prefix_prompts_path, "r", encoding="utf-8") as f:
        prefix_prompts = json5.load(f)
    # randomly sample a prefix prompt
    prefix_prompt = random.choice(prefix_prompts)

    # summarize the concept
    prompt = PROMPTS["instance_summary"].replace("{input_text}", instances)
    chat_seq = ChatSequence()
    chat_seq.append(Message('user', prompt))
    abstraction, response = chat_and_parse_with_retry(llm_handler, chat_seq)
    chat_seq.append(Message('assistant', response))

    # design more concepts
    prompt = PROMPTS["entity_design"].replace("{prefix_prompt}", prefix_prompt)
    chat_seq.append(Message('user', prompt))
    entity, response = chat_and_parse_with_retry(llm_handler, chat_seq)
    entities.append(entity)

    # add more attempts
    for _ in range(entity_num-1):
        chat_seq.append(Message('assistant', response))
        chat_seq.append(Message('user', PROMPTS["entity_continue_design"]))
        entity, response = chat_and_parse_with_retry(llm_handler, chat_seq)
        entities.append(entity)
    chat_seq.append(Message('assistant', response))

    return abstraction, entities


def concept_breed_in_between(
        theme: str,
        instances: str,
        llm_handler: LLMHandler,
    ) -> tuple[dict, list[dict]]:

    prefix_prompts_path = "GameIdea/llm_op/mutated_design_prompts.json"
    # load prefix prompts
    with open(prefix_prompts_path, "r", encoding="utf-8") as f:
        prefix_prompts = json5.load(f)
    # randomly sample a prefix prompt
    prefix_prompt = random.choice(prefix_prompts)

    # summarize the concept
    prompt = PROMPTS["instance_summary_in_between"].replace("{input_text}", instances).replace("{theme}", theme)
    chat_seq = ChatSequence()
    chat_seq.append(Message('user', prompt))
    abstraction, response = chat_and_parse_with_retry(llm_handler, chat_seq)
    chat_seq.append(Message('assistant', response))

    # get variations
    entities = []
    for category in abstraction['category']:
        category_description = category['description']
        chat_seq.append(Message('user', PROMPTS["entity_design_in_between"]\
                .replace("{prefix_prompt}", prefix_prompt)\
                .replace("{category}", category_description)\
                .replace("{theme}", theme)))
        entity, response = chat_and_parse_with_retry(llm_handler, chat_seq)
        entities.append(entity)
        chat_seq.pop()

    return abstraction, entities


