import os
import pandas as pd
import numpy as np
from ..row2row_base.r2r_base_data_generator import R2RBaseDataGenerator
from .r2rss_prompt_generator import R2RSSPromptGenerator
from .r2rss_task_descriptor import R2RSSTaskDescriptor
import json
from functools import partial

class R2RSSDataGenerator(R2RBaseDataGenerator):     
    def _get_prompt_generator(self, params):
        prompt_generator = R2RSSPromptGenerator(**params)
        return prompt_generator
    
    def _get_task_descriptor(self, params):
        task_descriptor = R2RSSTaskDescriptor(**params)
        return task_descriptor    