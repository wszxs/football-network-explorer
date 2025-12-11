# Football Network Explorer

**Football Network Explorer** is a Flask-based web application that visualizes and analyzes connections between football players based on their teammate history. 

Using graph theory algorithms, this tool reveals hidden relationships, identifies key players, detects communities, and calculates the shortest paths between any two players in the dataset.

## Features

* **Player Search:** Instantly find players and view their network statistics.
* **Path Finder:** Discover the "Six Degrees of Separation" between two players.
* **Centrality Rankings:**
    * **Degree Centrality:** Players with the most teammates.
    * **PageRank:** The most influential players in the network.
    * **Betweenness:** Players who connect different leagues or generations.
* **Player Cards:** Detailed profiles with radar charts comparing a player's network influence against the global average.

## Tech Stack

* **Python 3.8+**
* **Flask** Web Framework
* **NetworkX** Graph Algorithms & Analysis
* **GEXF** Graph Data Format

## Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/wszxs/football-network-explorer.git
    cd football-network-explorer
    ```

2.  **Install dependencies**
    ```bash
    pip install flask networkx
    ```

3.  **Data Setup**
    Ensure your graph data file (`football_network.gexf`) is placed correctly.
    * Create a folder named `data` in the root directory.
    * Place `football_network.gexf` inside it.

4.  **Configuration**
    Open `app.py` and update the `GRAPH_PATH` to point to your data file.
    
    *Recommended (Relative Path):*
    ```python
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    GRAPH_PATH = os.path.join(BASE_DIR, "data", "football_network.gexf")
    ```

## Usage

1.  **Run the application**
    ```bash
    python app.py
    ```

2.  **Access the Dashboard**
    Open your browser and navigate to:
    `http://127.0.0.1:5000`

    * *Note: The first launch might take a few seconds as the application pre-calculates PageRank and Betweenness metrics.*

## Project Structure

```text
football-network-explorer/
├── data/
│   └── football_network.gexf   # Raw graph data
├── static/                     # CSS, Images, JS
├── templates/                  # HTML Templates
│   ├── base.html
│   ├── home.html
│   ├── index.html              # Explorer page
│   ├── ranking.html
│   ├── communities.html
│   ├── result.html
│   └── player_card.html
├── app.py                      # Main Flask application
└── README.md
```
## Algorithmic Details
1. PageRank algorithm is used to determine the rating. A high PageRank means a player has played with other highly connected players.

2. High betweenness centrality indicates a player acts as a connector between otherwise disparate groups (e.g., a player who moved between EPL and La Liga).

3. Uses BFS to find the minimum number of teammate hops between two entities.