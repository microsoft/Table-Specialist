from ..row2row_base.r2r_base_task_descriptor import R2RBaseTaskDescriptor
import pandas as pd
import numpy as np

class R2RPTaskDescriptor(R2RBaseTaskDescriptor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pl = "python"
        
    def _get_task_description(self, random_state=None):
        descriptions = [
            # """Please inspect the given output examples in the "DERIVED_COLUMN" of the **Desired Output Table**, to identify the transformation program that can be used to produce the "DERIVED_COLUMN" using columns in the **Input table**. Please generate Python Pandas code for the transformation that can execute on the **Input table**.""",
            """The task of row-to-row transformation using examples, is to perform data transformation using table columns, to produce a new "DERIVED_COLUMN" in the table.
 
The task of "program-by-example" or "transform data by-example", is to use a few given example output values in the new "DERIVED_COLUMN", to infer the underlying transformation program that was used to derive the given output values in the "DERIVED_COLUMN". This is also known as program-synthesis or program-by-example in the research literature.
 
Given the **Input table** shown below, we want to perform data transformations on this Input Table, to produce a **Desired Output Table**, with the new "DERIVED_COLUMN" shown as the rightmost column of the **Desired Output Table**.
 
Please inspect the given output examples in the "DERIVED_COLUMN" of the **Desired Output Table**, to identify the transformation program that can be used to produce the "DERIVED_COLUMN" using columns in the **Input table**. Please generate Python Pandas code for the transformation that can execute on the **Input table**, to produce an output column that can exactly match the given output examples in the "DERIVED_COLUMN".
 
Please pay close attention to the format and the details of the given output examples in the "DERIVED_COLUMN", to make sure that your code will generate output values exactly matching the given examples, in terms of style, format, and casing.
When you generate Python Pandas code to read the input table, you can assume that the input table is always stored in a file named "data.csv", so always start your Python code with the boilerplate prefix:
"import pandas as pd
df = pd.read_csv('data.csv')
"

For numerical computation, please use Python Decimal class to avoid floating point precision issues, so always include "from decimal import Decimal" at the beginning of your code.

Please do not hard code your transformation program (e.g., if row id == 1, return output-value-1, etc.). Please produce transformation programs that can *generalize* to new data rows from the same table, that are not shown below in the interest of space.
Your Python Pandas code should always generate your target column in a column named "DERIVED_COLUMN" in the final dataframe. Please always save your final dataframe with this  "DERIVED_COLUMN" into a file named "result.csv" with header and no index column.
""",
            """The task of row-to-row transformation, is to perform data transformation using values in input columns from the same row, to produce a new output value in an output column.
 
In the table below, we want to perform row-to-row transformations. The last column marked as "TARGET_COLUMN" is the output column where we want to generate new output values, and all columns to the left of "TARGET_COLUMN" are used as input columns. In the "TARGET_COLUMN", only the first few values filled in, while the remaining cells in this column are currently missing (marked as "<MISSING>"), which we will need to fill in.
 
Your goal is to use the first few rows, to identify the transformation relationships between values in the input columns (all columns except the last "TARGET_COLUMN") and the values in the output column ("TARGET_COLUMN"). Please generate Python Pandas code that can be used to execute on the input table, to produce an output column that can exactly match the given examples in the "TARGET_COLUMN".
 
Please pay close attention to the format and the details of the given output examples in the "TARGET_COLUMN", to make sure that your code will generate output values exactly matching the given examples, in terms of style, format, and casing. 
When you generate Python Pandas code to read the input table, you can assume that the input table is always stored in a file named "data.csv", so always start your Python code with the boilerplate prefix:
"import pandas as pd
df = pd.read_csv('data.csv')
"
 
Your Python Pandas code should always generate your target column in a column named "TARGET_COLUMN" in the final dataframe. Please always save your final dataframe with this  "TARGET_COLUMN" into a file named "result.csv" with header and no index column.""",
            """Instruction:
Table row to row transformation with Python Pandas is the task to generate python code with Pandas library that can derive a target column given a input table and several example rows for the target column. Please figure out the patterns between the input table  and the target column from the first few rows, and generate the python code that can derive the entire target column.
 
The target column is marked as "TARGET_COLUMN" in the input, example rows are filled with values and others are filled with "<MISSING>".
 
The input table includes all the columns in the input except for the target column. Please produce your Python Pandas code that can run on this table, to generate the target column. To read this table, you can assume that the input table is always stored in a file named "data.csv", so always start your Python code with the boilerplate prefix:
"import pandas as pd
df = pd.read_csv('data.csv')
"
You should always generate your target column in a column named "TARGET_COLUMN" in the final dataframe. Please always save your final dataframe with this  "TARGET_COLUMN" into a file named "result.csv" with header and no index column.""",
        ]
        desc = self.select_one_option(descriptions, random_state=random_state)
        # if self.instruction is not None:
            # desc += f" (Hint: {self.instruction})"
        return desc
    