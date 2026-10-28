# Table-Specialist 

This repository contains the source code for the EMNLP'25 paper [Table-Specialist: Language Model Specialists for Tables using Iterative Fine-tuning](https://arxiv.org/abs/2410.12164).

## Table of Contents
- [Overview](#overview)
    - [WHAT CAN Table-Specialist do](#what-can-table-specialist-do)
    - [INTENDED USEs](#intended-uses)
    - [OUT-of-scope uses](#out-of-scope-uses)
- [How to get started](#how-to-get-started)
- [Evaluation](#evaluation)
    - [EVALUATION METHODS](#evaluation-methods)
    - [EVALUATION RESULTS](#evaluation-results)
- [LIMITATIONS](#limitations)
- [BEST PRACTICES](#best-practices)
- [LICENSE](#license)
- [TRADEMARKS](#trademarks)
- [CONTACT](#contact)

## Overview 

Table-Specialist is a new self-trained fine-tuning framework specifically designed for table tasks. This repo also contains a method for generating a synthetic training dataset. 

 

### WHAT CAN Table-Specialist do 

Table-Specialist was developed to generate and validate training data for table tasks. Our insight is that for each table task, there often exist two dual versions of the same task, one generative and one classification in nature. Leveraging their duality, we propose a Generator-Validator paradigm, to iteratively generate-then-validate training data from language-models, to fine-tune stronger Table-Specialist models that can specialize in a given task, without using manually-labeled data. In this approach, each Table-Specialist model is fine-tuned by design to focus on one specific type of table task𝑇 (e.g., one model for data transformation, one model for error detection, one model for NL-to-SQL, etc.), which is unlike Table-Generalist models (TableGPT and Table-Llama) that can handle all types of table tasks. 

A detailed discussion of Table-Specialist, including how it was developed and tested, can be found in our paper at:  https://arxiv.org/abs/2410.12164  

 

### INTENDED USEs 

Table-Specialist is best suited for researchers and domain experts that have a comprehensive understanding of the table task they are working on and have experience with LLM fine-tuning. Users should be independently capable of evaluating the quality of outputs before acting on them. 

Table-Specialist is being shared with the research community to facilitate reproduction of our results and foster further research in this area. 

 

 

### OUT-of-scope uses 

Table-Specialist is not well suited for all table-tasks. For example, this approach is not directly applicable to tasks that do not have precise ‘’ground-truth’’, such as table summarization, as the lack of ground-truth makes it hard for perform validation easily. 

There are also tasks that naturally come with ample training data, for which Generator-Validator would not be needed. For example, the task of Data-imputation, predicts the value for a missing cell in a table, where training data can be easily obtained (by masking out random cells in real tables, and use their ground-truth values for training). For such tasks, it would not be necessary to use of Generator-Validator for fine-tuning. 

We do not recommend using Table-Specialist in commercial or real-world applications without further testing and development. It is being released for research purposes. 

Table-Specialist was not designed or evaluated for all possible downstream purposes. Developers should consider its inherent limitations as they select use cases, and evaluate and mitigate for accuracy, safety, and fairness concerns specific to each intended downstream use. 

Without further testing and development, Table-Specialist should not be used in sensitive domains where inaccurate outputs could suggest actions that lead to injury or negatively impact an individual's legal, financial, or life opportunities. 

We do not recommend using Table-Specialist in the context of high-risk decision making (e.g. in law enforcement, legal, finance, or healthcare). 

 

## How to get started 

**Security prerequisite for generated-code execution:** Python, R, and SparkScala outputs are untrusted code. Host execution is disabled. Install and configure the isolated runner described in [sandbox/README.md](sandbox/README.md) before running generation, validation, or code-evaluation scripts. Do not run extracted code files directly on your workstation.

To begin using Table-Specialist, please see details at https://github.com/microsoft/Table-Specialist?tab=readme-ov-file for code and instruction. 

 

## Evaluation 

Table-Specialist was evaluated on its ability to perform NL-to-Code, Error-Detection, Schema-Matching, Table-QA, and Data-Transformation. 

A detailed discussion of our evaluation methods and results can be found in our paper at: https://arxiv.org/abs/2410.12164.  

 

### EVALUATION METHODS 

We used performance improvement after LLM fine-tuning with the generated and validated training data to measure Table-Specialist’s performance. 

We compared the performance of Table-Specialist against TableGPT, TableLlama using benchmarks on NL-to-Code, Error-Detection, Schema-Matching, Table-QA, and Data-Transformation. 

The models used for evaluation were gpt-3.5-turbo, gpt-4, and Llama3.1-8b. For more on these specific models, please see  https://platform.openai.com/docs/models, https://huggingface.co/meta-llama/Llama-3.1-8B.   

Results may vary if Table-Specialist is used with a different model based on its unique design, configuration and training.  

 

### EVALUATION RESULTS 

At a high level, we found that Table-Specialist improves its base models (e.g., TABLE-SPECIALIST-GPT-3.5 improves over GPT-3.5 on all benchmarks and even surpasses vanilla GPT-4 on 7 benchmarks). Importantly, since we do not use the training split of any benchmark data during fine-tuning, it demonstrates that the fine-tuned models can generalize to multiple unseen benchmarks. 

 

## LIMITATIONS 

Table-Specialist was developed for research and experimental purposes. Further testing and validation are needed before considering its application in commercial or real-world scenarios. 

Table-Specialist was designed and tested using the English language. Performance in other languages may vary and should be assessed by someone who is both an expert in the expected outputs and a native speaker of that language. 

Outputs generated by AI may include factual errors, fabrication, or speculation. Users are responsible for assessing the accuracy of generated content. All decisions leveraging outputs of the system should be made with human oversight and not be based solely on system outputs. 

Table-Specialist inherits any biases, errors, or omissions produced by its base model. Developers are advised to choose an appropriate base LLM/MLLM carefully, depending on the intended use case. 

Table-Specialist is model-agnostic, and end users need to use their own model/AI service. We tested Table-Specialist on gpt-3.5-turbo, gpt-4, and Llama3.1-8b only. 

Table-Specialist inherits any biases, errors, or omissions characteristic of its training data, which may be amplified by any AI-generated interpretations.  

There has not been a systematic effort to ensure that systems using Table-Specialist are protected from security vulnerabilities such as indirect prompt injection attacks. Any systems using it should take proactive measures to harden their systems as appropriate. 

Table-Specialist is a framework for LLM fine-tuning on table tasks that is agnostic to both the specific task and the underlying LLM. It does not include built-in security safeguards—for example, preventing the generation of training data for malicious purposes such as SQL injection. Responsibility for content safety and misuse prevention rests with the LLM providers and is not part of the Table-Specialist release. 

 

## BEST PRACTICES 

Better performance can be achieved by defining the table task clearly and giving specific requirements on the expected training data, iteratively refine the prompts. 

We strongly encourage users to use LLMs/MLLMs that support robust Responsible AI mitigations, such as Azure Open AI (AOAI) services. Such services continually update their safety and RAI mitigations with the latest industry standards for responsible use. For more on AOAI’s best practices when employing foundations models for scripts and applications: 

[What is Azure AI Content Safety?] (https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview)   

[Overview of Responsible AI practices for Azure OpenAI models] (https://learn.microsoft.com/en-us/legal/cognitive-services/openai/overview)  

[Azure OpenAI Transparency Note](https://learn.microsoft.com/en-us/legal/cognitive-services/openai/transparency-note) 

[OpenAI’s Usage policies] (https://openai.com/policies/usage-policies)  

[Azure OpenAI’s Code of Conduct] (https://learn.microsoft.com/en-us/legal/cognitive-services/openai/code-of-conduct)  

Users are responsible for sourcing their datasets legally and ethically. This could include securing appropriate rights and/or the anonymization of data prior to use in research.    

Users are reminded to be mindful of data privacy concerns and are encouraged to review the privacy policies associated with any models and data storage solutions interfacing with Table-Specialist.  

It is the user’s responsibility to ensure that the use of Table-Specialist complies with relevant data protection regulations and organizational guidelines. 

Developers should follow transparency best practices and inform end-users they are interacting with an AI system. 

 

## LICENSE 

MIT License 

Nothing disclosed here, including the Out of Scope Uses section, should be interpreted as or deemed a restriction or modification to the license the code is released under. 

 

## TRADEMARKS 

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow Microsoft's Trademark & Brand Guidelines. Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party's policies. 

 

## CONTACT 

This research was conducted by members of Microsoft Research and a PhD student (University of Michigan Ann Arbor) during internship.  We welcome feedback and collaboration from our audience. If you have suggestions, questions, or observe unexpected/offensive behavior in our technology, please contact us at junjiexing@microsoft.com (Junjie Xing). 

If the team receives reports of undesired behavior or identifies issues independently, we will update this repository with appropriate mitigations. 

 