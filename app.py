from flask import Flask, render_template, request, redirect, url_for
import networkx as nx
import os
from collections import Counter

app = Flask(__name__)

GRAPH_PATH = "C://Users//jett//PycharmProjects//PythonProject//data//football_network.gexf"

# --- 1. 加载图与数据清洗 ---
print("[-] Loading graph into memory...")
if os.path.exists(GRAPH_PATH):
    G = nx.read_gexf(GRAPH_PATH)
    print(f"[+] Graph loaded: {G.number_of_nodes()} nodes.")
else:
    G = nx.Graph()

NAME_TO_ID = {}
# 清洗数据 & 建立索引 (保留你之前的逻辑)
ATTR_MAPPING = {
    '0': 'name',
    '1': 'position',
    '3': 'birth_date',
    '4': 'img_url',
    '5': 'market_value',
    '6': 'team',
    '7': 'league',
}

for node_id, data in G.nodes(data=True):
    # 1. 尝试映射数字键到英文键
    for key_num, key_name in ATTR_MAPPING.items():
        if key_num in data:
            data[key_name] = data[key_num]

    # 2. 强制修复: 如果还是没有 team，但在爬虫原始数据里有，尝试从 label 恢复
    # (这一步是为了保险，如果上面的映射没生效)
    if 'team' not in data:
        data['team'] = 'Unknown'

        # 3. 确保有名字
    if 'name' not in data or not data['name']:
        data['name'] = node_id.split('_')[0]
        data['label'] = data['name']

    NAME_TO_ID[data['name'].lower()] = node_id

# --- 2. 预计算：中心度排名 (Centrality) ---
print("[-] Calculating Centrality Rankings...")

# 1. PageRank (计算字典，并生成核心球员列表)
try:
    if G.number_of_nodes() > 0:
        PAGERANK_DICT = nx.pagerank(G, alpha=0.85)
        CORE_PLAYERS = sorted(PAGERANK_DICT.items(), key=lambda x: x[1], reverse=True)[:50]
    else:
        PAGERANK_DICT = {}
        CORE_PLAYERS = []
except Exception as e:
    print(f"[!] PageRank Error: {e}")
    PAGERANK_DICT = {}
    CORE_PLAYERS = []

# 2. Betweenness (耗时操作，计算字典，并生成桥梁球员列表)
print("[-] Calculating Betweenness (k=500)...")
try:
    if G.number_of_nodes() > 0:
        # 这里只计算一次！
        BETWEENNESS_DICT = nx.betweenness_centrality(G, k=500, normalized=True)
        BRIDGE_PLAYERS = sorted(BETWEENNESS_DICT.items(), key=lambda x: x[1], reverse=True)[:50]
    else:
        BETWEENNESS_DICT = {}
        BRIDGE_PLAYERS = []
except Exception as e:
    print(f"[!] Betweenness Error: {e}")
    BETWEENNESS_DICT = {}
    BRIDGE_PLAYERS = []

print("[-] Metrics loaded.")

# 3. 辅助数据
DEGREE_DICT = dict(G.degree)
def get_percentile(score, all_scores):
    if not all_scores: return 0
    return int((sum(1 for x in all_scores.values() if x < score) / len(all_scores)) * 100)

# 辅助函数：解析身价字符串为数字
def parse_value(v):
    if not v or v == 'N/A': return 0.0
    try:
        clean = str(v).replace('€', '').replace('m', '').replace('k', '')
        val = float(clean)
        if 'k' in str(v): val = val / 1000
        return val
    except:
        return 0.0

@app.route('/')
def home():
    unique_communities = set()
    for _, data in G.nodes(data=True):
        if 'community_id' in data:
            unique_communities.add(data['community_id'])

    # 如果没数据默认显示 0
    comm_count = len(unique_communities) if unique_communities else 0
    stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "communities": comm_count
    }
    return render_template('home.html', stats=stats)


@app.route('/explorer')
def explorer():
    stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges()
    }
    return render_template('index.html', stats=stats)
    # 注意：你需要把 index.html 里的统计数据移除，或者重新传参


