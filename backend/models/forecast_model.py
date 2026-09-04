"""
Forecast Model — PyTorch LSTM + Statistical fallback (Prophet/ARIMA)
Predicts demand for the next N days based on historical transaction data.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from config import settings
import logging

logger = logging.getLogger(__name__)


class ForecastModel:
    """
    Tries to load PyTorch LSTM weights if available.
    Falls back to Prophet (statistical) which is always available.
    """

    def __init__(self):
        self._torch_model = None
        self._try_load_torch()

    def _try_load_torch(self):
        weights_path = Path(settings.MODEL_WEIGHTS_PATH)
        if not weights_path.exists():
            logger.info("PyTorch weights not found — using statistical fallback")
            return
        try:
            import torch
            from models.lstm_model import SalesLSTM
            model = SalesLSTM(input_size=1, hidden_size=64, num_layers=2, output_size=7)
            model.load_state_dict(torch.load(weights_path, map_location="cpu"))
            model.eval()
            self._torch_model = model
            logger.info("✅ PyTorch LSTM model loaded")
        except Exception as e:
            logger.warning(f"PyTorch model load failed: {e} — using statistical fallback")

    def predict(self, transactions: list[dict], days_ahead: int = 7) -> dict:
        """
        Predict demand for the next `days_ahead` days.
        Returns dict with predicted_demand_7d and confidence.
        """
        df = self._build_daily_series(transactions)

        if self._torch_model and len(df) >= 30:
            return self._predict_torch(df, days_ahead)
        else:
            return self._predict_statistical(df, days_ahead)

    def _build_daily_series(self, transactions: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(transactions)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "quantity"])
        daily = df.groupby(df["date"].dt.date)["quantity"].sum().reset_index()
        daily.columns = ["date", "quantity"]
        daily = daily.sort_values("date")
        # Fill missing days with 0
        if len(daily) > 1:
            idx = pd.date_range(daily["date"].min(), daily["date"].max())
            daily = daily.set_index("date").reindex(idx, fill_value=0).reset_index()
            daily.columns = ["date", "quantity"]
        return daily

    def _predict_torch(self, df: pd.DataFrame, days_ahead: int) -> dict:
        import torch
        seq_len = 30
        series = df["quantity"].values[-seq_len:].astype(np.float32)
        mean, std = series.mean(), series.std() + 1e-8
        series_norm = (series - mean) / std
        
        x = torch.tensor(series_norm, dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
        with torch.no_grad():
            pred_norm = self._torch_model(x).numpy().flatten()
        
        pred = pred_norm * std + mean
        pred = np.maximum(pred, 0)
        total_demand = float(pred[:days_ahead].sum())
        
        return {
            "predicted_demand_7d": round(total_demand, 2),
            "daily_predictions": [round(float(v), 2) for v in pred[:days_ahead]],
            "confidence": 0.82,
            "model": "pytorch_lstm",
        }

    def _predict_statistical(self, df: pd.DataFrame, days_ahead: int) -> dict:
        """Prophet with ARIMA as sub-fallback."""
        if len(df) < 5:
            # Not enough data — use simple mean
            avg = df["quantity"].mean() if len(df) > 0 else 0
            return {
                "predicted_demand_7d": round(avg * days_ahead, 2),
                "daily_predictions": [round(avg, 2)] * days_ahead,
                "confidence": 0.4,
                "model": "mean_fallback",
            }

        try:
            from prophet import Prophet
            prophet_df = df.rename(columns={"date": "ds", "quantity": "y"})
            prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
            
            m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
            m.fit(prophet_df)
            
            future = m.make_future_dataframe(periods=days_ahead)
            forecast = m.predict(future)
            next_days = forecast.tail(days_ahead)
            
            predictions = np.maximum(next_days["yhat"].values, 0)
            return {
                "predicted_demand_7d": round(float(predictions.sum()), 2),
                "daily_predictions": [round(float(v), 2) for v in predictions],
                "confidence": 0.72,
                "model": "prophet",
            }
        except Exception as e:
            logger.warning(f"Prophet failed: {e} — using rolling average")
            rolling_avg = df["quantity"].rolling(7, min_periods=1).mean().iloc[-1]
            total = float(rolling_avg * days_ahead)
            return {
                "predicted_demand_7d": round(total, 2),
                "daily_predictions": [round(float(rolling_avg), 2)] * days_ahead,
                "confidence": 0.55,
                "model": "rolling_average",
            }
