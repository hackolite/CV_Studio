# YOLOv8-nano-seg Model

This directory contains the YOLOv8-nano segmentation model for CV_Studio.

## Model File

The model file should be named `yolov8n-seg.onnx` and placed in the `model/` directory.

## How to Obtain the Model

### Option 1: Convert from YOLOv8 PyTorch weights

1. Install ultralytics:
```bash
pip install ultralytics
```

2. Export YOLOv8-nano-seg to ONNX format:
```python
from ultralytics import YOLO

# Load the model
model = YOLO('yolov8n-seg.pt')

# Export to ONNX
model.export(format='onnx', imgsz=640)
```

This will create `yolov8n-seg.onnx` file.

3. Copy the ONNX file to this directory:
```bash
cp yolov8n-seg.onnx /path/to/CV_Studio/node/DLNode/semantic_segmentation/yolov8_seg/model/
```

### Option 2: Download pre-converted ONNX model

You can download pre-converted ONNX models from the Ultralytics repository or community sources.

## Model Details

- **Architecture**: YOLOv8-nano-seg
- **Input Size**: 640x640
- **Input Format**: RGB, normalized to [0, 1]
- **Output**: 
  - Detection boxes with class scores
  - Segmentation masks (proto masks with coefficients)
- **Classes**: 80 (COCO dataset classes)

## Usage

Once the model is placed in the `model/` directory, it will be available in the Semantic Segmentation node dropdown menu as "YOLOv8-nano-seg".

The node will:
1. Perform instance segmentation on the input image
2. Extract contours from the segmentation masks
3. Display the contours overlaid on the original image

## License

Please refer to the Ultralytics YOLOv8 license for model usage terms.
