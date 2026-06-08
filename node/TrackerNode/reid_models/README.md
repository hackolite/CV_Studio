# ReID ONNX Models

Place your OSNet ONNX model files here for deep feature extraction.

## Supported Models

| File name           | Method selector   | Input shape     | Feature dim | Notes                            |
|---------------------|-------------------|-----------------|-------------|----------------------------------|
| `osnet_x0_25.onnx`  | OSNet_x0_25       | (1,3,256,128)   | 512         | Lightweight – recommended        |
| `osnet_x0_5.onnx`   | OSNet_x0_5        | (1,3,256,128)   | 512         | Medium                           |
| `osnet_x1_0.onnx`   | OSNet_x1_0        | (1,3,256,128)   | 512         | Full size, best accuracy         |

## How to export an OSNet model to ONNX

Install torchreid (`pip install torchreid`) then run:

```python
import torchreid
import torch

model = torchreid.models.build_model(
    name='osnet_x0_25',      # or osnet_x0_5 / osnet_x1_0
    num_classes=1,
    loss='softmax',
    pretrained=True
)
model.eval()

dummy = torch.zeros(1, 3, 256, 128)
torch.onnx.export(
    model, dummy, 'osnet_x0_25.onnx',
    input_names=['input'],
    output_names=['output'],
    opset_version=11,
    dynamic_axes={'input': {0: 'batch'}, 'output': {0: 'batch'}}
)
print('Exported osnet_x0_25.onnx')
```

## Pre-built weights (alternative)

Community-exported ONNX weights are available from the OpenCV Zoo project:
https://github.com/opencv/opencv_zoo

## Fallback

If no ONNX model file is found for the selected method, the node automatically
falls back to **Color Histogram** feature extraction with a warning in the log.
