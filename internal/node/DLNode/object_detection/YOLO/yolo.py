#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import copy
import cv2
import numpy as np
import onnxruntime
import math


# Désactive cuDNN et utilise le fallback CUDA
os.environ["ORT_CUDA_USE_CUDNN"] = "0"

class YOLO:
    def __init__(
        self,
        model_path='yolo11_n.onnx',
        class_score_th=0.0,
        nms_th=0.45,
        nms_score_th=0.1,
        providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
    ):
        self.class_score_th = class_score_th
        self.nms_th = nms_th
        self.nms_score_th = nms_score_th
        
        self.onnx_session = onnxruntime.InferenceSession(model_path, providers=providers)
        self.input_detail = self.onnx_session.get_inputs()[0]
        self.input_name = self.input_detail.name
        self.output_name = self.onnx_session.get_outputs()[0].name
        
        self.input_shape = (400, 600)
        self.input_width, self.input_height = self.input_shape

    def __call__(self, image):
        temp_image = copy.deepcopy(image)
        temp_image = cv2.resize(temp_image, (608, 416), interpolation=cv2.INTER_AREA)
        image = self._preprocess(temp_image)
        # Debug: print("preprocess", image.shape) 
        results = self.onnx_session.run(None, {self.input_name: image})
        
        bboxes, scores, class_ids = self._postprocess(results[0], self.nms_th, self.nms_score_th)
        return bboxes, scores, class_ids

    def _preprocess(self, image):
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_data = np.array(img) / 255.0
        image_data = np.transpose(image_data, (2, 0, 1))
        image_data = np.expand_dims(image_data, axis=0).astype(np.float32)
        return image_data
    

    def _postprocess(self, outputs, nms_th, nms_score_th):
        outputs = np.transpose(np.squeeze(outputs[0]))
        rows = outputs.shape[0]
        
        boxes, scores, class_ids = [], [], []
        gain = 1

        for i in range(rows):
            # Extract the class scores from the current row
            classes_scores = outputs[i][4:]

            # Find the maximum score among the class scores
            max_score = np.amax(classes_scores)

            # If the maximum score is above the confidence threshold
            if max_score >= nms_score_th:
                # Get the class ID with the highest score
                class_id = np.argmax(classes_scores)

                # Extract the bounding box coordinates from the current row
                x, y, w, h = outputs[i][0], outputs[i][1], outputs[i][2], outputs[i][3]

                # Convert (x, y, w, h) to (x1, y1, x2, y2)
                x1 = int((x - w / 2) / gain)
                y1 = int((y - h / 2) / gain)
                x2 = int((x + w / 2) / gain)
                y2 = int((y + h / 2) / gain)

                # Add the class ID, score, and box coordinates to the respective lists
                class_ids.append(class_id)
                scores.append(max_score)
                boxes.append([x1, y1, x2, y2])

        # Apply non-maximum suppression to filter out overlapping bounding boxes
        indices = cv2.dnn.NMSBoxes(boxes, scores, nms_score_th, nms_th)
        return np.array(boxes), np.array(scores), np.array(class_ids)


    def draw(self, image, score_th, bboxes, scores, class_ids, coco_classes, thickness=1):
        debug_image = copy.deepcopy(image)
        for bbox, score, class_id in zip(bboxes, scores, class_ids):
            x1, y1, x2, y2 = map(int, bbox)
            if score < score_th:
                continue
            color = self._get_color(class_id)
            debug_image = cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, thickness)
            text = f'{coco_classes[int(class_id)]}: {score:.2f}'
            debug_image = cv2.putText(debug_image, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)
        return debug_image
