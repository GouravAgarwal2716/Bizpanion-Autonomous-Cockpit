"""
PyTorch LSTM model definition.
This file is used both for training (on Kaggle) and inference (loaded in FastAPI).
"""
import torch
import torch.nn as nn


class SalesLSTM(nn.Module):
    """
    LSTM-based sales forecasting model.
    Input: sequence of daily sales quantities (normalized)
    Output: next N days of predicted quantities
    """

    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = 64,
        num_layers: int = 2,
        output_size: int = 7,
        dropout: float = 0.2,
    ):
        super(SalesLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x shape: (batch, seq_len, input_size)"""
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])  # Last time step
        return out
