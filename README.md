# 本地 AI 智能文献与图像管理助手
https://github.com/hetuntunNi/Multi-Modal-Agent-literature-and-image-management

## 项目简介
本项目是基于Python 3.10开发的本地多模态AI智能助手，解决本地文献（PDF）和图像的管理难题。通过语义搜索和自动分类技术，替代传统的文件名搜索，支持：
- 论文的语义搜索、单文件/批量自动分类
- 本地图像的以文搜图功能
- 完全本地化部署（无数据上传），保护隐私

### 核心功能
| 模块         | 功能列表                                                                 |
|--------------|--------------------------------------------------------------------------|
| 智能文献管理 | 1. 自然语言语义搜索论文<br>2. 单文件自动分类到指定主题<br>3. 批量整理混乱的论文文件夹 |
| 智能图像管理 | 1. 自然语言描述搜索本地图像<br>2. 自动建立图像嵌入索引                     |

## 环境配置
### 系统要求
- 操作系统：Windows/macOS/Linux
- Python版本：3.10
- 内存：8GB+（推荐16GB+，用于加载模型）
- 可选：NVIDIA GPU（CUDA 11.8+，加速模型推理）

### 依赖安装
```bash
# 1. 克隆仓库
git clone https://github.com/hetuntunNi/Multi-Modal-Agent-literature-and-image-management.git
cd Multi-Modal-Agent-literature-and-image-management

# 2. 安装依赖
pip install -r requirements.txt
```

## 运行示例
```bash
# 示例：将论文分类到CV、NLP、RL主题
python main.py add_paper "docs/GeoRAG A Question-Answering Approach from a Geographical Perspective.pdf" --topics "CV,NLP,RL"
```
![](src\web\static\1.png)
```bash
# 示例：整理papers文件夹下的所有PDF
python main.py add_paper "docs" --topics "CV,NLP,RL"
```
![](src\web\static\2.png)
```bash
# 示例：搜索相关论文（返回5条结果）
python main.py search_paper "GeoAI的发展" --n_results 3
```
![](src\web\static\6.png)
```bash
# 示例：搜索“海边的日落”相关图像
python main.py search_image "海边的日落" --n_results 3
```
![](src\web\static\7.png)

## 系统运行
```bash
python app.py
```
### 分类论文
![](src\web\static\4.png)
![](src\web\static\5.png)
### 搜索论文
![](src\web\static\8.png)
### 搜索图片
![](src\web\static\9.png)

