# 论文撰写模板（Objective 5）

> 本模板可直接复制到撰写工具中，按章节填入对应内容。建议在每个小节补充来自 FlowManager UI、脚本统计结果及实验截图的数据支撑。

## 摘要
- 简述研究背景、问题与解决思路
- 概述采用 FlowManager + Ryu 的 QoS 管理方案及实验成果

## 关键词
- 软件定义网络（SDN）
- 服务质量（QoS）
- FlowManager
- Mininet / Ryu

## 1. 引言
- 传统网络面临的挑战（复杂度、缺乏可编程性、QoS 难保障）
- SDN 的优势与 FlowManager 的定位
- 本文贡献点概述

## 2. 相关工作
- SDN QoS 管理相关研究现状
- FlowManager 或其他控制器图形化管理工具对比
- 本方案的差异化优势

## 3. 系统设计与实现
### 3.1 整体架构
- 描述控制器、拓扑、GUI、QoS 模块的组合
- 引用 `objective1_start_controller.sh`、`objective2_launch_mininet.sh` 的流程图或说明

### 3.2 FlowManager 配置流程
- GUI 各模块（Topology/Flows/Meters）的使用截图
- REST 接口与脚本的配合方式

### 3.3 QoS 策略设计
- 普通 vs 优先策略的配置细节（脚本配置、队列参数、流匹配）
- 若扩展分类转发策略，可补充 DSCP/多队列设计

## 4. 实验设计与结果
### 4.1 测试拓扑与业务流设置
- Mininet 拓扑说明、主机 IP/MAC 分配
- 业务流生成工具与参数（iperf3、D-ITG）

### 4.2 数据采集方法
- 使用 `scripts/tools/export_metrics.py` 或 `scripts/objectives/objective4_collect_stats.py`、FlowManager 日志、Ryu REST 接口的流程
- 数据存储结构（JSON、PNG、CSV）

### 4.3 策略对比分析
- 以图表（`scripts/tools/plot_metrics.py` 或 `scripts/objectives/objective4_plot.py` 输出）展示三种策略的吞吐/延迟差异
- 讨论 QoS 策略对关键业务的保障效果、对其他业务的影响
- 若存在瓶颈或意外现象，分析原因

## 5. 技术优势与待优化方向
- 汇总方案在可视化管理、自动化脚本化、QoS 收敛速度等方面的优势
- 提出待优化方向（如扩展多交换机、多队列动态调度、接入机器学习）

## 6. 结论与展望
- 回顾目标完成情况与项目价值
- 展望未来工作（例如生产环境部署、更多协议支持）

## 参考文献
- 列出引用的论文、工具文档及仓库链接

## 附录
- 关键脚本代码片段
- 实验环境参数表
- 更多对比图或原始数据链接
