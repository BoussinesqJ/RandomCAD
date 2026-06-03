# tests/test_quadtree.py
"""测试 src/core/quadtree.py 四叉树空间索引"""

import pytest
from src.core.quadtree import Quadtree, QuadtreeNode


class TestQuadtreeNode:
    def test_init(self):
        node = QuadtreeNode((0, 0, 100, 100))
        assert node.bounds == (0, 0, 100, 100)
        assert node.is_divided is False
        assert len(node.objects) == 0

    def test_insert_single(self):
        node = QuadtreeNode((0, 0, 100, 100))
        obj = {'shapely_obj': type('Mock', (), {'bounds': (10, 10, 20, 20)})()}
        assert node.insert(obj) is True
        assert len(node.objects) == 1

    def test_split_after_max_objects(self):
        node = QuadtreeNode((0, 0, 100, 100), max_objects=2)
        for i in range(3):
            obj = {'shapely_obj': type('Mock', (), {'bounds': (i*10, i*10, i*10+5, i*10+5)})()}
            node.insert(obj)
        assert node.is_divided is True

    def test_clear(self):
        node = QuadtreeNode((0, 0, 100, 100))
        obj = {'shapely_obj': type('Mock', (), {'bounds': (10, 10, 20, 20)})()}
        node.insert(obj)
        node.clear()
        assert len(node.objects) == 0


class TestQuadtree:
    def test_init(self):
        qt = Quadtree((0, 0, 100, 100))
        assert qt.bounds == (0, 0, 100, 100)

    def test_insert_and_query(self):
        qt = Quadtree((0, 0, 100, 100))
        obj = {'shapely_obj': type('Mock', (), {'bounds': (10, 10, 20, 20)})()}
        qt.insert(obj)
        results = qt.query_range((0, 0, 50, 50))
        assert len(results) == 1

    def test_query_empty(self):
        qt = Quadtree((0, 0, 100, 100))
        results = qt.query_range((0, 0, 50, 50))
        assert len(results) == 0

    def test_insert_batch(self):
        qt = Quadtree((0, 0, 100, 100))
        objects = [
            {'shapely_obj': type('Mock', (), {'bounds': (i*5, i*5, i*5+3, i*5+3)})()}
            for i in range(10)
        ]
        count = qt.insert_batch(objects)
        assert count == 10

    def test_clear(self):
        qt = Quadtree((0, 0, 100, 100))
        obj = {'shapely_obj': type('Mock', (), {'bounds': (10, 10, 20, 20)})()}
        qt.insert(obj)
        qt.clear()
        results = qt.query_range((0, 0, 100, 100))
        assert len(results) == 0

    def test_get_stats(self):
        qt = Quadtree((0, 0, 100, 100))
        stats = qt.get_stats()
        assert 'total_objects' in stats
        assert stats['total_objects'] == 0
