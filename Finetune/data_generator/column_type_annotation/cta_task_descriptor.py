from ..base.base_task_descriptor import BaseTaskDescriptor
import json


class CTATaskDescriptor(BaseTaskDescriptor):
    def _get_task_description(self, random_state=None):
        # description = "Please look at the input column and determine the semantic type that can describe *every single* instance the input column. Please only choose one semantic type from the candidate list, and remember that the type you choose has to accurately describe every single entity in the column. If no candidate column type can suitably describe every single instance in the column, please return 'None'. Please only choose one type from the candidate list below, and *do not* create new types."
        description = """Your task is annotate a target column with column name"<TARGET>" in a table with a semantic type, where the semantic type of this "<TARGET>" column can be classified as <TYPE> (e.g., address, city, age, etc.).
 
The semantic type <TYPE> should be drawn from one of the 78 column types below: 
["address", "affiliate", "affiliation", "age", "album", "area", "artist", "birth date", "birth place", "brand", "capacity", "category", "city", "class", "classification", "club", "code", "collection", "command", "company", "component", "continent", "country", "county", "creator", "credit", "currency", "day", "depth", "description", "director", "duration", "education", "elevation", "family", "file Size", "format", "gender", "genre", "grades", "industry", "isbn", "jockey", "language", "location", "manufacturer", "name", "nationality", "notes", "operator", "order", "organisation", "origin", "owner", "person", "plays", "position", "product", "publisher", "range", "rank", "ranking", "region", "religion", "requirement", "result", "sales", "service", "sex", "species", "state", "status", "symbol", "team", "team name", "type", "weight", "year"]

Provide your best guess for the semantic type <TYPE> of the "<TARGET>" column in the table and the probability that the <TYPE> is correct (0.0 to 1.0). Return the final result in the following format: {"type": "<TYPE>", "probability": <PROB>}. If you are not sure about the semantic type, you can return the following format: {"type": "None", "probability": <PROB>}.


"""
        return description

    def get_task_description(self, random_state):
        desc = self._get_task_description(random_state=random_state)
        if self.use_format_suffix:
            desc = self.add_format_suffix(desc)
        if self.use_cot:
            desc += "  Let's think step by step and show your reasoning before showing the final result."
        return desc

    def get_input(self, data, random_state=None):
        df, candidate_text = data
        # candidate_text = "\n".join(candidate_text)

        prompt = (
            "**Table:**\n"
            f"{self.serializer.serialize_df(df)}\n"
        )
        return prompt

    def get_output_example(self):
        return "type", "<TYPE>", "probability", "<PROB>"

    def add_format_suffix(self, desc):
        _, ans1, _, ans2 = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        text = f"{desc}Return the final result as JSON in the format {self.answer_to_json(ans1, ans2)}."
        return text

    def _get_output(self, y, prob):
        if y is None:
            return "None", prob
        else:
            return y[0], prob

    def get_output(self, y, prob):
        answer_1, answer_2 = self._get_output(y, prob)
        return self.answer_to_json(answer_1, answer_2)

    def answer_to_json(self, answer_1, answer_2):
        key1, _, key2, _ = self.get_output_example()
        return json.dumps({key1: answer_1, key2: answer_2})


class CTATaskDescriptorTest(CTATaskDescriptor):
    def _get_task_description(self, random_state=None):
        # description = "Please look at the input column and determine the semantic type that can describe *every single* instance the input column. Please only choose one semantic type from the candidate list, and remember that the type you choose has to accurately describe every single entity in the column. If no candidate column type can suitably describe every single instance in the column, please return 'None'. Please only choose one type from the candidate list below, and *do not* create new types."
        description = """Your task is annotate a target column with column name"<TARGET>" in a table with a semantic type, where the semantic type of this "<TARGET>" column can be classified as <TYPE> (e.g., address, city, age, etc.).
 
The semantic type <TYPE> should be drawn from one of the 78 column types below: 
["address", "affiliate", "affiliation", "age", "album", "area", "artist", "birth date", "birth place", "brand", "capacity", "category", "city", "class", "classification", "club", "code", "collection", "command", "company", "component", "continent", "country", "county", "creator", "credit", "currency", "day", "depth", "description", "director", "duration", "education", "elevation", "family", "file Size", "format", "gender", "genre", "grades", "industry", "isbn", "jockey", "language", "location", "manufacturer", "name", "nationality", "notes", "operator", "order", "organisation", "origin", "owner", "person", "plays", "position", "product", "publisher", "range", "rank", "ranking", "region", "religion", "requirement", "result", "sales", "service", "sex", "species", "state", "status", "symbol", "team", "team name", "type", "weight", "year"]

Provide your best guess for the semantic type <TYPE> of the "<TARGET>" column in the table and the probability that the <TYPE> is correct (0.0 to 1.0). Return the final result in the following format: {"type": "<TYPE>", "probability": <PROB>}.


"""
        return description
