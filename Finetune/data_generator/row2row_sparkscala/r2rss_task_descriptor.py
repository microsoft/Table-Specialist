from ..row2row_base.r2r_base_task_descriptor import R2RBaseTaskDescriptor
import pandas as pd
import numpy as np

class R2RSSTaskDescriptor(R2RBaseTaskDescriptor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pl = "scala"
        
    def _get_task_description(self, random_state=None):
        descriptions = [
            """The task of row-to-row transformation using examples, is to perform data transformation using table columns, to produce a new "DERIVED_COLUMN" in the table.
 
The task of "program-by-example" or "transform data by-example", is to use a few given example output values in the new "DERIVED_COLUMN", to infer the underlying transformation program that was used to derive the given output values in the "DERIVED_COLUMN". This is also known as program-synthesis or program-by-example in the research literature.
 
Given the **Input table** shown below, we want to perform data transformations on this Input Table, to produce a **Desired Output Table**, with the new "DERIVED_COLUMN" shown as the rightmost column of the **Desired Output Table**.
 
Please inspect the given output examples in the "DERIVED_COLUMN" of the **Desired Output Table**, to identify the transformation program that can be used to produce the "DERIVED_COLUMN" using columns in the **Input table**. Please generate Scala code using the Apache Spark library for the transformation that can execute on the **Input table**, to produce an output column that can exactly match the given output examples in the "DERIVED_COLUMN".
 
Please pay close attention to the format and the details of the given output examples in the "DERIVED_COLUMN", to make sure that your code will generate output values exactly matching the given examples, in terms of style, format, and casing.
When you generate Spark Scala code to read the input table, you can assume that the input table is always stored in a file named "data.csv", so always start your Spark Scala code with the boilerplate prefix:
"val df = spark.read.option("header", "true").csv("data.csv")"
 
Please do not use match/case statements, or anything that is like CASE/IF/ELSE, to hard code your transformation program (e.g., if row id == 1, return output-value-1, etc.). Please produce transformation programs that can *generalize* to new data rows from the same table, that are not shown below in the interest of space.
 
Your Spark Scala code should always generate your target column in a column named "DERIVED_COLUMN" in the final dataframe. Please always save your final dataframe with this "DERIVED_COLUMN" into a file named "result.csv" with header and no index column.""",
        ]
        desc = self.select_one_option(descriptions, random_state=random_state)
        # if self.instruction is not None:
            # desc += f" (Hint: {self.instruction})"
        return desc
    