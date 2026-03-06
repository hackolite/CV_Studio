#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for TinyBert Vigilance node core logic."""

import csv
import os
import sys
import unittest.mock as mock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock DearPyGui and related modules before importing the node
sys.modules.setdefault('dearpygui', mock.MagicMock())
sys.modules.setdefault('dearpygui.dearpygui', mock.MagicMock())
sys.modules.setdefault('node_editor', mock.MagicMock())
sys.modules.setdefault('node_editor.util', mock.MagicMock())
sys.modules.setdefault('node.node_abc', mock.MagicMock())
sys.modules.setdefault('cv2', mock.MagicMock())

from node.NLPModelNode.node_tinybert_vigilance import (
    TinyBertVigilanceNode,
    FactoryNode,
    _on_db_combo_change,
    _DB_CACHE,
    _MODEL_CACHE,
)


# ---------------------------------------------------------------------------
# Score mapping (0-10 → 1-5)
# ---------------------------------------------------------------------------

def test_map_score_level_1():
    """Scores 0-2 should map to vigilance level 1 (normal)."""
    assert TinyBertVigilanceNode._map_score_to_vigilance(0) == 1
    assert TinyBertVigilanceNode._map_score_to_vigilance(1) == 1
    assert TinyBertVigilanceNode._map_score_to_vigilance(2) == 1


def test_map_score_level_2():
    """Scores 3-4 should map to vigilance level 2 (unusual activity)."""
    assert TinyBertVigilanceNode._map_score_to_vigilance(3) == 2
    assert TinyBertVigilanceNode._map_score_to_vigilance(4) == 2


def test_map_score_level_3():
    """Scores 5-6 should map to vigilance level 3 (probable danger)."""
    assert TinyBertVigilanceNode._map_score_to_vigilance(5) == 3
    assert TinyBertVigilanceNode._map_score_to_vigilance(6) == 3


def test_map_score_level_4():
    """Scores 7-8 should map to vigilance level 4 (physical integrity danger)."""
    assert TinyBertVigilanceNode._map_score_to_vigilance(7) == 4
    assert TinyBertVigilanceNode._map_score_to_vigilance(8) == 4


def test_map_score_level_5():
    """Scores 9-10 should map to vigilance level 5 (danger of death)."""
    assert TinyBertVigilanceNode._map_score_to_vigilance(9) == 5
    assert TinyBertVigilanceNode._map_score_to_vigilance(10) == 5


def test_map_score_float_values():
    """Float scores should be handled correctly by threshold comparison."""
    assert TinyBertVigilanceNode._map_score_to_vigilance(2.5) == 2
    assert TinyBertVigilanceNode._map_score_to_vigilance(4.9) == 3
    assert TinyBertVigilanceNode._map_score_to_vigilance(6.1) == 4
    assert TinyBertVigilanceNode._map_score_to_vigilance(8.5) == 5


def test_map_score_boundary_values():
    """Boundary values should map to the correct level."""
    assert TinyBertVigilanceNode._map_score_to_vigilance(2.0) == 1
    assert TinyBertVigilanceNode._map_score_to_vigilance(2.01) == 2
    assert TinyBertVigilanceNode._map_score_to_vigilance(4.0) == 2
    assert TinyBertVigilanceNode._map_score_to_vigilance(4.01) == 3


# ---------------------------------------------------------------------------
# Nearest neighbor search
# ---------------------------------------------------------------------------

def test_find_nearest_score_brute_force():
    """Brute force nearest neighbor should return the score of the closest vector."""
    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)
    node._nn_index = None

    # Create 3 normalized vectors and scores
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    v3 = np.array([0.0, 0.0, 1.0])
    node._vectors = np.array([v1, v2, v3])
    node._scores = np.array([2.0, 5.0, 9.0])

    # Query closest to v1
    query = np.array([0.9, 0.1, 0.0])
    query = query / np.linalg.norm(query)
    score = node._find_nearest_score(query)
    assert score == 2.0

    # Query closest to v3
    query = np.array([0.0, 0.1, 0.9])
    query = query / np.linalg.norm(query)
    score = node._find_nearest_score(query)
    assert score == 9.0


def test_find_nearest_score_with_sklearn_index():
    """When nn_index is set (>300 phrases), it should be used."""
    from sklearn.neighbors import NearestNeighbors

    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)

    # Create vectors and build sklearn index
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    v3 = np.array([0.0, 0.0, 1.0])
    vectors = np.array([v1, v2, v3])
    node._vectors = vectors
    node._scores = np.array([1.0, 6.0, 10.0])
    node._nn_index = NearestNeighbors(
        n_neighbors=1, metric='cosine', algorithm='brute',
    )
    node._nn_index.fit(vectors)

    # Query closest to v2
    query = np.array([0.1, 0.9, 0.0])
    query = query / np.linalg.norm(query)
    score = node._find_nearest_score(query)
    assert score == 6.0


