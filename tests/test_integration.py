"""
集成测试

测试 GroupManager 和 RandomAggregateGenerator 的核心流程
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from src.core.generator import RandomAggregateGenerator
from src.core.group_manager import GroupManager


def _make_valid_config():
    """创建有效的组配置"""
    return [{
        'area_ratio': 40.0,
        'itz_thickness': 0.5,
        'max_count': 10,
        'layer_color': 1,
        'shapes': [
            {'type': 'polygon', 'weight': 1.0},
        ],
    }]


class TestGroupManager(unittest.TestCase):
    """GroupManager 核心功能测试"""

    def setUp(self):
        self.manager = GroupManager()

    def test_set_and_get_config(self):
        """set_config + get_config 往返一致"""
        config = _make_valid_config()
        self.manager.set_config(config)
        result = self.manager.get_config()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['area_ratio'], 40.0)
        self.assertEqual(result[0]['itz_thickness'], 0.5)

    def test_validate_config_valid(self):
        """有效配置应通过验证"""
        config = _make_valid_config()
        self.manager.set_config(config)
        self.assertTrue(self.manager.validate_config())

    def test_validate_config_empty(self):
        """空配置不应通过验证"""
        self.assertFalse(self.manager.validate_config())

    def test_validate_config_no_shapes(self):
        """没有 shape 的配置不应通过验证"""
        config = [{
            'area_ratio': 40.0,
            'itz_thickness': 0.5,
            'max_count': 10,
            'layer_color': 1,
            'shapes': [],
        }]
        self.manager.set_config(config)
        self.assertFalse(self.manager.validate_config())

    def test_select_next_group_count_mode(self):
        """count 模式下 select_next_group 应返回配置"""
        config = _make_valid_config()
        self.manager.set_config(config)
        selected = self.manager.select_next_group("count")
        self.assertIsNotNone(selected)
        self.assertEqual(selected['id'], 1)

    def test_select_next_group_none_available(self):
        """当所有组都达到 max_count 时应返回 None"""
        config = [{
            'area_ratio': 40.0,
            'itz_thickness': 0.5,
            'max_count': 2,
            'layer_color': 1,
            'shapes': [{'type': 'polygon', 'weight': 1.0}],
        }]
        self.manager.set_config(config)
        # 填满 max_count
        self.manager.update_group_stats(1, 10.0)
        self.manager.update_group_stats(1, 10.0)
        selected = self.manager.select_next_group("count")
        self.assertIsNone(selected)

    def test_reset_group_stats(self):
        """reset_group_stats 应清零所有统计数据"""
        config = [{
            'area_ratio': 40.0,
            'itz_thickness': 0.5,
            'max_count': 10,
            'layer_color': 1,
            'shapes': [{'type': 'polygon', 'weight': 1.0}],
        }]
        self.manager.set_config(config)
        self.manager.update_group_stats(1, 50.0)
        self.manager.update_group_stats(1, 30.0)

        configs = self.manager.get_config()
        self.assertEqual(configs[0]['generated_area'], 80.0)
        self.assertEqual(configs[0]['count'], 2)

        self.manager.reset_group_stats()
        configs = self.manager.get_config()
        self.assertEqual(configs[0]['generated_area'], 0.0)
        self.assertEqual(configs[0]['count'], 0)

    def test_config_missing_required_field_raises(self):
        """缺少必填字段应抛出 ValueError"""
        config = [{
            'area_ratio': 40.0,
            # 缺少 itz_thickness 等字段
        }]
        with self.assertRaises(ValueError):
            self.manager.set_config(config)


class TestGeneratorInit(unittest.TestCase):
    """RandomAggregateGenerator 初始化测试"""

    def test_generator_init_no_cad(self):
        """auto_start=False 不应连接 CAD"""
        generator = RandomAggregateGenerator(auto_start=False, cad_type="autocad")
        self.assertIsNotNone(generator)
        self.assertEqual(generator.generation_mode, "count")

    def test_set_groups_delegates_to_manager(self):
        """set_groups 应通过 GroupManager.set_config 设置"""
        generator = RandomAggregateGenerator(auto_start=False, cad_type="autocad")
        config = _make_valid_config()
        generator.set_groups(config)
        result = generator.groups.get_config()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['area_ratio'], 40.0)


if __name__ == '__main__':
    unittest.main()
