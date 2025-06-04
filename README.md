# mindmap-merger

マインドマップファイルを統合・最適化するツールです。複数のマインドマップを統合し、意味的な関連性を考慮した階層構造に再構成します。

## 機能

- Ollama の ローカルLLM を使って複数のマインドマップを意味的に最適化して統合
- 意味的な関連性を考慮した階層構造に再構成したマインドマップデータを作成

## ファイル構成

```
mindmap-merger/
├── README.md           # このファイル
├── LICENSE             # MITライセンス
├── .gitignore          # Gitで無視するファイル
└── mindmap_merger.py   # メインスクリプト
```

## セットアップ方法

```bash
git clone https://github.com/z39084yu9023jr/mindmap-merger.git
cd mindmap-merger
python3 -m venv venv
source venv/bin/activate
```

## 使用方法

```bash
python mindmap_merger.py --mindmaps path/to/mindmap1.md path/to/mindmap2.md path/to/mindmap3.md --output optimized_mindmap.md --model llama3
```

## ライセンス

MIT License