@app.route('/search', methods=['GET', 'POST'])
def search():
    # ... (保持你现有的搜索代码不变) ...
    # 这里直接复制你之前已经跑通的 search 函数逻辑
    query_name = request.args.get('name', '').strip().lower()
    target_name = request.args.get('target', '').strip().lower()

    if not query_name: return redirect(url_for('index'))

    found_id = None
    if query_name in NAME_TO_ID:
        found_id = NAME_TO_ID[query_name]
    else:
        matches = [pid for name, pid in NAME_TO_ID.items() if query_name in name]
        if matches: found_id = matches[0]  # 简单取第一个

    if not found_id:
        return render_template('result.html', error=f"Player '{query_name}' not found.")

    player_data = G.nodes[found_id]

    # 路径逻辑
    path_result = None
    if target_name:
        target_id = NAME_TO_ID.get(target_name)  # 简化的查找，建议保留你原来的模糊匹配
        if not target_id:
            # 尝试模糊匹配目标
            t_matches = [pid for name, pid in NAME_TO_ID.items() if target_name in name]
            if t_matches: target_id = t_matches[0]

        if target_id:
            try:
                path = nx.shortest_path(G, source=found_id, target=target_id)
                path_result = []
                for i in range(len(path) - 1):
                    p1, p2 = path[i], path[i + 1]
                    edge_data = G.get_edge_data(p1, p2)
                    history = edge_data.get('history', 'Teammates')
                    path_result.append({"from": G.nodes[p1], "to": G.nodes[p2], "relation": history})
            except nx.NetworkXNoPath:
                path_result = "No connection found."

    teammates = [G.nodes[n] for n in G.neighbors(found_id)]
    teammates.sort(key=lambda x: parse_value(x.get('market_value')), reverse=True)

    return render_template('result.html', player=player_data, teammates=teammates[:12], path=path_result,
                           degree=G.degree(found_id))


@app.route('/rankings')
def rankings():
    """功能 2: 增强版排行榜"""

    # 辅助函数：格式化数据
    def format_list(score_list, score_name):
        res = []
        for pid, score in score_list:
            node = G.nodes[pid]
            res.append({
                "name": node.get('name', 'Unknown'),
                "score": f"{score:.4f}" if isinstance(score, float) else score,  # 保留4位小数
                "score_label": score_name,
                "position": node.get('position', '-'),
                "team": node.get('team', '-'),  # 确保 build_graph 里存了 team
                "img_url": node.get('img_url', '')
            })
        return res

    # 准备三份榜单
    # 1. 最广人脉 (Degree) - 你原本的
    degree_list = sorted(G.degree, key=lambda x: x[1], reverse=True)[:50]

    context = {
        "degree_rank": format_list(degree_list, "Teammates"),
        "core_rank": format_list(CORE_PLAYERS, "PageRank Score"),
        "bridge_rank": format_list(BRIDGE_PLAYERS, "Betweenness")
    }

    return render_template('ranking.html', **context)


# --- 辅助函数：美化球队名 ---
def clean_team_name(slug):
    """把 'us-lecce' 变成 'US Lecce', 'manchester-city' 变成 'Manchester City'"""
    if not slug: return "Unknown Team"
    # 去掉 fc-, us-, -fc 这种常见的前后缀
    slug = slug.replace('fc-', '').replace('us-', '').replace('-fc', '').replace('-cfc', '')
    # 把横杠变空格，并每个单词首字母大写
    clean = slug.replace('-', ' ').title()

    # 特殊处理一些著名缩写
    if "Psg" in clean: clean = "PSG"
    if "Man Utd" in clean: clean = "Manchester United"
    if "Nizza" in clean: clean = "OGC Nice"  # 修正德语拼写
    if "Genua" in clean: clean = "Genoa"

    return clean


