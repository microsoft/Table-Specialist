import os
import pandas as pd
import numpy as np
from ..row2row_base.r2r_base_data_generator import R2RBaseDataGenerator
from .r2rs_prompt_generator import R2RSPromptGenerator
from .r2rs_task_descriptor import R2RSTaskDescriptor
import json
from functools import partial

class R2RSDataGenerator(R2RBaseDataGenerator):     
    def _get_prompt_generator(self, params):
        prompt_generator = R2RSPromptGenerator(**params)
        return prompt_generator
    
    def _get_task_descriptor(self, params):
        task_descriptor = R2RSTaskDescriptor(**params)
        return task_descriptor    