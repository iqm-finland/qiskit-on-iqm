# Copyright 2024 Qiskit on IQM developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Collection of utility functions"""

from typing import TypeVar

T = TypeVar('T')


def sort_list(input_list: list[T]) -> list[T]:
    """Creates a copy of the list, sorts it, and returns it without changing the original list"""
    r = list(input_list)
    r.sort()
    return r


def is_multi_qubit_operation(operation: str):
    """Checks whether the given operation is a multi-qubit operation"""
    return operation in ['cz', 'move']


def is_directed_operation(operation: str):
    """Checks whether the given operation is directed"""
    return operation == 'move'
