"""
IAMI File Watcher - 监控记忆文件变化并实时更新索引
"""
import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from indexer.data_loader import IAMIDataLoader
from indexer.graph_indexer import IAMIGraphIndexer, IndexConfig


class MemoryFileHandler(FileSystemEventHandler):
    """记忆文件变化处理器"""

    def __init__(self, indexer: IAMIGraphIndexer, loader: IAMIDataLoader):
        self.indexer = indexer
        self.loader = loader
        self.pending_updates: Set[str] = set()
        self.update_task = None

    def on_modified(self, event: FileSystemEvent):
        """文件修改时触发"""
        if event.is_directory:
            return

        file_path = event.src_path
        if self._should_process_file(file_path):
            print(f"Detected change: {file_path}")
            self.pending_updates.add(file_path)
            self._schedule_update()

    def on_created(self, event: FileSystemEvent):
        """文件创建时触发"""
        if event.is_directory:
            return

        file_path = event.src_path
        if self._should_process_file(file_path):
            print(f"Detected new file: {file_path}")
            self.pending_updates.add(file_path)
            self._schedule_update()

    def _should_process_file(self, file_path: str) -> bool:
        """判断是否应该处理该文件"""
        path = Path(file_path)

        # 只处理 memory 目录下的 JSON 和 MD 文件
        if "memory" not in path.parts:
            return False

        if path.suffix not in ['.json', '.md']:
            return False

        # 排除模板文件
        if path.name == '_template.md':
            return False

        return True

    def _schedule_update(self):
        """调度更新任务（防抖）"""
        if self.update_task:
            self.update_task.cancel()

        # 延迟2秒执行更新，避免频繁更新
        self.update_task = asyncio.create_task(self._delayed_update())

    async def _delayed_update(self):
        """延迟更新索引"""
        await asyncio.sleep(2)

        if not self.pending_updates:
            return

        print(f"\nUpdating index for {len(self.pending_updates)} file(s)...")

        try:
            # 重新加载所有数据（简单方式，实际可以优化为只加载变化的文件）
            documents = self.loader.load_all_data()

            # 重新索引
            results = await self.indexer.index_documents(documents)

            print(f"Update complete: {results['success']} documents indexed")

            if results['failed'] > 0:
                print(f"Warning: {results['failed']} documents failed to index")

        except Exception as e:
            print(f"Error updating index: {e}")

        finally:
            self.pending_updates.clear()


class IAMIFileWatcher:
    """IAMI 文件监控器"""

    def __init__(self, memory_path: str = "./memory"):
        self.memory_path = Path(memory_path)
        self.observer = None

        # 初始化索引器
        config = IndexConfig(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            working_dir=os.getenv("GRAPHRAG_INDEX_DIR", "./graphrag/storage/index")
        )
        self.indexer = IAMIGraphIndexer(config)
        self.loader = IAMIDataLoader(str(self.memory_path))

        # 创建事件处理器
        self.event_handler = MemoryFileHandler(self.indexer, self.loader)

    def start(self):
        """启动文件监控"""
        print(f"Starting file watcher for: {self.memory_path}")

        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.memory_path),
            recursive=True
        )
        self.observer.start()

        print("File watcher started. Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止文件监控"""
        if self.observer:
            print("\nStopping file watcher...")
            self.observer.stop()
            self.observer.join()
            print("File watcher stopped.")


async def main():
    """主函数"""
    watcher = IAMIFileWatcher()

    # 首次启动时重建索引
    print("Initial indexing...")
    documents = watcher.loader.load_all_data()
    results = await watcher.indexer.index_documents(documents)
    print(f"Initial indexing complete: {results['success']} documents indexed\n")

    # 启动监控
    watcher.start()


if __name__ == "__main__":
    # 运行异步主函数
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
