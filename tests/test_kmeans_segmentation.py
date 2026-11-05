"""KMeans tiers on a synthetic Customer 360 table with four planted groups."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kmeans_segmentation import FEATURES, cluster_customers, prepare_features, write_report  # noqa: E402


@pytest.fixture(scope="module")
def customers():
    rng = np.random.default_rng(0)
    groups = [  # (balance, txn value, txn count, products, loans)
        (80_000, 60_000, 400, 3, 40_000),
        (60_000, 2_000, 20, 1, 0),
        (2_000, 30_000, 300, 3, 5_000),
        (1_000, 500, 10, 1, 0),
    ]
    rows = []
    for g, (bal, val, cnt, prod, loan) in enumerate(groups):
        for _ in range(250):
            rows.append({
                "customer_id": len(rows) + 1,
                "total_balance": rng.lognormal(np.log(bal), 0.3),
                "transaction_value": rng.lognormal(np.log(val), 0.3),
                "transaction_count": max(1, int(rng.normal(cnt, cnt * 0.1))),
                "product_count": prod,
                "total_loan_value": rng.lognormal(np.log(loan), 0.3) if loan else 0.0,
                "customer_segment": f"rule-{g}",
            })
    return pd.DataFrame(rows)


def test_skewed_columns_are_log_transformed_and_everything_scaled():
    rng = np.random.default_rng(1)
    n = 2000
    df = pd.DataFrame({
        "total_balance": rng.lognormal(8, 1.5, n),        # heavily right-skewed, like real balances
        "transaction_value": rng.lognormal(7, 1.5, n),
        "transaction_count": rng.normal(100, 10, n).clip(1),  # roughly symmetric: left as is
        "product_count": rng.integers(1, 4, n),
        "total_loan_value": rng.lognormal(9, 1.5, n),
    })
    X, before, after, logged = prepare_features(df)
    assert {"total_balance", "transaction_value", "total_loan_value"} <= set(logged)
    assert "transaction_count" not in logged
    assert abs(after["total_balance"]) < abs(before["total_balance"])
    assert np.allclose(X.mean(axis=0), 0, atol=1e-6) and np.allclose(X.std(axis=0), 1, atol=1e-3)


def test_recovers_four_planted_groups(customers):
    result = cluster_customers(customers, scan=False)
    assert result.data["kmeans_tier"].nunique() == 4
    assert result.agreement_with_rules > 0.9  # planted groups match the clusters almost exactly
    assert result.summary["customers"].sum() == len(customers)


def test_tiers_are_named_by_value_and_engagement(customers):
    tiers = set(cluster_customers(customers, scan=False).data["kmeans_tier"])
    assert {"High Value, High Engagement", "Low Value, Low Engagement"} <= tiers


def test_report_contains_assumption_checks(customers, tmp_path):
    result = cluster_customers(customers, scan=True)
    write_report(result, tmp_path / "report.md")
    text = (tmp_path / "report.md").read_text()
    assert "Skew before" in text and "Silhouette" in text and "adjusted Rand index" in text
    assert set(result.silhouette_by_k) == set(range(2, 8))
    assert all(f in text for f in FEATURES)