# ---------------------------------------------------------------------------
# Default CSV file
# ---------------------------------------------------------------------------

def test_default_csv_exists():
    """The default vigilance CSV should exist alongside the node module."""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'NLPModelNode', 'vigilance_default.csv',
    )
    assert os.path.exists(csv_path), 'vigilance_default.csv not found'


def test_default_csv_has_100_rows():
    """The default CSV should contain exactly 100 phrases."""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'NLPModelNode', 'vigilance_default.csv',
    )
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 100


def test_default_csv_has_required_columns():
    """The CSV must have 'vigilance' and 'sentence' columns."""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'NLPModelNode', 'vigilance_default.csv',
    )
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        row = next(reader)
    assert 'vigilance' in row
    assert 'sentence' in row


def test_default_csv_scores_in_range():
    """All vigilance scores in the CSV should be between 0 and 10."""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'NLPModelNode', 'vigilance_default.csv',
    )
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            score = float(row['vigilance'])
            assert 0 <= score <= 10, 'Score {} out of range'.format(score)


# ---------------------------------------------------------------------------
# Node constants and metadata
# ---------------------------------------------------------------------------

def test_node_tag():
    assert TinyBertVigilanceNode().node_tag == 'TinyBertVigilance'


def test_node_label():
    assert TinyBertVigilanceNode().node_label == 'TinyBert Vigilance'


def test_default_model():
    assert TinyBertVigilanceNode.DEFAULT_MODEL == 'huawei-noah/TinyBERT_General_4L_312D'


def test_factory_node_tag():
    factory = FactoryNode()
    assert factory.node_tag == 'TinyBertVigilance'


def test_factory_node_label():
    factory = FactoryNode()
    assert factory.node_label == 'TinyBert Vigilance'


# ---------------------------------------------------------------------------
# Update logic (without model)
# ---------------------------------------------------------------------------

def test_update_returns_none_when_not_loaded():
    """Before loading, update should return all None."""
    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)
    node.node_tag = 'TinyBertVigilance'
    node._is_loaded = False
    node._is_loading = False
    node._load_requested = False
    node._db_select_requested = False
    node._selected_db_name = None
    node._last_db_cache_size = 0
    node.tag_db_combo = None

    with mock.patch(
        'node.NLPModelNode.node_tinybert_vigilance.dpg_get_value',
        return_value='test',
    ), mock.patch(
        'node.NLPModelNode.node_tinybert_vigilance.dpg_set_value',
    ):
        result = node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={},
        )

    assert result == {"image": None, "json": None, "audio": None}


def test_update_returns_vigilance_when_loaded():
    """When loaded and connected, update should return vigilance score."""
    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)
    node.node_tag = 'TinyBertVigilance'
    node._is_loaded = True
    node._is_loading = False
    node._load_requested = False
    node._db_select_requested = False
    node._selected_db_name = None
    node._last_db_cache_size = 0
    node.tag_db_combo = None
    node._nn_index = None

    # Mock vectors/scores: one vector close to what _encode_text would return
    node._vectors = np.array([[1.0, 0.0, 0.0]])
    node._scores = np.array([7.0])  # Should map to vigilance 4

    # Mock _encode_text to return a known vector
    mock_vector = np.array([1.0, 0.0, 0.0])
    node._encode_text = mock.MagicMock(return_value=mock_vector)

    # Create a connection from a VLM node
    connection_list = [
        ['1:VLM:JSON:OutputJson', '2:TinyBertVigilance:JSON:InputJson']
    ]
    node_result_dict = {
        '1:VLM': {'TEXT': 'A person is attacking with a weapon'}
    }

    with mock.patch(
        'node.NLPModelNode.node_tinybert_vigilance.dpg_get_value',
        return_value='test',
    ), mock.patch(
        'node.NLPModelNode.node_tinybert_vigilance.dpg_set_value',
    ):
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )

    assert result['json'] == {"vigilance": 4}
    node._encode_text.assert_called_once_with(
        'A person is attacking with a weapon',
    )


