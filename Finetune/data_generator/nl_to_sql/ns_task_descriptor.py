from ..base.base_task_descriptor import BaseTaskDescriptor

class NSTaskDescriptor(BaseTaskDescriptor):
    def _get_task_description(self, random_state=None):
        descriptions = [
"""Natural language to SQL, also known as NL2SQL, is the problem of generating a SQL query that can be executed on a input table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate an SQL query that can be executed on the input table to answer the question.

Please ensure that the generated SQL only return relevant columns being specifically asked in the question (e.g., in SQL please don't return more than one columns in SELECT if only one column is needed to answer the given question, and similarly please refrain from using SELECT * unless the entire row is needed to answer the question).
 
When generating SQL code, please use the SQLite syntax to ensure that your SQL is executable on SQLite3. Use only columns that are present in the table, always use quotes around your column and table names (some column names have punctuation or special characters), and refer to the columns using the column-names exactly as they appear in the table, do not add or remove punctuation (underscore, slash, etc.)

""",
#====================================================
"""Natural Language to SQL (NL2SQL) is about generating a SQL query from a natural language question that can be executed on a given table.

You will receive a table called "table" in markdown format and a question. Your goal is to write an SQL query that answers the question using the input table.

Ensure the generated SQL query only includes the columns directly needed for the answer. For example, if the question requires one column, do not return multiple columns in the SELECT statement. Avoid using SELECT * unless the entire row is necessary.

Use SQLite syntax for the SQL query to ensure compatibility with SQLite3. Only use columns available in the table, always enclose column and table names in quotes, and refer to the columns exactly as they appear in the table, maintaining all punctuation and special characters.

""",
"""
NL2SQL involves translating a natural language question into a SQL query that can be executed on a specified table.

You will be provided with a table named "table" in markdown format and a question. Your task is to generate a SQL query that, when executed on the input table, answers the question.

Ensure the SQL query only includes the columns explicitly needed to answer the question. For instance, if only one column is required, do not include more columns in the SELECT statement. Avoid using SELECT * unless the full row is necessary.

Write the SQL query in SQLite syntax to ensure it runs on SQLite3. Use only the columns present in the table, always put quotes around column and table names, and use the column names exactly as they appear in the table without altering any punctuation or special characters.

""",
"""
NL2SQL refers to creating a SQL query from a natural language question that can be executed on a provided input table.

You will receive a table named "table" in markdown format along with a question. Your task is to create an SQL query that, when run on the input table, answers the question.

Make sure the SQL query only returns the columns specifically asked for in the question. For example, if only one column is needed, do not return multiple columns. Avoid using SELECT * unless the entire row is required.

Generate the SQL code using SQLite syntax to ensure it is executable on SQLite3. Use only the columns present in the table, always enclose column and table names in quotes, and refer to the columns exactly as they appear in the table, without modifying punctuation or special characters.

""",

            """NL2SQL is the task of converting a natural language question into a SQL query that can be executed on a provided table.

You will be given a table named "table" in markdown format and a question. Your task is to create a SQL query that answers the question when run on the input table.

Make sure the SQL query only includes the columns specifically requested in the question. For instance, if only one column is needed, do not return additional columns. Avoid using SELECT * unless the question requires all columns.

Write the SQL query using SQLite syntax to ensure it can be executed on SQLite3. Use only the columns present in the table, always enclose column and table names in quotes, and use the column names exactly as they appear in the table, without altering punctuation or special characters.

""",
#====================================================
            """Natural language to SQL, also known as NL2SQL, is the problem of generating a SQL query that can be executed on a input table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate an SQL query that can be executed on the input table to answer the question.

Please ensure that the generated SQL only return relevant columns being specifically asked in the question (e.g., in SQL please don't return more than one columns in SELECT if only one column is needed to answer the given question, and similarly please refrain from using SELECT * unless the entire row is needed to answer the question).
 
When generating SQL code, please use the SQLite syntax to ensure that your SQL is executable on SQLite3. Use only columns that are present in the table, always use quotes around your column and table names (some column names have punctuation or special characters), and refer to the columns using the column-names exactly as they appear in the table, do not add or remove punctuation (underscore, slash, etc.)

Please first think of an almost correct, but still incorrect SQL for this question first, output as [INCORRECT] folowed by a ```sql<SQL CODE>``` markdown code block, explain why this is likely incorrect, and then produce a correct SQL for this question, as [CORRECT] followed by a ```sql<SQL CODE>``` code block.

If you cannot think of any almost correct but still incorrect SQL for this question, just output [CORRECT] followed by a ```sql<SQL CODE>``` code block.

""",
            """Natural language to SQL, also known as NL2SQL, is the problem of generating a SQL query that can be executed on a input table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate an SQL query that can be executed on the input table to answer the question.

Please ensure that the generated SQL only return relevant columns being specifically asked in the question (e.g., in SQL please don't return more than one columns in SELECT if only one column is needed to answer the given question, and similarly please refrain from using SELECT * unless the entire row is needed to answer the question).
 
When generating SQL code, please use the SQLite syntax to ensure that your SQL is executable on SQLite3. Use only columns that are present in the table, always use quotes around your column and table names (some column names have punctuation or special characters), and refer to the columns using the column-names exactly as they appear in the table, do not add or remove punctuation (underscore, slash, etc.)

Please explain how you plan to answer this query first in a markdown JSON codeblock. In your plan in JSON, please follow this format:
	explain your planned filters as {"Filters": [{"Column": "filter-column-1", "Condition": "equal/less-than/greater-than/…", "Value": "filter-value-1"}, …]}.
	explain your planned group-by as {"GroupBy": ["groupby-column-1", …]}
	explain your aggregation as {"Aggregation": [{"Column": "aggregate-column-name-1", "Aggregation-Function": "min/max/average/…"}, …]}.
	explain your other operations in {"Other": "other plans that do not fit above"}

After the JSON plan, please then return the code only with the following markdown codeblock format : ```sql<SQL CODE>```.

""",
            "Please write the SQL query given the input table and question. Use 'table' as the table name if needed.",
            "Could you create the SQL query using the input table and question, possibly with 'table' as the table name?",
            "Your task is to generate an SQL query using the input table and question. Feel free to employ 'table' as the table name.",
            "Compose the SQL query based on the input table and question. In case it's necessary, utilize 'table' as the table name.",
            "Please come up with an SQL query by referring to the input table and question. You can insert 'table' as the table name if required.",
            "Your job is to write an SQL query while considering the input table and question. Use 'table' as the table name if it helps.",
            "Given the input table and question, devise an SQL query. Include 'table' as the table name if it makes the query clearer.",
            "Create an SQL query with the input table and question in mind. Incorporate 'table' as the table name whenever appropriate.",
            "Design an SQL query using the input table and question as the basis. 'Table' can be used as the table name if necessary.",
            "Please generate an SQL query by using the provided input table and question. You may employ 'table' as the table name if it makes the query more understandable.",
            "Your task is to come up with an SQL query with reference to the input table and question. You can utilize 'table' as the table name when needed.",
            "Compose the SQL query based on the input table and question given. Feel free to include 'table' as the table name for clarity.",
            "Please write an SQL query using the input table and question. If needed, use 'table' as the table name.",
            "Your job is to create an SQL query using the input table and question as the reference. Use 'table' as the table name if it improves the query's readability.",
            "Given the input table and question, devise an SQL query. In case it helps, employ 'table' as the table name in the query.",
            "Develop an SQL query with the input table and question in mind. Don't forget to consider using 'table' as the table name if appropriate.",
            "Design an SQL query based on the input table and question. Incorporate 'table' as the table name if it makes the query more understandable.",
            "Please generate an SQL query by referring to the input table and question provided. 'Table' can be used as the table name if necessary.",
            "Your task is to come up with an SQL query using the input table and question as a guide. You may utilize 'table' as the table name when needed.",
            "Compose the SQL query based on the input table and question given. If needed, include 'table' as the table name for clarity.",
            "Please write an SQL query using the input table and question provided. If necessary, use 'table' as the table name.",
            "Given the input table and question, please draft an SQL query. If required, employ 'table' as the table name.",
            "Create an SQL query based on the input table and question. You can use 'table' as the table name if it aids understanding.",
            "Compose the SQL query using the input table and question provided. Feel free to insert 'table' as the table name, if appropriate.",
            "Please write the SQL query for the given input table and question. Consider using 'table' as the table name when necessary.",
            "Your task is to generate an SQL query using the input table and question as guidance. Use 'table' as the table name if it helps.",
            "Given the input table and question, devise an SQL query. You may include 'table' as the table name for clarity.",
            "Create an SQL query with reference to the input table and question. Incorporate 'table' as the table name whenever suitable.",
            "Design an SQL query based on the input table and question. 'Table' can be used as the table name if needed.",
            "Please generate an SQL query using the input table and question provided. You can employ 'table' as the table name if it improves readability.",
            "Your job is to come up with an SQL query using the input table and question as a basis. You may use 'table' as the table name when appropriate.",
            "Compose the SQL query based on the input table and question given. If necessary, include 'table' as the table name for better understanding.",
            "Please write an SQL query using the input table and question. If needed, utilize 'table' as the table name.",
            "Your task is to create an SQL query using the input table and question as a reference. Use 'table' as the table name if it aids comprehension.",
            "Given the input table and question, devise an SQL query. Consider using 'table' as the table name in the query if it facilitates clarity.",
            "Develop an SQL query with the input table and question in mind. Don't forget to consider using 'table' as the table name if applicable.",
            "Design an SQL query based on the input table and question. Incorporate 'table' as the table name if it enhances the query's readability.",
            "Please generate an SQL query by referring to the input table and question provided. You may use 'table' as the table name if necessary.",
            "Your task is to come up with an SQL query using the input table and question as a guide. You can utilize 'table' as the table name when required.",
            "Compose the SQL query based on the input table and question given. If needed, add 'table' as the table name for clarity.",
            "Please write an SQL query using the input table and question provided. If required, use 'table' as the table name.",
        ]
        return self.select_one_option(descriptions[:5], random_state=random_state)
    
    def add_format_suffix(self, desc):
        # _, ans1, = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        text = f"""{desc}No explanation, return the code only with the following markdown codeblock format : ```sql<SQL CODE>```."""
        # text = f"""{desc}No explanation, return the code only with the following markdown codeblock format : ```sql<SQL CODE>```. After your codeblock, please then reflect on your generated code, to see whether it is syntactically correct that can run, and whether it can accurately answer the given question, if not please correct your code."""
        # text = f"""{desc}Please explain how you plan to answer this query first in a markdown JSON codeblock. After the JSON plan, please then return the code only with the following markdown codeblock format : ```sql<SQL CODE>```."""
        # text = f"""{desc}Please explain how you plan to answer this query first, then return the code only with the following markdown codeblock format : ```sql<SQL CODE>```."""
        # text = f"""{desc}Please explain how you plan to answer this query **step-by-step** first, then return the code only with the following markdown codeblock format : ```sql<SQL CODE>```."""
        # text = f"""{desc}Return the code with the following markdown codeblock format : ```sql<SQL CODE>```.\n\n[Correct]: here is a correct response that succeeds for the task."""
        # text = f"""{desc}Return the code with the following markdown codeblock format : ```sql<SQL CODE>```.\n\n[Incorrect]: here is an incorrect response that fails for the task."""
        # text = f"""{desc}Please first think of an almost correct, but still incorrect SQL for this question first, output as [INCORRECT] folowed by a ```sql<SQL CODE>``` markdown code block, explain why this is likely incorrect, and then produce a correct SQL for this question, as [CORRECT] followed by a ```sql<SQL CODE>``` code block.

# If you cannot think of any almost correct but still incorrect SQL for this question, just output [CORRECT] followed by a ```sql<SQL CODE>``` code block."""
        return text

    def get_input(self, data, random_state=None):
        df, question, incorrect_label = data
        df_text = self.serializer.serialize_df(df)
        text = (
            "**Input table:**\n"
            f"{df_text}\n"
            f"**Question:**\n{question}\n"   
        )
        return text
    
    def get_output(self, y):
        return "```sql\n" + y + "\n```"
        # return "Upon review, code is incorrect and should be rewritten as follows: \n```sql\n" + y + "\n```"
        # return y
    
    def _get_output(self, y):
        return y

    def get_output_example(self):
        return "SQL", "<SQL code>"