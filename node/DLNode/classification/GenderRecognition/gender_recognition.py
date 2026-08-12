#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2 as cv
import numpy as np
import onnxruntime


class GenderRecognition(object):
    """Gender recognition classifier (Male / Female).

    Input : BGR image (any size)
    Output: class_scores, class_ids  where class 0 = Male, class 1 = Female
    """

    CLASS_NAMES = {0: 'Male', 1: 'Female'}

    def __init__(
        self,
        model_path,
        input_size=(224, 224),
        providers=None,
    ):
        if providers is None:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.onnx_session = onnxruntime.InferenceSession(
            model_path,
            providers=providers,
        )
        self.input_name = self.onnx_session.get_inputs()[0].name
        self.output_name = self.onnx_session.get_outputs()[0].name
        self.input_shape = input_size

    def __call__(self, image, top_k=2):
        # Pre-process: Resize, BGR -> RGB, HWC -> NCHW, float32
        input_image = cv.resize(
            image,
            dsize=(self.input_shape[1], self.input_shape[0]),
        )
        input_image = cv.cvtColor(input_image, cv.COLOR_BGR2RGB)
        input_image = input_image.transpose(2, 0, 1)          # HWC -> CHW
        input_image = np.expand_dims(input_image, axis=0).astype('float32')

        # Inference
        result = self.onnx_session.run(
            None, {self.input_name: input_image}
        )

        # Post-process: squeeze and return top-k scores / ids
        scores = np.array(result).squeeze()
        sorted_idx = np.argsort(scores)[::-1][:top_k]
        class_scores = scores[sorted_idx]
        class_ids = sorted_idx

        return class_scores, class_ids


if __name__ == '__main__':
    cap = cv.VideoCapture(0)

    model_path = 'model/GenderRecognition.onnx'
    model = GenderRecognition(model_path)
    class_names = GenderRecognition.CLASS_NAMES

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        class_scores, class_ids = model(frame)
        label = class_names.get(int(class_ids[0]), 'Unknown')
        score = float(class_scores[0])
        cv.putText(frame, f'{label}: {score:.2f}', (10, 30),
                   cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv.imshow('GenderRecognition', frame)

        key = cv.waitKey(1)
        if key == 27:
            break

    cap.release()
    cv.destroyAllWindows()
