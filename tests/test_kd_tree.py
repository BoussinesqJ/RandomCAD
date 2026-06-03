# tests/test_kd_tree.py
"""测试 src/core/kd_tree.py KD树空间索引"""

import pytest
from src.core.kd_tree import KDTree


class TestKDTree:
    def test_init(self):
        kdt = KDTree((0, 0, 100, 100))
        assert kdt.bounds == (0, 0, 100, 100)

    def test_insert_and_query(self):
        kdt = KDTree((0, 0, 100, 100))
        obj = {'shapely_obj': type('Mock', (), {'bounds': (10, 10, 20, 20)})()}
        kdt.insert(obj)
        results = kdt.query_range((0, 0, 50, 50))
        assert len(results) == 1

    def test_query_empty(self):
        kdt = KDTree((0, 0, 100, 100))
        results = kdt.query_range((0, 0, 50, 50))
        assert len(results) == 0

    def test_insert_batch(self):
        kdt = KDTree((0, 0, 100, 100))
        objects = [
            {'shapely_obj': type('Mock', (), {'bounds': (i*5, i*5, i*5+3, i*5+3)})()}
            for i in range(10)
        ]
        count = kdt.insert_batch(objects)
        assert count == 10

    def test_clear(self):
        kdt = KDTree((0, 0, 100, 100))
        obj = {'shapely_obj': type('Mock', (), {'bounds': (10, 10, 20, 20)})()}
        kdt.insert(obj)
        kdt.clear()
        results = kdt.query_range((0, 0, 100, 100))
        assert len(results) == 0

    def test_get_stats(self):
        kdt = KDTree((0, 0, 100, 100))
        stats = kdt.get_stats()
        assert 'total_objects' in stats
        assert stats['total_objects'] == 0

    def test_spatial_index_protocol(self):
        """验证 KDTree 符合 SpatialIndex 协议"""
        from src.core.spatial_index import SpatialIndex
        kdt = KDTree((0, 0, 100, 100))
        assert isinstance(kdt, SpatialIndex)
