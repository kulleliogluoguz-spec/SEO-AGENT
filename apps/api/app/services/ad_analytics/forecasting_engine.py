"""
Forecasting Engine
- Prophet for time-series ROAS/conversion forecasting (with linear fallback)
- IsolationForest for anomaly detection
- Rule-based CTR prediction (XGBoost optional)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ForecastingEngine:
    """Multi-model forecasting for ad performance metrics."""

    # ── ROAS forecast ────────────────────────────────────────────────────────

    def forecast_roas(
        self,
        historical_data: list[dict],
        forecast_days: int = 30,
        campaign_name: str = "campaign",
    ) -> dict:
        """
        Forecast ROAS for next N days using Prophet (with linear fallback).
        Input: [{"date": "2024-01-01", "roas": 2.5}, ...]
        """
        if not historical_data:
            return self._linear_forecast([], forecast_days)

        try:
            from prophet import Prophet
        except ImportError:
            logger.warning("[forecast] prophet not installed, using linear")
            return self._linear_forecast(historical_data, forecast_days)

        if len(historical_data) < 14:
            return self._linear_forecast(historical_data, forecast_days)

        try:
            df = pd.DataFrame(historical_data)
            df["ds"] = pd.to_datetime(df["date"])
            df["y"] = df["roas"].clip(lower=0)

            model = Prophet(
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=1.0,
                seasonality_mode="multiplicative",
                weekly_seasonality=True,
                yearly_seasonality=len(df) > 90,
                daily_seasonality=False,
                interval_width=0.90,
            )
            model.fit(df[["ds", "y"]])
            future = model.make_future_dataframe(periods=forecast_days, freq="D")
            forecast = model.predict(future)

            future_only = forecast[forecast["ds"] > df["ds"].max()].copy()

            return {
                "campaign": campaign_name,
                "forecast_days": forecast_days,
                "start_date": future_only["ds"].iloc[0].strftime("%Y-%m-%d"),
                "end_date": future_only["ds"].iloc[-1].strftime("%Y-%m-%d"),
                "daily_forecasts": [
                    {
                        "date": row["ds"].strftime("%Y-%m-%d"),
                        "predicted_roas": round(max(row["yhat"], 0), 3),
                        "lower_bound": round(max(row["yhat_lower"], 0), 3),
                        "upper_bound": round(max(row["yhat_upper"], 0), 3),
                    }
                    for _, row in future_only.iterrows()
                ],
                "avg_predicted_roas": round(float(future_only["yhat"].clip(lower=0).mean()), 3),
                "trend": (
                    "improving"
                    if future_only["trend"].iloc[-1] > future_only["trend"].iloc[0]
                    else "declining"
                ),
                "model": "prophet",
            }
        except Exception as e:
            logger.error("[forecast] prophet failed: %s", e)
            return self._linear_forecast(historical_data, forecast_days)

    def _linear_forecast(self, historical_data: list[dict], forecast_days: int) -> dict:
        """Simple linear/mean extrapolation as fallback."""
        if not historical_data:
            return {
                "daily_forecasts": [],
                "avg_predicted_roas": 0,
                "trend": "stable",
                "model": "linear_fallback",
            }

        values = [float(d.get("roas", 0) or 0) for d in historical_data]
        recent = values[-7:] if len(values) >= 7 else values
        avg = float(np.mean(recent))
        std = float(np.std(recent)) if len(recent) > 1 else max(avg * 0.2, 0.1)

        forecasts = []
        base = date.today()
        for i in range(forecast_days):
            d = base + timedelta(days=i)
            forecasts.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "predicted_roas": round(avg, 3),
                    "lower_bound": round(max(avg - 1.645 * std, 0), 3),
                    "upper_bound": round(avg + 1.645 * std, 3),
                }
            )

        return {
            "daily_forecasts": forecasts,
            "avg_predicted_roas": round(avg, 3),
            "trend": "stable",
            "model": "linear_extrapolation",
        }

    # ── CTR prediction ───────────────────────────────────────────────────────

    def predict_ctr(self, campaign_features: dict) -> dict:
        """
        Predict CTR from campaign features.
        Uses a degradation model based on ad age + frequency.
        """
        age = float(campaign_features.get("ad_age_days", 7))
        freq = float(campaign_features.get("frequency", 3))
        base_ctr = float(campaign_features.get("historical_ctr", 0.02))

        age_factor = max(1 - (age / 30) * 0.3, 0.5)
        freq_factor = max(1 - (freq / 8) * 0.4, 0.4)
        predicted = base_ctr * age_factor * freq_factor

        return {
            "predicted_ctr": round(predicted, 5),
            "confidence": 0.60,
            "model": "rule_based_degradation",
            "degradation_factors": {
                "age_factor": round(age_factor, 3),
                "frequency_factor": round(freq_factor, 3),
            },
        }

    # ── Anomaly detection ────────────────────────────────────────────────────

    def detect_anomalies(self, time_series: list[dict], metric: str = "roas") -> list[dict]:
        """
        Detect anomalous days using IsolationForest.
        Returns dates whose metric value is statistically anomalous.
        """
        if len(time_series) < 14:
            return []

        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            return []

        try:
            df = pd.DataFrame(time_series)
            if metric not in df.columns:
                return []
            values = df[metric].astype(float).values.reshape(-1, 1)

            model = IsolationForest(contamination=0.1, random_state=42)
            labels = model.fit_predict(values)

            anomalies = []
            mean_val = float(np.mean(values))
            std_val = float(np.std(values)) or 1.0
            for i, (label, row) in enumerate(zip(labels, df.itertuples(), strict=False)):
                if label == -1:
                    val = float(values[i][0])
                    severity = "high" if abs(val - mean_val) > 2 * std_val else "medium"
                    anomalies.append(
                        {
                            "date": str(getattr(row, "date", i)),
                            "value": val,
                            "severity": severity,
                        }
                    )
            return anomalies
        except Exception as e:
            logger.error("[forecast] anomaly detection failed: %s", e)
            return []

    # ── Enhanced anomaly detection (richer payload) ──────────────────────────

    def detect_anomalies_enhanced(
        self,
        time_series: list[dict],
        metric: str = "roas",
        sensitivity: float = 1.5,
    ) -> dict:
        """
        Returns a richer payload with z-scores, expected value, deviation %,
        direction (spike/drop), and per-anomaly severity. Falls back to z-score
        thresholds if scikit-learn is unavailable.
        """
        if len(time_series) < 7:
            return {"anomalies": [], "status": "insufficient_data"}
        try:
            df = pd.DataFrame(time_series)
        except Exception as e:
            logger.error("[forecast] enhanced anomaly df build failed: %s", e)
            return {"anomalies": [], "status": "error"}

        if metric not in df.columns:
            return {"anomalies": [], "status": f"metric {metric} not found"}

        values = df[metric].fillna(0).astype(float).values
        mean = float(np.mean(values)) if len(values) else 0.0
        std = float(np.std(values)) if len(values) else 0.0
        z_scores = np.abs((values - mean) / std) if std > 0 else np.zeros(len(values))

        try:
            from sklearn.ensemble import IsolationForest

            labels = IsolationForest(contamination=0.1, random_state=42).fit_predict(
                values.reshape(-1, 1)
            )
        except Exception:
            labels = np.where(z_scores > sensitivity * 2, -1, 1)

        anomalies: list[dict] = []
        for i, (z, label) in enumerate(zip(z_scores, labels, strict=False)):
            if label == -1 or z > sensitivity * 2:
                row = df.iloc[i]
                v = float(row[metric])
                direction = "spike" if v > mean else "drop"
                if z > sensitivity * 3:
                    severity = "critical"
                elif z > sensitivity * 2:
                    severity = "high"
                else:
                    severity = "medium"
                anomalies.append(
                    {
                        "date": str(row.get("date", i)),
                        "metric": metric,
                        "value": v,
                        "expected": round(mean, 3),
                        "deviation_pct": (round((v - mean) / mean * 100, 1) if mean else 0),
                        "direction": direction,
                        "severity": severity,
                        "description": f"{metric.upper()} {direction}: {v:.2f} vs expected {mean:.2f}",
                    }
                )
        return {
            "anomalies": anomalies,
            "metric": metric,
            "mean": round(mean, 3),
            "total": len(anomalies),
        }