def test_update_handles_description_key():
    """Input with 'description' key should be handled."""
    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)
    node.node_tag = 'TinyBertVigilance'
    node._is_loaded = True
    node._is_loading = False
    node._load_requested = False
    node._db_select_requested = False
    node._selected_db_name = None
    node._last_db_cache_size = 0
    node.tag_db_combo = None
    node._nn_index = None
    node._vectors = np.array([[1.0, 0.0, 0.0]])
    node._scores = np.array([0.0])  # vigilance 1

    mock_vector = np.array([1.0, 0.0, 0.0])
    node._encode_text = mock.MagicMock(return_value=mock_vector)

    connection_list = [
        ['1:Source:JSON:OutputJson', '2:TinyBertVigilance:JSON:InputJson']
    ]
    node_result_dict = {
        '1:Source': {'description': 'A calm restaurant scene'}
    }

    with mock.patch(
        'node.NLPModelNode.node_tinybert_vigilance.dpg_get_value',
        return_value='test',
    ), mock.patch(
        'node.NLPModelNode.node_tinybert_vigilance.dpg_set_value',
    ):
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )

    assert result['json'] == {"vigilance": 1}
    node._encode_text.assert_called_once_with('A calm restaurant scene')


# ---------------------------------------------------------------------------
# DB cache and model cache
# ---------------------------------------------------------------------------


def _make_fake_db(sentence_count=5, dim=4):
    """Return a minimal fake DB cache entry."""
    vectors = np.random.rand(sentence_count, dim).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    scores = np.arange(sentence_count, dtype=float)
    return {
        'vectors': vectors,
        'scores': scores,
        'nn_index': None,
        'sentence_count': sentence_count,
    }


def test_load_model_and_build_db_stores_in_db_cache(tmp_path):
    """After a successful load the real function populates _DB_CACHE."""
    import node.NLPModelNode.node_tinybert_vigilance as mod

    csv_file = tmp_path / 'test_cache_store.csv'
    csv_file.write_text('vigilance,sentence\n0,Hello world\n5,Danger here\n')

    db_name = 'test_cache_store'

    # ---- Fake tensors that behave like torch Tensors for mean-pooling ----
    class FakeTensor:
        """Wraps a numpy array to satisfy the mean-pooling ops in the node."""
        def __init__(self, arr):
            self._arr = np.asarray(arr, dtype=np.float32)

        def unsqueeze(self, dim):
            return FakeTensor(np.expand_dims(self._arr, axis=dim))

        def expand(self, *shape):
            # handle expand(tuple) vs expand(d0, d1, d2)
            if len(shape) == 1 and isinstance(shape[0], tuple):
                shape = shape[0]
            return FakeTensor(np.broadcast_to(self._arr, shape).copy())

        def float(self):
            return self

        def sum(self, dim=None):
            return FakeTensor(self._arr.sum(axis=dim))

        def size(self):
            return self._arr.shape

        def numpy(self):
            return self._arr

        def __mul__(self, other):
            return FakeTensor(self._arr * other._arr)

        def __truediv__(self, other):
            return FakeTensor(self._arr / other._arr)

    # 1 sentence, 2 tokens, 4-dim hidden states
    hidden = FakeTensor(np.ones((1, 2, 4)))
    attn_mask = FakeTensor(np.ones((1, 2)))

    fake_outputs = mock.MagicMock()
    fake_outputs.last_hidden_state = hidden

    fake_model = mock.MagicMock()
    fake_model.return_value = fake_outputs

    fake_tokenizer = mock.MagicMock()
    fake_tokenizer.return_value = {'attention_mask': attn_mask,
                                   'input_ids': mock.MagicMock()}

    fake_torch = mock.MagicMock()
    fake_torch.no_grad.return_value.__enter__ = mock.MagicMock(return_value=None)
    fake_torch.no_grad.return_value.__exit__ = mock.MagicMock(return_value=False)
    fake_torch.sum = lambda t, dim: t.sum(dim)
    fake_torch.clamp = lambda t, min: FakeTensor(
        np.clip(t._arr, a_min=min, a_max=None)
    )

    fake_transformers = mock.MagicMock()
    fake_transformers.AutoTokenizer.from_pretrained.return_value = fake_tokenizer
    fake_transformers.AutoModel.from_pretrained.return_value = fake_model

    import sys
    with mock.patch.dict(mod._DB_CACHE, {}, clear=True), \
         mock.patch.dict(mod._MODEL_CACHE, {}, clear=True), \
         mock.patch.dict(
             sys.modules,
             {'torch': fake_torch, 'transformers': fake_transformers},
         ):
        result_dict = {}
        mod._load_model_and_build_db(result_dict, str(csv_file), 'fake-model')

        # Assert inside the context while the patched dict is still active
        assert result_dict.get('done') is True, result_dict.get('error', '')
        assert db_name in mod._DB_CACHE
        assert mod._DB_CACHE[db_name]['sentence_count'] == 2


