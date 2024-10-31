"""Testing utility functions for investigating transpiled circuits.
"""

from .utils import AllowedOps, _coerce_to_allowed_ops, _get_allowed_ops, _map_operations_to_indices, get_mocked_backend

ALLOWED_OPS = AllowedOps(
    cz=[
        (1, 0),
        (0, 1),
        (2, 0),
        (0, 2),
        (3, 0),
        (0, 3),
        (4, 0),
        (0, 4),
        (5, 0),
        (0, 5),
        (6, 0),
        (0, 6),
    ],
    prx=[1, 2, 3, 4, 5, 6],
    move=[
        (1, 0),
        (2, 0),
        (3, 0),
        (4, 0),
        (5, 0),
        (6, 0),
    ],
    measure=[1, 2, 3, 4, 5, 6],
)

ALLOWED_OPS_AS_NESTED_LISTS = {
    "cz": [
        [1, 0],
        [2, 0],
        [3, 0],
        [4, 0],
        [5, 0],
        [6, 0],
    ],
    "prx": [[1], [2], [3], [4], [5], [6]],
    "move": [
        [1, 0],
        [2, 0],
        [3, 0],
        [4, 0],
        [5, 0],
        [6, 0],
    ],
    "measure": [[1], [2], [3], [4], [5], [6]],
}


def test_get_allowed_ops(ndonis_architecture):
    backend, _client = get_mocked_backend(ndonis_architecture)
    allowed_ops = _get_allowed_ops(backend)
    assert ALLOWED_OPS == allowed_ops


def test_coerce_to_allowed_ops():
    actual = _coerce_to_allowed_ops(ALLOWED_OPS_AS_NESTED_LISTS)
    assert ALLOWED_OPS == actual


def test_map_operators_to_indices(ndonis_architecture):
    backend, _client = get_mocked_backend(ndonis_architecture)
    as_indices = _map_operations_to_indices(backend.architecture.gates, backend.architecture.components)
    assert ALLOWED_OPS_AS_NESTED_LISTS == as_indices
