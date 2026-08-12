import tempfile
import unittest
from pathlib import Path

from src.train_and_predict import (
    EvaluationMetrics,
    render_sql,
    validate_identifier,
    verify_metrics,
)


class TrainAndPredictTest(unittest.TestCase):
    def test_training_evaluation_and_prediction_windows_do_not_overlap(self) -> None:
        root = Path(__file__).resolve().parents[1]
        train_sql = (root / "sql" / "train_model.sql").read_text(encoding="utf-8")
        evaluate_sql = (root / "sql" / "evaluate_model.sql").read_text(encoding="utf-8")
        predict_sql = (root / "sql" / "predict_visitors.sql").read_text(encoding="utf-8")

        self.assertIn("'20160801' AND '20170430'", train_sql)
        self.assertIn("'20170501' AND '20170630'", evaluate_sql)
        self.assertIn("'20170701' AND '20170731'", predict_sql)
        self.assertIn("WHERE probability.label = 1", predict_sql)
        self.assertNotIn("OFFSET(1)", predict_sql)

    def test_render_sql_qualifies_model_and_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            template = Path(temporary_directory) / "query.sql"
            template.write_text(
                "{project_id}.{dataset_id}.{model_id} {prediction_table_id}",
                encoding="utf-8",
            )
            sql = render_sql(template, "demo-project", "ecommerce", "model", "scores")

        self.assertEqual(sql, "demo-project.ecommerce.model scores")

    def test_rejects_unsafe_identifier(self) -> None:
        with self.assertRaises(ValueError):
            validate_identifier("dataset`; DROP MODEL model")

    def test_accepts_metrics_better_than_random(self) -> None:
        verify_metrics(EvaluationMetrics(0.45, 0.62, 0.81, 0.52, 0.41, 0.73))

    def test_rejects_random_classifier_auc(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "ROC AUC above 0.5"):
            verify_metrics(EvaluationMetrics(0.2, 0.3, 0.5, 0.2, 0.69, 0.5))


if __name__ == "__main__":
    unittest.main()