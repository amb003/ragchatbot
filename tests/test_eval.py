from ragchatbot.config import AppConfig
from ragchatbot.eval.runner import run_eval


def test_eval_suite(prepared_env: AppConfig) -> None:
    report = run_eval(prepared_env)
    assert report.failed == 0
