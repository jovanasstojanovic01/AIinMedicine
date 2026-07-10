import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


class GlaucomaVFProgressionGRU(nn.Module):

    def __init__(self, input_size, hidden_size, num_layers, dropout):
        super(GlaucomaVFProgressionGRU, self).__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout_layer = nn.Dropout(dropout)
        
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x, lengths):
        lengths_cpu = lengths.cpu().int()

        packed_x = pack_padded_sequence(
            x, lengths_cpu, batch_first=True, enforce_sorted=False
        )
        packed_out, _ = self.gru(packed_x)

        
        
        out, _ = pad_packed_sequence(
            packed_out, batch_first=True, total_length=x.size(1)
        )

        out = self.dropout_layer(out)
        preds = self.fc(out)  
        return preds.squeeze(-1)  