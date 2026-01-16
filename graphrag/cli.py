#!/usr/bin/env python3
"""
IAMI GraphRAG CLI - 命令行工具
"""
import os
import sys
import asyncio
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphrag.indexer import IAMIDataLoader, IAMIGraphIndexer, IndexConfig
from graphrag.visualizer import IAMIGraphVisualizer

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """IAMI GraphRAG - 知识检索系统"""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='强制重建索引')
def build(force):
    """构建知识图谱索引"""
    console.print("[bold blue]Building IAMI Knowledge Graph...[/bold blue]\n")

    # 加载配置
    config = IndexConfig(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        working_dir=os.getenv("GRAPHRAG_INDEX_DIR", "./graphrag/storage/index")
    )

    if not config.api_key:
        console.print("[bold red]Error: DEEPSEEK_API_KEY not set[/bold red]")
        console.print("Please set your DeepSeek API key in .env file")
        sys.exit(1)

    # 初始化
    loader = IAMIDataLoader()
    indexer = IAMIGraphIndexer(config)

    # 加载数据
    with Progress() as progress:
        task = progress.add_task("[cyan]Loading documents...", total=100)

        documents = loader.load_all_data()
        progress.update(task, completed=50)

        console.print(f"Loaded [bold]{len(documents)}[/bold] documents\n")

        # 索引数据
        progress.update(task, description="[cyan]Indexing documents...")

        async def do_index():
            return await indexer.index_documents(documents)

        results = asyncio.run(do_index())
        progress.update(task, completed=100)

    # 显示结果
    table = Table(title="Indexing Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Documents", str(results['total']))
    table.add_row("Success", str(results['success']))
    table.add_row("Failed", str(results['failed']))

    console.print(table)

    if results['errors']:
        console.print("\n[bold yellow]Errors:[/bold yellow]")
        for error in results['errors'][:5]:
            console.print(f"  - {error['doc_id']}: {error['error']}")


@cli.command()
@click.argument('query')
@click.option('--mode', type=click.Choice(['naive', 'local', 'global', 'hybrid']), default='hybrid', help='查询模式')
@click.option('--top-k', type=int, default=5, help='返回结果数量')
def query(query, mode, top_k):
    """查询知识图谱"""
    console.print(f"[bold blue]Query:[/bold blue] {query}\n")

    # 加载配置
    config = IndexConfig(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        working_dir=os.getenv("GRAPHRAG_INDEX_DIR", "./graphrag/storage/index")
    )

    if not config.api_key:
        console.print("[bold red]Error: DEEPSEEK_API_KEY not set[/bold red]")
        sys.exit(1)

    # 查询
    indexer = IAMIGraphIndexer(config)

    async def do_query():
        return await indexer.query(query, mode=mode, top_k=top_k)

    with console.status(f"[bold green]Searching (mode: {mode})..."):
        result = asyncio.run(do_query())

    if result['success']:
        console.print("\n[bold green]Result:[/bold green]\n")
        console.print(result['result'])
    else:
        console.print(f"[bold red]Error:[/bold red] {result.get('error')}")


@cli.command()
def stats():
    """显示索引统计信息"""
    config = IndexConfig(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        working_dir=os.getenv("GRAPHRAG_INDEX_DIR", "./graphrag/storage/index")
    )

    indexer = IAMIGraphIndexer(config)
    stats = indexer.get_stats()

    table = Table(title="Index Statistics")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Working Directory", stats['working_dir'])
    table.add_row("Exists", "Yes" if stats['exists'] else "No")
    table.add_row("Files Count", str(len(stats['files'])))

    console.print(table)

    if stats['files']:
        console.print("\n[bold]Files:[/bold]")
        for f in stats['files']:
            console.print(f"  - {f}")


@cli.command()
@click.option('--relationships/--no-relationships', default=True, help='可视化关系网络')
@click.option('--timeline/--no-timeline', default=True, help='可视化时间轴')
def visualize(relationships, timeline):
    """生成可视化"""
    viz = IAMIGraphVisualizer()

    if relationships:
        try:
            output = viz.visualize_relationships()
            console.print(f"[green]✓[/green] Relationships: {output}")
        except Exception as e:
            console.print(f"[red]✗[/red] Relationships failed: {e}")

    if timeline:
        try:
            output = viz.visualize_timeline()
            console.print(f"[green]✓[/green] Timeline: {output}")
        except Exception as e:
            console.print(f"[red]✗[/red] Timeline failed: {e}")


@cli.command()
def watch():
    """监控文件变化并自动更新索引"""
    console.print("[bold blue]Starting file watcher...[/bold blue]\n")

    from graphrag.watcher import IAMIFileWatcher

    watcher = IAMIFileWatcher()

    # 初始索引
    console.print("Initial indexing...")
    documents = watcher.loader.load_all_data()

    async def do_initial_index():
        return await watcher.indexer.index_documents(documents)

    results = asyncio.run(do_initial_index())
    console.print(f"Indexed {results['success']} documents\n")

    # 启动监控
    try:
        watcher.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/yellow]")


if __name__ == "__main__":
    cli()
