from ..row2row_base.r2r_base_task_descriptor import R2RBaseTaskDescriptor
import pandas as pd
import numpy as np

class R2RSTaskDescriptor(R2RBaseTaskDescriptor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pl = "sql"
        
    def _get_task_description(self, random_state=None):
        descriptions = [
            """The task of row-to-row transformation using examples, is to perform data transformation using table columns, to produce a new "DERIVED_COLUMN" in the table.

The task of "program-by-example" or "transform data by-example", is to use a few given example output values in the new "DERIVED_COLUMN", to infer the underlying transformation program that was used to derive the given output values in the "DERIVED_COLUMN". This is also known as program-synthesis or program-by-example in the research literature.

Given the **Input table** shown below, we want to perform data transformations on this Input Table, to produce a **Desired Output Table**, with the new "DERIVED_COLUMN" shown as the rightmost column of the **Desired Output Table**.

Please inspect the given output examples in the "DERIVED_COLUMN" of the **Desired Output Table**, to identify the transformation program that can be used to produce the "DERIVED_COLUMN" using columns in the **Input table**. Please generate SQL code for the transformation that can execute on the **Input table**, to produce an output column that can exactly match the given output examples in the "DERIVED_COLUMN".

Please pay close attention to the format and the details of the given output examples in the "DERIVED_COLUMN", to make sure that your code will generate output values exactly matching the given examples, in terms of style, format, and casing.

For numerical computation, please use SQL Decimal class to avoid floating point precision issues, so always do "CAST(<computation> AS DECIMAL) AS DERIVED_COLUMN" if numbers are involved.

Also, to perform string concatenation in SQL using "||", always remember to cast both sides of "||" from number to string before performing concatenation, so always do "CAST(CAST(<computation> AS DECIMAL) AS TEXT) || "some string"", before you return your results.

Please do not use case_when statements, or anything that is like CASE/IF/ELSE, to hard code your transformation program (e.g., if row id == 1, return output-value-1, etc.). Please produce transformation programs that can *generalize* to new data rows from the same table, that are not shown below in the interest of space.

Your SQL code should always generate your target column in a column named "DERIVED_COLUMN" in your final result. You can assume that your SQL code will be executed on a SQLite3 database and on a table called "table".
"""
        ]
        desc = self.select_one_option(descriptions, random_state=random_state)
        # if self.instruction is not None:
            # desc += f" (Hint: {self.instruction})"
        return desc
    