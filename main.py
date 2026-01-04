import argparse
import os

from src.document_manager import DocumentManager
from src.image_manager import ImageManager

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="本地多模态AI智能文献与图像管理助手")
    subparsers = parser.add_subparsers(dest="command", help="可用命令：add_paper, search_paper, add_image, search_image")

    # 1. 添加/分类论文命令
    add_paper_parser = subparsers.add_parser("add_paper", help="添加并分类论文（单文件/批量）")
    add_paper_parser.add_argument("path", help="PDF文件路径或文件夹路径")
    add_paper_parser.add_argument("--topics", required=True, help="分类主题，用逗号分隔（如：CV,NLP,RL）")

    # 2. 搜索论文命令
    search_paper_parser = subparsers.add_parser("search_paper", help="语义搜索论文")
    search_paper_parser.add_argument("query", help="搜索查询语句（自然语言）")
    search_paper_parser.add_argument("--n_results", type=int, default=5, help="返回结果数量（默认5）")

    # 3. 添加/索引图片命令（新增：完善参数定义）
    add_image_parser = subparsers.add_parser("add_image", help="添加并索引图片（单文件/批量）")
    add_image_parser.add_argument("path", help="图片文件路径或文件夹路径")

    # 4. 以文搜图命令
    search_image_parser = subparsers.add_parser("search_image", help="以文搜图")
    search_image_parser.add_argument("query", help="图像描述语句（自然语言）")
    search_image_parser.add_argument("--n_results", type=int, default=5, help="返回结果数量（默认5）")

    # 解析参数
    args = parser.parse_args()

    # 执行对应命令
    if args.command == "add_paper":
        # 处理论文添加/分类
        doc_manager = DocumentManager()
        topics = [t.strip() for t in args.topics.split(",")]
        if os.path.isfile(args.path):
            # 单文件处理
            result = doc_manager.add_paper(args.path, topics)
            print(result)
        elif os.path.isdir(args.path):
            # 批量处理文件夹
            result = doc_manager.batch_organize(args.path, topics)
            print(result)
        else:
            print(f"错误：{args.path} 不是有效的文件或文件夹")

    elif args.command == "search_paper":
        # 语义搜索论文
        doc_manager = DocumentManager()
        results = doc_manager.search_paper(args.query, args.n_results)
        if results:
            print(f"\n=== 论文搜索结果（共{len(results)}条）===")
            for i, res in enumerate(results, 1):
                print(f"\n{i}. 文件名：{res['file_name']}")
                print(f"   路径：{res['path']}")
                print(f"   分类：{res['topic']}")
                print(f"   相似度：{res['similarity']}")
        else:
            print("\n未找到相关论文")

    elif args.command == "add_image":
        # 处理图片添加/索引
        img_manager = ImageManager()
        if os.path.isfile(args.path):
            # 单张图片处理
            result = img_manager.add_image(args.path)
            print(result)
        elif os.path.isdir(args.path):
            # 批量处理图片文件夹
            result = img_manager.batch_index_images(args.path)
            print(result)
        else:
            print(f"错误：{args.path} 不是有效的文件或文件夹")

    elif args.command == "search_image":
        # 以文搜图
        img_manager = ImageManager()
        results = img_manager.search_image(args.query, args.n_results)
        if results:
            print(f"\n=== 图像搜索结果（共{len(results)}条）===")
            for i, res in enumerate(results, 1):
                print(f"\n{i}. 文件名：{res['file_name']}")
                print(f"   路径：{res['path']}")
                print(f"   相似度：{res['similarity']}")
        else:
            print("\n未找到相关图像")

    else:
        # 显示帮助信息
        parser.print_help()

if __name__ == "__main__":
    main()