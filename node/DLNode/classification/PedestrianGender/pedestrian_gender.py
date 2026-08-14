#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2 as cv
import numpy as np
import onnxruntime


class PedestrianGender(object):
    """Pedestrian gender classifier using pedestrian_gender.onnx.

    Input model:  ``images``  [batch, 3, 224, 224] float32
    Output model: ``class_scores`` [batch, 2] float32 (raw logits)

    Softmax is applied internally so that returned scores are in [0, 1].
    Class mapping: 0 → Male, 1 → Female.
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
        self.input_size = input_size

    @staticmethod
    def _softmax(x):
        e = np.exp(x - x.max())
        return e / e.sum()

    def __call__(self, image, top_k=2):
        # Pre-process: resize, BGR → RGB, HWC → NCHW, normalize to [0, 1]
        input_image = cv.resize(image, dsize=(self.input_size[1], self.input_size[0]))
        input_image = cv.cvtColor(input_image, cv.COLOR_BGR2RGB)
        input_image = input_image.transpose(2, 0, 1)           # HWC → CHW
        input_image = np.expand_dims(input_image, axis=0).astype('float32') / 255.0

        # Inference
        result = self.onnx_session.run(None, {self.input_name: input_image})

        # Post-process: softmax → probabilities, sort descending, top-k
        logits = result[0].squeeze()
        probs = self._softmax(logits)
        sorted_idx = np.argsort(probs)[::-1][:top_k]
        class_scores = probs[sorted_idx]
        class_ids = sorted_idx

        return class_scores, class_ids
