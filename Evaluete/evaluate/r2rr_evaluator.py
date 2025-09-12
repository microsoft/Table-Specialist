from .r2r_base_evaluator import R2RBaseEvaluator

class R2RREvaluator(R2RBaseEvaluator):
    def __init__(self):
        super().__init__()
        self.run_time_executive = "Rscript"
        self.run_time_file = "transform.R"
        self.pl = "r"

        self.codeBlockNotFound = f"{self.pl}CodeBlockNotFound"
        self.executionError = f"{self.pl}ExecutionError"
        