from ..base.base_task_descriptor import BaseTaskDescriptor
import numpy as np
import json


class EMTaskDescriptor(BaseTaskDescriptor):
    # decribe em task using natural language
    def __init__(self, topic="Entity", **kwargs):
        super().__init__(**kwargs)
        self.topic = topic
        self.entity_1, self.entity_2 = self.get_entity_names(
            random_state=self.random_state)

    def get_entity_names(self, random_state=None):
        pairs = [
            (f"{self.topic} A", f"{self.topic} B"),
            (f"{self.topic} 1", f"{self.topic} 2"),
            (f"{self.topic} I", f"{self.topic} II"),
            (f"the First {self.topic}", f"the Second {self.topic}"),
            (f"{self.topic} (1)", f"{self.topic} (2)"),
        ]
        return self.select_one_option(pairs, random_state=random_state)

    def _get_task_description(self, random_state=None):
        descriptions = [
#             f"""# Task Description: # Instruction: Entity matching (EM) is the task of identifying pairs of table records that refer to the same real-world entity.
 
# Given a table of interest, please first check all attributes in the table, and identify the real-world entity being represented in the table (e.g., it may be a sports team, a product, a restaurant, etc.). Then, identify the "essential information" for the type of entity that can usually be used to uniquely identify the entity, which are sometimes known as "keys" or "candidate keys" in database terminologies. For example, in a table of "restaurantes", ("restaurant name" and "zipcode") together can often be used to uniquely identify a real-world resturant, and therefore is a "candidate key". Similarly, "phone-number" can often be used to uniquely identify a real-world resturant (because no two different restaurants should share the same phone number), which is therefore also a "candidate key". Likewise, "full street address" is likely another "candidate key" (as no two restaurants should be located in the same address). In addition, please note that sometimes such uniquely identifying information of an entity may not be a standalone attribute, but may be embedded in an attribute -- for example, in a table of "products", the unique identifying information may be UPC code or Model Number (e.g., LAT1000AAE), which may appear within a long text field called "product description".
 
# The remaining "non-essential" attributes in the table may not be sufficient to uniquely identify a real-world entity (e.g., "price" of a product, "zipcode" of a restaurant, "authors" of a book, etc.), but can nevertheless be useful to determine whether two records cannot refer to the same a real-world entity (e.g., two restaurants with similar names but located in two different "zipcodes" cannot be the same real-world restaurant).
 
# In each example below, we will show a pair of entities, {self.entity_1} and {self.entity_2} as two rows from the same table. Please check if {self.entity_1} and {self.entity_2} can be considered as a "fuzzy match" or a "non match", defined as follows:
 
# (1) Definition of "fuzzy match": the two records in {self.entity_1} and {self.entity_2} are considered a "fuzzy match" if they refer to the same real-world entity, either because they share similar names that make us to conclude tha the two are the same, or because the two records share the same unique-identifying information or "candidate keys", (e.g., if two products having the same Model Number, or two resturants sharing the same phone-number, or two books sharing the same title and year of publication, etc.).
 
# - Note that two records can be considered a "fuzzy match", even if their "essential attributes"  have variations (e.g., abbreviation, typos, alternative names, and different token orders, etc.), as long as one can infer that the two records still refer to the same entity.
 
# - Also note that for "non-essential" attributes in the table, two records can have many more variations, and still be considered as a "fuzzy match" (e.g., "price" of $100 vs. $130 for two products from two different retailers, "revenue" of $100K vs. $108,389 which are quite close, "phone" of "425-800-8080" vs. "425.800.8080" which have format variations, etc.). Missing attribute values in "non-essential" attributes will also not affect two records from being considered a match (e.g., missing "price" information for a product, missing "year" information for a book, etc.).
 
 
# (2) Definition of "non match": the two records in {self.entity_1} and {self.entity_2} are considered a "non match", if they refer to a DIFFERENT real-world entity. This can either be because the unique identifying information (candidate keys) of the two records are clearly different (e.g., two products with different Model Numbers, or two restaurants with different phone-numbers), or because we can garner sufficient evidence from the non-identifying attributes that the two records must be different (e.g., two movies sharing the same name but released in different years, or two restaurants sharing the same name but located in two different states\/zipcodes).
 
 
# # Task: Please inspect the two records {self.entity_1} and {self.entity_2} below, and determine whether they are "fuzzy match" or not ("non match"), based on the definitions above. Your final answer should be 'Yes' or 'No' along with the probability that the two is a "fuzzy match" (from 0.0 to 1.0). Return the final result as JSON in the format {{"answer": "<Yes or No>", "probability": <PROB>}}.
 
# """,
            f"""Please determine whether {self.entity_1} and {self.entity_2} refer to the same entity or not. Your final answer should be 'Yes' or 'No' along with the probability that the answer is correct (0.0 to 1.0).""",
            f"Kindly ascertain whether {self.entity_1} and {self.entity_2} pertain to the identical entity or not. Provide your ultimate response as either 'Yes' or 'No'.",
            f"I request you to establish if {self.entity_1} and {self.entity_2} are referring to the same entity. State your final answer as 'Yes' or 'No'.",
            f"Please determine if {self.entity_1} and {self.entity_2} denote the same entity. Your conclusive answer should be 'Yes' or 'No'.",
            f"Could you confirm whether {self.entity_1} and {self.entity_2} point to the same entity or not? Indicate your final response as either 'Yes' or 'No'.",
            f"We need to establish if {self.entity_1} and {self.entity_2} represent the same entity. Provide your ultimate answer as 'Yes' or 'No'.",
            f"I would like you to determine whether {self.entity_1} and {self.entity_2} are referring to the same entity or not. Please respond with 'Yes' or 'No'.",
            f"It is essential to ascertain if {self.entity_1} and {self.entity_2} refer to the same entity. Your final response should be 'Yes' or 'No'.",
            f"Please verify whether {self.entity_1} and {self.entity_2} are denoting the same entity. Indicate your conclusive answer as either 'Yes' or 'No'.",
            f"Let's determine if {self.entity_1} and {self.entity_2} pertain to the same entity or not. Your ultimate answer should be 'Yes' or 'No'.",
            f"I request you to confirm whether {self.entity_1} and {self.entity_2} represent the same entity or not. Please respond with 'Yes' or 'No'.",
            f"Could you establish if {self.entity_1} and {self.entity_2} are referring to the same entity or not? Indicate your final response as either 'Yes' or 'No'.",
            f"We need to verify if {self.entity_1} and {self.entity_2} denote the same entity. Provide your ultimate answer as 'Yes' or 'No'.",
            f"I would like you to ascertain whether {self.entity_1} and {self.entity_2} are referring to the same entity or not. Your final response should be 'Yes' or 'No'.",
            f"It is crucial to determine if {self.entity_1} and {self.entity_2} represent the same entity. Indicate your conclusive answer as either 'Yes' or 'No'.",
            f"Please confirm whether {self.entity_1} and {self.entity_2} are denoting the same entity or not. Please respond with 'Yes' or 'No'.",
            f"Let's verify if {self.entity_1} and {self.entity_2} pertain to the same entity or not. Your ultimate answer should be 'Yes' or 'No'.",
            f"I request you to establish whether {self.entity_1} and {self.entity_2} represent the same entity or not. Indicate your final response as either 'Yes' or 'No'.",
            f"Could you determine if {self.entity_1} and {self.entity_2} are referring to the same entity or not? Provide your ultimate answer as 'Yes' or 'No'.",
            f"We need to ascertain if {self.entity_1} and {self.entity_2} denote the same entity. Your final response should be 'Yes' or 'No'.",
            f"I would like you to verify whether {self.entity_1} and {self.entity_2} are referring to the same entity or not. Your final response should be 'Yes' or 'No'.",
            f"Please determine whether {self.entity_1} and {self.entity_2} refer to the same entity or not. Your final answer should be 'Yes' or 'No'.",
            f"I request you to establish if {self.entity_1} and {self.entity_2} denote the same entity. State your final answer as 'Yes' or 'No'.",
            f"Could you confirm whether {self.entity_1} and {self.entity_2} point to the same entity or not? Indicate your final response as either 'Yes' or 'No'.",
            f"We need to establish if {self.entity_1} and {self.entity_2} represent the same entity. Provide your ultimate answer as 'Yes' or 'No'.",
            f"I would like you to determine whether {self.entity_1} and {self.entity_2} are referring to the same entity or not. Please respond with 'Yes' or 'No'.",
            f"It is essential to ascertain if {self.entity_1} and {self.entity_2} refer to the same entity. Your final response should be 'Yes' or 'No'.",
            f"Please verify whether {self.entity_1} and {self.entity_2} are denoting the same entity or not. Indicate your conclusive answer as either 'Yes' or 'No'.",
            f"Let's determine if {self.entity_1} and {self.entity_2} pertain to the same entity or not. Your ultimate answer should be 'Yes' or 'No'.",
            f"I request you to confirm whether {self.entity_1} and {self.entity_2} represent the same entity or not. Please respond with 'Yes' or 'No'.",
            f"Could you establish if {self.entity_1} and {self.entity_2} are referring to the same entity or not? Provide your ultimate answer as 'Yes' or 'No'.",
            f"We need to verify if {self.entity_1} and {self.entity_2} denote the same entity. Your final response should be 'Yes' or 'No'.",
            f"I would like you to ascertain whether {self.entity_1} and {self.entity_2} are referring to the same entity or not. Your final response should be 'Yes' or 'No'.",
            f"It is crucial to determine if {self.entity_1} and {self.entity_2} represent the same entity. Indicate your conclusive answer as either 'Yes' or 'No'.",
            f"Please confirm whether {self.entity_1} and {self.entity_2} are denoting the same entity or not. Please respond with 'Yes' or 'No'.",
            f"Let's verify if {self.entity_1} and {self.entity_2} pertain to the same entity or not. Your ultimate answer should be 'Yes' or 'No'.",
            f"I request you to establish whether {self.entity_1} and {self.entity_2} represent the same entity or not. Indicate your final response as either 'Yes' or 'No'.",
            f"Could you determine if {self.entity_1} and {self.entity_2} are referring to the same entity or not? Provide your ultimate answer as 'Yes' or 'No'.",
            f"We need to ascertain if {self.entity_1} and {self.entity_2} denote the same entity. Your final response should be 'Yes' or 'No'.",
            f"I would like you to verify whether {self.entity_1} and {self.entity_2} are referring to the same entity or not. Your final response should be 'Yes' or 'No'.",
            f"It is essential to determine if {self.entity_1} and {self.entity_2} refer to the same entity. Indicate your conclusive answer as either 'Yes' or 'No'.",
            f"Please verify whether {self.entity_1} and {self.entity_2} are denoting the same entity or not. Please respond with 'Yes' or 'No'.",
            f"Let's determine if {self.entity_1} and {self.entity_2} pertain to the same entity or not. Your ultimate answer should be 'Yes' or 'No'.",
            f"I request you to confirm whether {self.entity_1} and {self.entity_2} represent the same entity or not. Please respond with 'Yes' or 'No'.",
            f"Could you establish if {self.entity_1} and {self.entity_2} are referring to the same entity or not? Provide your ultimate answer as 'Yes' or 'No'.",
            f"We need to verify if {self.entity_1} and {self.entity_2} denote the same entity. Your final response should be 'Yes' or 'No'.",
        ]
        return self.select_one_option(descriptions, random_state=random_state)

    def get_input_suffix(self, name, random_state=None):
        suffix = [
            f"{name} is:",
            f"{name} can be described as:",
            f"{name} is shown as:",
            f"{name} can be represented as:",
            f"{name}:",
            f"{name} can be presented as follows.",
            f"Here is the description of {name}.",
            f"The below table depicts {name}.",
            f"The following table provides details of {name}.",
        ]
        return self.select_one_option(suffix, random_state=random_state)

    def get_input(self, data, random_state=None):
        row_l, row_r = data
        l_text = self.serializer.serialize_row(row_l)
        r_text = self.serializer.serialize_row(row_r)

        if random_state is not None:
            np.random.seed(random_state)
        suffix_1 = self.get_input_suffix(self.entity_1, random_state=None)
        suffix_2 = self.get_input_suffix(self.entity_2, random_state=None)

        text = (
            f"{suffix_1}\n"
            f"{l_text}\n"
            f"{suffix_2}\n"
            f"{r_text}"
        )
        return text

    def get_output_example(self):
        return "answer", "<Yes or No>", "probability", "<PROB>"

    def add_format_suffix(self, desc):
        _, ans1, _, ans2 = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        text = f"""{desc}Return the final result as JSON in the format {self.answer_to_json(ans1, ans2)}."""
        # text = f"""{desc}Please inspect the two records {self.entity_1} and {self.entity_2} above, and determine whether they are "fuzzy match" or not ("non match"). Return the final result as JSON in the format {self.answer_to_json(ans1, ans2)}."""
        return text

    def answer_to_json(self, answer_1, answer_2):
        key1, _, key2, _ = self.get_output_example()
        return json.dumps({key1: answer_1, key2: answer_2})

    def get_output(self, y):
        if y["label"] == "1":
            answer = "Yes"
        elif y["label"] == "0":
            answer = "No"
        else:
            raise Exception(f"invalid label {y['label']}")

        answer = self.answer_to_json(answer, y['probability'])

        if y["cot"] is not None:
            cot_text = y["cot"].strip()

            if cot_text[-1] != ".":
                cot_text += "."

            cot_text = cot_text.replace(f"{self.topic} A", self.entity_1).replace(
                f"{self.topic} B", self.entity_2)
            if y["cot_position"] == "before_answer":
                completion = f"{cot_text} Therefore, the final answer is {answer}."
            elif y["cot_position"] == "after_answer":
                completion = f"{answer}. {cot_text}"
            else:
                raise Exception(f"Wrong cot position {y['cot_position']}")
        else:
            completion = answer

        return completion
