"""
GPU vs CPU 性能基准测试脚本

用法:
    python benchmark_gpu.py

比较 GPU 加速和 CPU 模式下骨料生成的碰撞检测性能。
"""

import sys
import os
import time
import statistics

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.generator import RandomAggregateGenerator


def run_benchmark(use_gpu: bool, num_runs: int = 3) -> dict:
    """
    运行一次基准测试

    Args:
        use_gpu: 是否使用 GPU
        num_runs: 重复运行次数（取平均值）

    Returns:
        包含平均耗时和统计数据的字典
    """
    times = []
    counts = []

    for i in range(num_runs):
        gen = RandomAggregateGenerator(auto_start=False, cad_type="autocad")
        gen.set_use_gpu(use_gpu)
        gen.set_generation_mode("count")

        # 配置测试组：生成 200 个混合形状骨料
        groups = [
            {
                'id': 1,
                'max_count': 100,
                'area_ratio': 0.5,
                'layer_color': '红色',
                'itz_thickness': 0.0,
                'shapes': [
                    {
                        'type': 'polygon',
                        'enabled': True,
                        'weight': 1.0,
                        'min_radius': 2.0,
                        'max_radius': 5.0,
                        'sides_min': 5,
                        'sides_max': 8,
                        'elongation_min': 1.0,
                        'elongation_max': 1.5
                    }
                ]
            },
            {
                'id': 2,
                'max_count': 100,
                'area_ratio': 0.5,
                'layer_color': '绿色',
                'itz_thickness': 0.0,
                'shapes': [
                    {
                        'type': 'circle',
                        'enabled': True,
                        'weight': 1.0,
                        'min_radius': 1.5,
                        'max_radius': 4.0,
                        'sides_min': 5,
                        'sides_max': 8,
                        'elongation_min': 1.0,
                        'elongation_max': 1.5
                    }
                ]
            }
        ]
        gen.set_groups(groups)

        start = time.perf_counter()
        count = gen.generate_aggregates_in_region(
            region_min=(0, 0),
            region_max=(100, 100),
            min_distance=0.5,
            max_attempts=200,
            boundary_adjust=False,
            allow_touching=True,
            progress_callback=None,
            draw_callback=None
        )
        elapsed = time.perf_counter() - start

        times.append(elapsed)
        counts.append(count)
        print(f"  Run {i + 1}/{num_runs}: {elapsed:.3f}s, {count} aggregates")

    return {
        'mean_time': statistics.mean(times),
        'stdev_time': statistics.stdev(times) if len(times) > 1 else 0.0,
        'min_time': min(times),
        'max_time': max(times),
        'mean_count': statistics.mean(counts),
        'times': times,
        'counts': counts
    }


def main():
    print("=" * 60)
    print("RandomCAD GPU vs CPU 性能基准测试")
    print("=" * 60)

    # 检查 PyTorch 和 CUDA
    try:
        import torch
        print(f"\nPyTorch 版本: {torch.__version__}")
        print(f"CUDA 可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU 名称: {torch.cuda.get_device_name(0)}")
            print(f"GPU 显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    except ImportError:
        print("\n[WARN] PyTorch 未安装，无法测试 GPU 模式")
        print("仅运行 CPU 基准测试\n")

    num_runs = 3

    # CPU 基准测试
    print(f"\n{'---' * 14}")
    print("[CPU] CPU 模式基准测试 ({} 次运行)".format(num_runs))
    print(f"{'---' * 14}")
    cpu_results = run_benchmark(use_gpu=False, num_runs=num_runs)

    # GPU 基准测试
    gpu_results = None
    try:
        import torch
        if torch.cuda.is_available():
            print(f"\n{'---' * 14}")
            print("[GPU] GPU 模式基准测试 ({} 次运行)".format(num_runs))
            print(f"{'---' * 14}")
            gpu_results = run_benchmark(use_gpu=True, num_runs=num_runs)
    except ImportError:
        pass

    # 输出汇总结果
    print(f"\n{'=' * 60}")
    print("[RESULT] 基准测试结果汇总")
    print(f"{'=' * 60}")

    print(f"\n[CPU] CPU 模式:")
    print(f"   平均耗时: {cpu_results['mean_time']:.3f}s ± {cpu_results['stdev_time']:.3f}s")
    print(f"   最快/最慢: {cpu_results['min_time']:.3f}s / {cpu_results['max_time']:.3f}s")
    print(f"   平均骨料数: {cpu_results['mean_count']:.0f}")

    if gpu_results:
        print(f"\n[GPU] GPU 模式:")
        print(f"   平均耗时: {gpu_results['mean_time']:.3f}s ± {gpu_results['stdev_time']:.3f}s")
        print(f"   最快/最慢: {gpu_results['min_time']:.3f}s / {gpu_results['max_time']:.3f}s")
        print(f"   平均骨料数: {gpu_results['mean_count']:.0f}")

        speedup = cpu_results['mean_time'] / gpu_results['mean_time'] if gpu_results['mean_time'] > 0 else float('inf')
        print(f"\n>>> 加速比: {speedup:.2f}x", end="")
        if speedup > 1:
            print(f"  (GPU 快 {(speedup - 1) * 100:.0f}%)")
        else:
            print(f"  (CPU 更快 {(1 - speedup) * 100:.0f}%)")
            print("   注意: 在骨料数量较少时，GPU 的数据传输开销可能大于计算收益。")
            print("   GPU 加速在 500+ 骨料时效果更加显著。")
    else:
        print("\n[WARN] GPU 基准测试未运行 (CUDA 不可用)")

    print(f"\n{'=' * 60}")
    print("基准测试完成。")


if __name__ == "__main__":
    main()
