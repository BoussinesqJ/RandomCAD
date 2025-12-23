# core/group_manager.py

import logging
import random
from typing import List, Dict, Any, Optional

class GroupManager:
    def __init__(self):
        self.groups: List[Dict[str, Any]] = []

    def set_config(self, groups_config: List[Dict[str, Any]]) -> None:
        """
        设置组配置
        
        Args:
            groups_config: 组配置列表，每个配置包含area_ratio、itz_thickness、max_count等字段
        """
        self.groups = []
        for i, conf in enumerate(groups_config):
            # 验证配置的必填字段
            required_fields = ['area_ratio', 'itz_thickness', 'max_count', 'layer_color', 'shapes']
            for field in required_fields:
                if field not in conf:
                    raise ValueError(f"组配置缺少必填字段: {field}")
            
            # 验证面积占比合理性
            if conf['area_ratio'] < 0:
                raise ValueError(f"组 {i+1} 的面积占比不能为负数")
            
            # 验证ITZ厚度合理性
            if conf['itz_thickness'] < 0:
                raise ValueError(f"组 {i+1} 的ITZ厚度不能为负数")
            
            group = {
                'id': i + 1,
                'area_ratio': conf['area_ratio'],
                'itz_thickness': conf['itz_thickness'],
                'max_count': conf['max_count'],
                'layer_color': conf['layer_color'],
                'shapes': conf['shapes'],
                # 运行时动态添加的属性
                'target_area': 0.0,
                'generated_area': 0.0,
                'count': 0,
                'shapes_and_itz': []
            }
            self.groups.append(group)
        logging.info(f"GroupManager: 已设置 {len(self.groups)} 个组")

    def get_config(self) -> List[Dict[str, Any]]:
        """
        获取组配置
        
        Returns:
            List[Dict[str, Any]]: 组配置列表
        """
        return self.groups

    def get_target_areas(self) -> Dict[int, float]:
        """
        获取各组的目标面积
        
        Returns:
            Dict[int, float]: 以组ID为键，目标面积为值的字典
        """
        return {g['id']: g['target_area'] for g in self.groups}

    def select_next_group(self, generation_mode: str = "count") -> Optional[Dict[str, Any]]:
        """
        根据生成模式选择下一个需要生成的组
        
        Args:
            generation_mode: 生成模式，可选值："count"（按数量）、"porosity"（按孔隙度）
            
        Returns:
            Optional[Dict[str, Any]]: 选中的组配置，没有可生成的组时返回None
        """
        if generation_mode == "porosity":
            # 孔隙度模式：优先选择生成进度低的组，确保各组按比例生成
            # 计算每个组的生成进度
            for g in self.groups:
                if g['target_area'] > 0:
                    g['progress'] = g['generated_area'] / g['target_area']
                else:
                    g['progress'] = 0.0
            
            # 按生成进度排序，优先选择进度低的组
            candidate_groups = sorted(self.groups, key=lambda g: g['progress'])
        else:
            # 数量模式：优先选择面积占比低的组
            candidate_groups = sorted(self.groups, key=lambda g: g['generated_area'] / g['target_area'] if g['target_area'] > 0 else 0)
        
        # 过滤掉已达到最大数量的组
        available_groups = [g for g in candidate_groups if g['count'] < g['max_count']]
        
        if available_groups:
            return available_groups[0]  # 返回进度最低的组，而不是随机选择
        return None

    def update_group_stats(self, group_id: int, area: float) -> bool:
        """
        更新指定组的统计数据
        
        Args:
            group_id: 组ID
            area: 新增的骨料面积
            
        Returns:
            bool: 更新成功返回True，未找到组返回False
        """
        for group in self.groups:
            if group['id'] == group_id:
                group['generated_area'] += area
                group['count'] += 1
                return True
        logging.warning(f"GroupManager: 未找到ID为 {group_id} 的组")
        return False

    def reset_group_stats(self) -> None:
        """
        重置所有组的统计数据
        """
        for group in self.groups:
            group['generated_area'] = 0.0
            group['count'] = 0
            group['shapes_and_itz'] = []
        logging.info("GroupManager: 已重置所有组的统计数据")

    def calculate_total_area_ratio(self) -> float:
        """
        计算所有组的面积占比总和
        
        Returns:
            float: 总面积占比
        """
        return sum(g['area_ratio'] for g in self.groups)

    def validate_config(self) -> bool:
        """
        验证组配置的合理性
        
        Returns:
            bool: 配置合理返回True，否则返回False
        """
        # 检查是否至少有一个组
        if not self.groups:
            logging.error("GroupManager: 没有配置任何组")
            return False
        
        # 检查每个组的形状配置
        for group in self.groups:
            if not group['shapes']:
                logging.error(f"GroupManager: 组 {group['id']} 没有配置任何形状")
                return False
            
            # 检查形状配置的有效性
            for shape in group['shapes']:
                if 'type' not in shape or 'weight' not in shape:
                    logging.error(f"GroupManager: 组 {group['id']} 的形状配置缺少必填字段")
                    return False
                
                if shape['weight'] < 0:
                    logging.error(f"GroupManager: 组 {group['id']} 的形状权重不能为负数")
                    return False
        
        return True