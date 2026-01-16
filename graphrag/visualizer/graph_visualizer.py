"""
IAMI Graph Visualizer - 关系图谱可视化
"""
import json
import networkx as nx
from pathlib import Path
from typing import Dict, Any, Optional
from pyvis.network import Network


class IAMIGraphVisualizer:
    """IAMI 关系图谱可视化器"""

    def __init__(self, output_dir: str = "./graphrag/storage/visualizations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def visualize_relationships(
        self,
        network_file: str = "./memory/relationships/network.json",
        output_file: Optional[str] = None
    ) -> str:
        """可视化人际关系网络"""

        if output_file is None:
            output_file = str(self.output_dir / "relationships.html")

        # 读取网络数据
        with open(network_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 创建网络图
        G = nx.Graph()

        # 添加节点和边
        if isinstance(data, dict):
            # 假设数据格式为 {nodes: [...], edges: [...]}
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])

            for node in nodes:
                node_id = node.get("id") or node.get("name")
                G.add_node(
                    node_id,
                    label=node.get("name", node_id),
                    title=node.get("description", ""),
                    group=node.get("type", "person")
                )

            for edge in edges:
                source = edge.get("source") or edge.get("from")
                target = edge.get("target") or edge.get("to")
                relationship = edge.get("relationship", "")

                G.add_edge(
                    source,
                    target,
                    title=relationship,
                    label=relationship
                )

        # 使用 pyvis 创建交互式可视化
        net = Network(
            height="750px",
            width="100%",
            bgcolor="#ffffff",
            font_color="#000000",
            heading="IAMI 人际关系网络"
        )

        net.from_nx(G)

        # 设置物理引擎
        net.set_options("""
        {
          "nodes": {
            "borderWidth": 2,
            "size": 30,
            "font": {
              "size": 14,
              "face": "Arial"
            }
          },
          "edges": {
            "color": {
              "inherit": true
            },
            "smooth": {
              "type": "continuous"
            },
            "arrows": {
              "to": {
                "enabled": true,
                "scaleFactor": 0.5
              }
            }
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -30000,
              "springConstant": 0.001,
              "springLength": 200
            },
            "stabilization": {
              "iterations": 2500
            }
          }
        }
        """)

        # 保存
        net.save_graph(output_file)

        return output_file

    def visualize_timeline(
        self,
        snapshots_file: str = "./memory/timeline/snapshots.json",
        output_file: Optional[str] = None
    ) -> str:
        """可视化时间轴"""

        if output_file is None:
            output_file = str(self.output_dir / "timeline.html")

        # 读取时间轴数据
        with open(snapshots_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 使用 plotly 创建时间轴
        try:
            import plotly.graph_objects as go
            from datetime import datetime

            snapshots = data.get("snapshots", []) if isinstance(data, dict) else data

            # 解析时间戳和标题
            dates = []
            titles = []
            descriptions = []

            for snapshot in snapshots:
                timestamp = snapshot.get("timestamp", "")
                if timestamp:
                    try:
                        date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        dates.append(date)
                        titles.append(snapshot.get("title", "快照"))
                        descriptions.append(snapshot.get("summary", ""))
                    except:
                        pass

            # 创建时间轴图
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=dates,
                y=[1] * len(dates),
                mode='markers+text',
                marker=dict(size=15, color='blue'),
                text=titles,
                textposition="top center",
                hovertext=descriptions,
                hoverinfo="text+x"
            ))

            fig.update_layout(
                title="IAMI 思想演变时间轴",
                xaxis_title="时间",
                yaxis_visible=False,
                height=400,
                hovermode='closest'
            )

            fig.write_html(output_file)

            return output_file

        except ImportError:
            # 如果 plotly 不可用，生成简单的 HTML
            html = self._generate_simple_timeline_html(snapshots)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            return output_file

    def _generate_simple_timeline_html(self, snapshots: list) -> str:
        """生成简单的 HTML 时间轴"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>IAMI 思想演变时间轴</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        .timeline {
            max-width: 800px;
            margin: 0 auto;
        }
        .snapshot {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #4285f4;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .summary {
            color: #333;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="timeline">
        <h1>IAMI 思想演变时间轴</h1>
"""

        for snapshot in snapshots:
            html += f"""
        <div class="snapshot">
            <div class="timestamp">{snapshot.get('timestamp', '')}</div>
            <div class="title">{snapshot.get('title', '快照')}</div>
            <div class="summary">{snapshot.get('summary', '')}</div>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""
        return html

    def create_knowledge_map(
        self,
        query_result: Dict[str, Any],
        output_file: Optional[str] = None
    ) -> str:
        """根据查询结果创建知识地图"""

        if output_file is None:
            output_file = str(self.output_dir / "knowledge_map.html")

        # 这里可以根据 GraphRAG 的查询结果生成知识地图
        # 暂时生成一个简单的可视化

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>知识地图</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .result {{
            background: white;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        pre {{
            background: #f8f8f8;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="result">
        <h1>查询结果</h1>
        <pre>{json.dumps(query_result, ensure_ascii=False, indent=2)}</pre>
    </div>
</body>
</html>
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_file


if __name__ == "__main__":
    # 测试
    viz = IAMIGraphVisualizer()

    # 可视化关系网络
    try:
        output = viz.visualize_relationships()
        print(f"Relationships visualization saved to: {output}")
    except Exception as e:
        print(f"Error visualizing relationships: {e}")

    # 可视化时间轴
    try:
        output = viz.visualize_timeline()
        print(f"Timeline visualization saved to: {output}")
    except Exception as e:
        print(f"Error visualizing timeline: {e}")
