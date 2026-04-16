# PyTorch Model Files

Place your `.pt` PyTorch model file here for the Shark Species CNN.

**Expected filename:** `shark_species_cnn.pt`

## Model Requirements

- **Framework:** PyTorch 2.0+
- **Format:** .pt (PyTorch model file)
- **Input shape:** (batch_size, 3, 224, 224)
- **Output:** Classification logits for shark species

## How to Create/Train Your Model

1. Train your CNN model using PyTorch on shark images
2. Save the model using: `torch.save(model.state_dict(), 'shark_species_cnn.pt')`
3. Place the file in this directory
4. Restart the Django server
5. Upload shark images in the CNN page to test

## Example PyTorch Save Code

```python
import torch
import torch.nn as nn

# Your trained model
model = YourCNNModel()

# Save the model
torch.save(model.state_dict(), 'shark_species_cnn.pt')
```

The application expects the model to return logits/class probabilities for at least 10 shark species.