def test_load_model_and_build_db_cache_hit(tmp_path):
    """If the CSV name is already in _DB_CACHE, vectorization is skipped."""
    import node.NLPModelNode.node_tinybert_vigilance as mod

    db_name = 'already_cached'
    cached_entry = _make_fake_db(3)

    fake_tokenizer = mock.MagicMock()
    fake_model = mock.MagicMock()

    # Patch torch and transformers so the function can run without them installed
    fake_torch = mock.MagicMock()
    fake_transformers = mock.MagicMock()

    with mock.patch.dict(mod._DB_CACHE, {db_name: cached_entry}, clear=True), \
         mock.patch.dict(
             mod._MODEL_CACHE,
             {'fake-model': {'tokenizer': fake_tokenizer, 'model': fake_model}},
         ), \
         mock.patch.dict(
             'sys.modules',
             {'torch': fake_torch, 'transformers': fake_transformers},
         ):
        csv_file = tmp_path / (db_name + '.csv')
        csv_file.write_text('vigilance,sentence\n0,x\n1,y\n2,z\n')

        result_dict = {}
        mod._load_model_and_build_db(result_dict, str(csv_file), 'fake-model')

    assert result_dict.get('done') is True
    assert 'from cache' in result_dict.get('status', '')
    assert result_dict['db_name'] == db_name
    # Vectors should come directly from the cache entry
    np.testing.assert_array_equal(
        result_dict['vectors'], cached_entry['vectors'],
    )


def test_on_db_combo_change_sets_flags():
    """Selecting a cached DB via the combobox sets the node's state flags."""
    import node.NLPModelNode.node_tinybert_vigilance as mod

    db_name = 'my_vigilance_db'
    fake_entry = _make_fake_db()

    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)
    node._selected_db_name = None
    node._db_select_requested = False

    with mock.patch.dict(mod._DB_CACHE, {db_name: fake_entry}):
        _on_db_combo_change(sender=None, app_data=db_name, user_data=node)

    assert node._selected_db_name == db_name
    assert node._db_select_requested is True


def test_on_db_combo_change_ignores_unknown_db():
    """Selecting a DB name not in the cache should be silently ignored."""
    import node.NLPModelNode.node_tinybert_vigilance as mod

    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)
    node._selected_db_name = None
    node._db_select_requested = False

    with mock.patch.dict(mod._DB_CACHE, {}, clear=True):
        _on_db_combo_change(sender=None, app_data='ghost_db', user_data=node)

    assert node._selected_db_name is None
    assert node._db_select_requested is False


def test_update_loads_from_cache_instantly():
    """When _db_select_requested is True, update() loads from cache without a thread."""
    import node.NLPModelNode.node_tinybert_vigilance as mod

    db_name = 'fast_db'
    fake_entry = _make_fake_db(4)

    node = TinyBertVigilanceNode.__new__(TinyBertVigilanceNode)
    node.node_tag = 'TinyBertVigilance'
    node._is_loaded = False
    node._is_loading = False
    node._load_requested = False
    node._load_result = {}
    node._selected_db_name = db_name
    node._db_select_requested = True
    node._last_db_cache_size = 0
    node.tag_db_combo = None  # no DPG widget in tests

    with mock.patch.dict(mod._DB_CACHE, {db_name: fake_entry}), \
         mock.patch(
             'node.NLPModelNode.node_tinybert_vigilance.dpg_get_value',
             return_value='',
         ), mock.patch(
             'node.NLPModelNode.node_tinybert_vigilance.dpg_set_value',
         ):
        result = node.update(
            node_id=1,
            connection_list=[],
            node_image_dict={},
            node_result_dict={},
            node_audio_dict={},
        )

    # After cache selection the node should be marked as loaded
    assert node._is_loaded is True
    assert node._db_select_requested is False
    np.testing.assert_array_equal(node._vectors, fake_entry['vectors'])
    np.testing.assert_array_equal(node._scores, fake_entry['scores'])
    # No input connected, so json output is None
    assert result == {"image": None, "json": None, "audio": None}


def test_node_new_state_attributes():
    """New state attributes must exist with correct defaults after __init__."""
    node = TinyBertVigilanceNode()
    assert node._selected_db_name is None
    assert node._db_select_requested is False
    assert node._last_db_cache_size == 0
    assert node.tag_db_combo is None


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