@app.route('/communities')
def communities():
    """功能 3: 极速版社区展示 (直接读取 build_graph 算好的结果)"""

    # 1. 从图中提取社区数据
    # 我们创建一个字典: {community_id: [player_id1, player_id2...]}
    comm_groups = {}

    # 遍历所有节点，按 community_id 分组
    for pid, data in G.nodes(data=True):
        # 读取我们在 build_graph.py 里存进去的 ID，如果没有就默认 0
        # 注意：GEXF 读取时属性名可能会变成字符串 'community_id' 或者数字键
        # 先尝试直接读取
        cid = data.get('community_id')

        # 如果读取不到，尝试去属性映射里找 (GEXF有时候会把属性变成 '8', '9' 这种数字)
        if cid is None:
            # 这是一个兜底策略，遍历所有属性找整数型的值
            for k, v in data.items():
                if k.isdigit() and isinstance(v, int):
                    # 假设整数属性就是社区ID (通常是唯一的整数属性)
                    cid = v
                    break

        if cid is None: cid = 0  # 实在找不到归为0

        if cid not in comm_groups:
            comm_groups[cid] = []
        comm_groups[cid].append(pid)

    # 2. 筛选出最大的 8 个社区
    # 按人数排序
    sorted_groups = sorted(comm_groups.items(), key=lambda x: len(x[1]), reverse=True)[:8]

    community_display = []

    for idx, (cid, members) in enumerate(sorted_groups):
        # 找出这个社区里最核心的球员 (Degree最高)
        top_players_ids = sorted(members, key=lambda x: G.degree(x), reverse=True)[:12]
        top_players = [G.nodes[pid] for pid in top_players_ids]

        # 统计球队构成
        all_teams = []
        for pid in members:
            node = G.nodes[pid]
            # 尝试获取 team 属性
            t = node.get('team', 'Unknown')
            # 兼容 GEXF 键名丢失的情况
            if t == 'Unknown':
                for k, v in node.items():
                    # 简单的启发式：如果是字符串且不是 URL 不是日期
                    if isinstance(v, str) and len(v) < 30 and '/' not in v:
                        t = v  # 暂时借用
                        break
            if t != 'Unknown': all_teams.append(t)

        # 命名逻辑
        comm_name = f"Cluster {idx + 1}"
        description = "A grouped player network."

        if all_teams:
            counts = Counter(all_teams).most_common(2)
            primary_team, count1 = counts[0]
            total = len(all_teams)
            percent = int((count1 / total) * 100)

            # 美化名字函数 (如果你之前写了 clean_team_name 就在这里用)
            # primary_team = clean_team_name(primary_team)

            if percent > 50:
                comm_name = f"{primary_team} Core"
                description = f"Dominantly {primary_team} players ({percent}%)."
            elif len(counts) > 1:
                sec_team = counts[1][0]
                comm_name = f"{primary_team} & {sec_team} Link"
                description = f"Connection between {primary_team} and {sec_team}."

        community_display.append({
            "id": idx + 1,
            "name": comm_name,
            "description": description,
            "size": len(members),
            "top_members": top_players
        })

    return render_template('communities.html', communities=community_display)


@app.route('/player/<path:name>')
def player_profile(name):
    """功能 4: 独立的球员卡片展示"""
    # 1. 查找球员 ID
    name_clean = name.strip().lower()
    found_id = None

    # 尝试完全匹配
    if name_clean in NAME_TO_ID:
        found_id = NAME_TO_ID[name_clean]
    else:
        # 尝试从 URL 恢复 (有时候 URL 里的空格被转义了)
        for n, pid in NAME_TO_ID.items():
            if name_clean == n:
                found_id = pid
                break

    if not found_id:
        return render_template('result.html', error=f"Player '{name}' not found.")

    node = G.nodes[found_id]

    # 2. 获取各项指标数据
    degree = G.degree(found_id)
    pr_score = PAGERANK_DICT.get(found_id, 0)
    bt_score = BETWEENNESS_DICT.get(found_id, 0)

    # 3. 计算雷达图所需的“能力值” (0-100)
    # 使用百分位排名，这样所有球员的分数都会分布在 0-100 之间
    stats = {
        "degree_rating": get_percentile(degree, dict(G.degree)),
        "core_rating": get_percentile(pr_score, PAGERANK_DICT),
        "bridge_rating": get_percentile(bt_score, BETWEENNESS_DICT),
        # 原始数据
        "degree_raw": degree,
        "team": node.get('team', 'Unknown'),
        "league": node.get('league', '-')
    }

    return render_template('player_card.html', player=node, stats=stats)


@app.route('/lookup', methods=['POST'])
def lookup():
    """首页查找按钮的中转路由：处理模糊搜索并跳转到球员卡"""
    query_name = request.form.get('name', '').strip().lower()

    if not query_name:
        return redirect(url_for('home'))

    found_id = None

    # 1. 尝试完全匹配
    if query_name in NAME_TO_ID:
        found_id = NAME_TO_ID[query_name]
    else:
        # 2. 尝试模糊匹配 (和 Search 逻辑一样，找最短的匹配项)
        matches = []
        for name_key, pid in NAME_TO_ID.items():
            if query_name in name_key:
                matches.append((name_key, pid))

        if matches:
            # 按名字长度排序，取最像的那个
            matches.sort(key=lambda x: len(x[0]))
            found_id = matches[0][1]

    # 3. 跳转逻辑
    if found_id:
        # 找到 ID 后，获取正确的显示名字 (例如 "Harry Kane")
        # 这样 URL 就会很漂亮：/player/Harry%20Kane
        real_name = G.nodes[found_id].get('name', query_name)
        return redirect(url_for('player_profile', name=real_name))
    else:
        # 没找到，就跳转到原来的搜索结果页显示 "Not Found"
        return redirect(url_for('search', name=query_name))

if __name__ == '__main__':
    app.run(debug=True, port=5000)