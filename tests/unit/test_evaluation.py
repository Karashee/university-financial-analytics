import numpy as np
import pandas as pd

from scripts.evaluate_models import _evaluate_if_from_dataframes, _evaluate_lr_from_arrays

ANOMALY_TYPES = ["Sudden Expenditure Spike", "Duplicate-Like Payment", "Unusual Vendor Payment"]


def make_joined_df(extra_rows: list[dict] = None) -> pd.DataFrame:
    rows = [
        {"is_anomaly_ground_truth": 0, "is_anomaly_predicted": False, "anomaly_type_ground_truth": "Normal"}
        for _ in range(17)
    ]
    rows += [
        {"is_anomaly_ground_truth": 1, "is_anomaly_predicted": True, "anomaly_type_ground_truth": anomaly_type}
        for anomaly_type in ANOMALY_TYPES
    ]
    if extra_rows:
        rows += extra_rows
    return pd.DataFrame(rows)


def test_evaluate_if_perfect_predictions_precision_recall_f1():
    joined_df = make_joined_df()
    result = _evaluate_if_from_dataframes(joined_df)
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0


def test_per_type_recall_has_anomaly_type_keys_excludes_normal():
    joined_df = make_joined_df()
    result = _evaluate_if_from_dataframes(joined_df)
    assert set(result["per_type_recall"].keys()) == set(ANOMALY_TYPES)
    assert "Normal" not in result["per_type_recall"]


def test_missed_anomaly_lowers_recall_but_precision_stays_perfect():
    missed_row = {
        "is_anomaly_ground_truth": 1,
        "is_anomaly_predicted": False,
        "anomaly_type_ground_truth": "Sudden Expenditure Spike",
    }
    joined_df = make_joined_df(extra_rows=[missed_row])
    result = _evaluate_if_from_dataframes(joined_df)
    assert result["recall"] < 1.0
    assert result["precision"] == 1.0


def test_evaluate_lr_from_arrays_mae_and_rmse():
    result = _evaluate_lr_from_arrays(np.array([100, 200, 300]), np.array([110, 190, 310]))
    assert result["mae"] == 10.0
    assert result["rmse"] >= 10.0


def test_evaluate_lr_from_arrays_test_size():
    result = _evaluate_lr_from_arrays(np.array([100, 200, 300]), np.array([110, 190, 310]))
    assert result["test_size"] == 3
