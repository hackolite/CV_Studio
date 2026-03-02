#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import os
import threading

import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode


def _load_model_and_build_db(result_dict, csv_path, model_name):
    """Load TinyBERT model, read CSV, vectorize sentences, build database.

    Runs in a background thread so the GUI stays responsive.
    Results are returned through *result_dict*.
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel

        result_dict['status'] = 'Loading model...'
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        model.eval()

        result_dict['status'] = 'Reading CSV...'
        sentences = []
        scores = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sentences.append(row['sentence'].strip())
                scores.append(float(row['vigilance']))

        if not sentences:
            result_dict['error'] = 'CSV is empty'
            return

        result_dict['status'] = 'Vectorizing {} sentences...'.format(len(sentences))
        vectors = []
        batch_size = 32
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]
            inputs = tokenizer(
                batch, return_tensors='pt', truncation=True,
                max_length=128, padding=True,
            )
            with torch.no_grad():
                outputs = model(**inputs)
            # Mean pooling
            attention_mask = inputs['attention_mask']
            token_embeddings = outputs.last_hidden_state
            mask_expanded = attention_mask.unsqueeze(-1).expand(
                token_embeddings.size(),
            ).float()
            sum_embeddings = torch.sum(token_embeddings * mask_expanded, 1)
            sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
            batch_vectors = (sum_embeddings / sum_mask).numpy()
            vectors.append(batch_vectors)

        vectors = np.vstack(vectors)
        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vectors = vectors / norms

        # Build index if >300 phrases
        nn_index = None
        if len(sentences) > 300:
            from sklearn.neighbors import NearestNeighbors
            nn_index = NearestNeighbors(
                n_neighbors=1, metric='cosine', algorithm='brute',
            )
            nn_index.fit(vectors)

        result_dict['tokenizer'] = tokenizer
        result_dict['model'] = model
        result_dict['vectors'] = vectors
        result_dict['scores'] = np.array(scores)
        result_dict['nn_index'] = nn_index
        result_dict['done'] = True
        result_dict['status'] = 'Loaded {} sentences'.format(len(sentences))

    except ImportError as exc:
        result_dict['error'] = 'Missing: {}'.format(str(exc)[:50])
    except FileNotFoundError:
        result_dict['error'] = 'CSV file not found'
    except Exception as exc:
        result_dict['error'] = 'Error: {}'.format(str(exc)[:60])


def _on_load_click(sender, app_data, user_data):
    """Callback for Load button click."""
    node = user_data
    node._load_requested = True


class FactoryNode:
    node_label = 'TinyBert Vigilance'
    node_tag = 'TinyBertVigilance'

    def __init__(self):
        pass

    def add_node(
        self, parent, node_id, pos=[0, 0],
        callback=None, opencv_setting_dict=None,
    ):
        node = TinyBertVigilanceNode()
        node.tag_node_name = '{}:{}'.format(node_id, node.node_tag)
        tag_node_name = node.tag_node_name

        # JSON Input (from VLM or other source)
        node.tag_node_input_json_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':InputJson'
        )
        node.tag_node_input_json_value_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':InputJsonValue'
        )

        # JSON Output (vigilance score)
        node.tag_node_output_json_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':OutputJson'
        )
        node.tag_node_output_json_value_name = (
            tag_node_name + ':' + node.TYPE_JSON + ':OutputJsonValue'
        )

        # Static widget tags
        tag_csv_path = tag_node_name + ':CsvPathValue'
        tag_model_name = tag_node_name + ':ModelNameValue'
        tag_status = tag_node_name + ':StatusValue'

        node._opencv_setting_dict = opencv_setting_dict or {}

        # Default CSV path (bundled with the node)
        default_csv = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'vigilance_default.csv',
        )

        with dpg.node(
            tag=tag_node_name, parent=parent,
            label=node.node_label, pos=pos,
        ):
            # JSON input attribute
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value='JSON Input (description)',
                )

            # Model name
            with dpg.node_attribute(
                tag=tag_node_name + ':ModelName',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_model_name,
                    default_value=TinyBertVigilanceNode.DEFAULT_MODEL,
                    width=240,
                    label='Model',
                )

            # CSV path input
            with dpg.node_attribute(
                tag=tag_node_name + ':CsvPath',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_input_text(
                    tag=tag_csv_path,
                    default_value=default_csv,
                    width=240,
                    label='CSV',
                )

            # Load button
            with dpg.node_attribute(
                tag=tag_node_name + ':LoadBtn',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=tag_node_name + ':LoadBtnValue',
                    label='Load Database',
                    width=240,
                    callback=_on_load_click,
                    user_data=node,
                )

            # Status indicator
            with dpg.node_attribute(
                tag=tag_node_name + ':Status',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=tag_status,
                    default_value='Not loaded',
                )

            # JSON output attribute
            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='Vigilance Output',
                )

        return node


class TinyBertVigilanceNode(BaseNode):
    _ver = '0.0.1'

    DEFAULT_MODEL = 'huawei-noah/TinyBERT_General_4L_312D'

    def __init__(self):
        super().__init__()
        self.node_label = 'TinyBert Vigilance'
        self.node_tag = 'TinyBertVigilance'
        self._tokenizer = None
        self._model = None
        self._vectors = None
        self._scores = None
        self._nn_index = None
        self._is_loaded = False
        self._is_loading = False
        self._load_requested = False
        self._load_result = {}
        self._load_thread = None

    @staticmethod
    def _map_score_to_vigilance(score_0_10):
        """Map a 0-10 raw score to a 1-5 vigilance level.

        1 = normal, 2 = unusual activity, 3 = probable danger,
        4 = physical integrity danger, 5 = danger of death.
        """
        if score_0_10 <= 2:
            return 1
        elif score_0_10 <= 4:
            return 2
        elif score_0_10 <= 6:
            return 3
        elif score_0_10 <= 8:
            return 4
        else:
            return 5

    def _encode_text(self, text):
        """Encode a single text using TinyBERT and return a normalized vector."""
        import torch
        inputs = self._tokenizer(
            text, return_tensors='pt', truncation=True,
            max_length=128, padding=True,
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
        attention_mask = inputs['attention_mask']
        token_embeddings = outputs.last_hidden_state
        mask_expanded = attention_mask.unsqueeze(-1).expand(
            token_embeddings.size(),
        ).float()
        sum_embeddings = torch.sum(token_embeddings * mask_expanded, 1)
        sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
        vector = (sum_embeddings / sum_mask).numpy()[0]
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def _find_nearest_score(self, query_vector):
        """Find the nearest neighbor and return its raw vigilance score."""
        if self._nn_index is not None:
            # Use sklearn index for large databases (>300 phrases)
            distances, indices = self._nn_index.kneighbors([query_vector])
            return self._scores[indices[0][0]]
        else:
            # Brute force cosine similarity (vectors are already normalized)
            similarities = self._vectors @ query_vector
            idx = int(np.argmax(similarities))
            return self._scores[idx]

    def update(
        self, node_id, connection_list, node_image_dict,
        node_result_dict, node_audio_dict,
    ):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        tag_status = '{}:StatusValue'.format(tag_node_name)
        tag_csv_path = '{}:CsvPathValue'.format(tag_node_name)
        tag_model_name = '{}:ModelNameValue'.format(tag_node_name)

        # Handle loading request
        if self._load_requested and not self._is_loading:
            self._load_requested = False
            self._is_loading = True
            self._is_loaded = False
            self._load_result = {}

            csv_path = dpg_get_value(tag_csv_path) or ''
            model_name = dpg_get_value(tag_model_name) or self.DEFAULT_MODEL

            dpg_set_value(tag_status, 'Loading...')

            self._load_thread = threading.Thread(
                target=_load_model_and_build_db,
                args=(self._load_result, csv_path, model_name),
                daemon=True,
            )
            self._load_thread.start()

        # Check loading progress
        if self._is_loading:
            if 'error' in self._load_result:
                dpg_set_value(tag_status, self._load_result['error'])
                self._is_loading = False
            elif self._load_result.get('done'):
                self._tokenizer = self._load_result['tokenizer']
                self._model = self._load_result['model']
                self._vectors = self._load_result['vectors']
                self._scores = self._load_result['scores']
                self._nn_index = self._load_result['nn_index']
                self._is_loaded = True
                self._is_loading = False
                dpg_set_value(
                    tag_status,
                    self._load_result.get('status', 'Loaded'),
                )
            elif 'status' in self._load_result:
                dpg_set_value(tag_status, self._load_result['status'])
            return {"image": None, "json": None, "audio": None}

        # If not loaded, nothing to process
        if not self._is_loaded:
            return {"image": None, "json": None, "audio": None}

        # Find connected JSON input
        input_json = {}
        for connection_info in connection_list:
            parts = connection_info[0].split(':')
            if len(parts) < 3:
                continue
            connection_type = parts[2]
            target = connection_info[1]
            if connection_type == self.TYPE_JSON and 'InputJson' in target:
                src_key = ':'.join(parts[:2])
                input_json = node_result_dict.get(src_key, {})
                break

        if not input_json or not isinstance(input_json, dict):
            return {"image": None, "json": None, "audio": None}

        # Extract description text (compatible with VLM output and custom input)
        description = (
            input_json.get('description')
            or input_json.get('TEXT')
            or ''
        )
        if not description:
            return {"image": None, "json": None, "audio": None}

        # Encode and find nearest neighbor
        try:
            query_vector = self._encode_text(description)
            raw_score = float(self._find_nearest_score(query_vector))
            vigilance = self._map_score_to_vigilance(raw_score)
            json_out = {"vigilance": vigilance}
            dpg_set_value(
                tag_status,
                'Vigilance: {} (raw: {:.1f})'.format(vigilance, raw_score),
            )
            return {"image": None, "json": json_out, "audio": None}
        except Exception as exc:
            dpg_set_value(
                tag_status,
                'Error: {}'.format(str(exc)[:40]),
            )
            return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        """Clean up resources."""
        self._model = None
        self._tokenizer = None
        self._vectors = None
        self._scores = None
        self._nn_index = None

    def get_setting_dict(self, node_id):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        tag_csv_path = '{}:CsvPathValue'.format(tag_node_name)
        tag_model_name = '{}:ModelNameValue'.format(tag_node_name)

        pos = dpg.get_item_pos(tag_node_name)
        setting_dict = {
            'ver': self._ver,
            'pos': pos,
            tag_csv_path: dpg_get_value(tag_csv_path),
            tag_model_name: dpg_get_value(tag_model_name),
        }
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = '{}:{}'.format(node_id, self.node_tag)
        tag_csv_path = '{}:CsvPathValue'.format(tag_node_name)
        tag_model_name = '{}:ModelNameValue'.format(tag_node_name)

        dpg_set_value(
            tag_csv_path,
            setting_dict.get(tag_csv_path, ''),
        )
        dpg_set_value(
            tag_model_name,
            setting_dict.get(tag_model_name, self.DEFAULT_MODEL),
        )
