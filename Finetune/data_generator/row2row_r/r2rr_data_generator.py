import os
import pandas as pd
import numpy as np
from ..row2row_base.r2r_base_data_generator import R2RBaseDataGenerator
from .r2rr_prompt_generator import R2RRPromptGenerator
from .r2rr_task_descriptor import R2RRTaskDescriptor
import json
from functools import partial

class R2RRDataGenerator(R2RBaseDataGenerator):     
    def _get_prompt_generator(self, params):
        prompt_generator = R2RRPromptGenerator(**params)
        return prompt_generator
    
    def _get_task_descriptor(self, params):
        task_descriptor = R2RRTaskDescriptor(**params)
        return task_descriptor    