"""
Train the PyTorch SalesLSTM forecasting model locally and save weights.
This activates deep learning demand forecasting across all sectors.
"""
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from models.lstm_model import SalesLSTM

def train_and_save():
    print("[INFO] Starting PyTorch LSTM demand forecast model training...")
    
    # Generate multi-trend synthetic daily sales series (180 days)
    np.random.seed(42)
    torch.manual_seed(42)
    
    # 180 days with weekly periodicity, seasonal trend, and noise
    days = 180
    t = np.arange(days)
    weekly_pattern = 15 * np.sin(2 * np.pi * t / 7)
    monthly_trend = 0.2 * t
    base_demand = 85.0
    noise = np.random.normal(0, 4.0, size=days)
    series = base_demand + weekly_pattern + monthly_trend + noise
    series = np.maximum(series, 10.0)

    # Normalize
    mean_val = float(np.mean(series))
    std_val = float(np.std(series))
    norm_series = (series - mean_val) / std_val

    # Create sequences: seq_len = 30 -> predict next 7 days
    seq_len = 30
    pred_len = 7
    X_list, y_list = [], []
    for i in range(len(norm_series) - seq_len - pred_len + 1):
        X_list.append(norm_series[i : i + seq_len])
        y_list.append(norm_series[i + seq_len : i + seq_len + pred_len])

    X_train = torch.tensor(np.array(X_list), dtype=torch.float32).unsqueeze(-1) # (N, 30, 1)
    y_train = torch.tensor(np.array(y_list), dtype=torch.float32)              # (N, 7)

    # Initialize model
    model = SalesLSTM(input_size=1, hidden_size=64, num_layers=2, output_size=pred_len)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    # Train for 60 epochs
    model.train()
    for epoch in range(60):
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 20 == 0:
            print(f"   Epoch [{epoch+1}/60], Loss: {loss.item():.4f}")

    # Save weights
    out_dir = Path("models")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "forecast_model.pt"
    torch.save(model.state_dict(), out_path)
    print(f"[SUCCESS] PyTorch LSTM model weights saved to {out_path} ({out_path.stat().st_size} bytes)")

if __name__ == "__main__":
    train_and_save()
