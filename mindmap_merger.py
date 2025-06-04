import os
import argparse
import json
import time
import sys
import requests

# タイムアウト設定
REQUEST_TIMEOUT = 180  # 3分
MAX_RETRY_COUNT = 2

def check_ollama_version(host="http://localhost:11434"):
    """Ollamaのバージョンを確認する"""
    try:
        # requestsライブラリを使用してバージョン確認
        response = requests.get(f"{host}/api/version", timeout=10)
        if response.status_code == 200:
            version_info = response.json()
            print(f"Ollamaバージョン: {version_info}")
            return version_info
        else:
            print(f"Ollamaバージョン確認エラー: ステータスコード {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print(f"Ollamaバージョン確認タイムアウト")
        return None
    except Exception as e:
        print(f"Ollamaバージョン確認中にエラーが発生しました: {e}")
        return None

def check_ollama_models(host="http://localhost:11434"):
    """利用可能なOllamaモデルを確認する"""
    try:
        # requestsライブラリを使用してモデル一覧を取得
        response = requests.get(f"{host}/api/tags", timeout=10)
        if response.status_code == 200:
            models_info = response.json()
            if 'models' in models_info:
                model_names = [model.get('name', str(model)) for model in models_info['models']]
                print(f"利用可能なモデル: {model_names}")
                return model_names
            else:
                print("モデル情報の形式が不明です")
                print(f"レスポンス: {models_info}")
                return []
        else:
            print(f"モデル一覧取得エラー: ステータスコード {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        print("モデル一覧取得タイムアウト")
        return []
    except Exception as e:
        print(f"モデル一覧取得中にエラーが発生しました: {e}")
        return []

def check_ollama_server(host="http://localhost:11434"):
    """Ollamaサーバーが起動しているか確認する"""
    try:
        # まずRESTful APIでバージョン確認を試みる
        version_info = check_ollama_version(host)
        if version_info:
            # バージョン確認成功の場合はモデル一覧も取得
            models = check_ollama_models(host)
            print(f"Ollamaサーバー接続確認: 成功")
            if models:
                print(f"利用可能なモデル: {models}")
            return True
        
        # Python Clientを使ったバックアップ方法
        try:
            from ollama import Client
            client = Client(host=host)
            response = client.list()
            
            models = []
            # より堅牢なレスポンス処理
            if isinstance(response, dict) and 'models' in response:
                # 新形式: {'models': [{'name': 'model1'}, {'name': 'model2'}]}
                for model in response['models']:
                    if isinstance(model, dict) and 'name' in model:
                        models.append(model['name'])
            elif isinstance(response, list):
                # 古い形式または他の形式: [{'name': 'model1'}, {'name': 'model2'}] または他の構造
                for model in response:
                    if isinstance(model, dict) and 'name' in model:
                        models.append(model['name'])
                    else:
                        models.append(str(model))
            else:
                # その他の場合は文字列変換を試みる
                models = ["レスポンス形式が不明"]
                
            print(f"Ollamaサーバー接続確認: 成功 (Client API)")
            if models:
                print(f"利用可能なモデル: {models}")
            return True
        except Exception as client_e:
            print(f"Client APIでの接続失敗: {client_e}")
            return False
            
    except Exception as e:
        print(f"Ollamaサーバーに接続できません: {e}")
        print("Ollamaサーバーが起動しているか確認してください。")
        return False

def merge_mindmaps_with_ollama(mindmap_files, model_name="llama3", output_file="merged_mindmap.md", host="http://localhost:11434"):
    """マインドマップのマークダウンファイル同士をOllamaを使って統合する"""
    
    # マインドマップファイルの内容を読み込む
    mindmap_contents = []
    for file_path in mindmap_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                mindmap_contents.append({
                    "file": os.path.basename(file_path),
                    "content": content
                })
            print(f"マインドマップファイル「{file_path}」を読み込みました")
        except Exception as e:
            print(f"ファイル「{file_path}」の読み込み中にエラーが発生しました: {e}")
            return None
    
    if not mindmap_contents:
        print("有効なマインドマップファイルがありません")
        return None
    
    # マインドマップの内容をプロンプトに結合
    combined_content = ""
    for i, mindmap in enumerate(mindmap_contents):
        combined_content += f"\n\n--- マインドマップ {i+1}: {mindmap['file']} ---\n{mindmap['content']}"
    
    # 単一ファイルか複数ファイルかによってプロンプトを調整
    is_single_file = len(mindmap_contents) == 1
    task_description = "最適化" if is_single_file else "統合・最適化"
    
    # 強化されたシステムプロンプト (ハルシネーション防止の指示を追加)
    system_prompt = f"""
あなたは{'マインドマップを最適化し' if is_single_file else '複数のマインドマップを統合し'}、概念間の意味的な関連性を考慮して最適化された階層構造を持つ単一の整合的なマインドマップを作成する専門家アシスタントです。

【重要：ハルシネーション防止の指示】
- 元の入力ファイルに明示的に含まれていない情報は決して追加しないでください
- もし不確かな情報や推測に基づく内容を含める必要がある場合は、その部分を "(Hallucination?)" と明示的にマークしてください
- 曖昧な概念や解釈が複数可能な場合も "(Hallucination?)" と付記してください
- 入力データに存在しない概念やカテゴリを作成しないでください
- 情報の統合・最適化は行いますが、新たな創作や拡張は行わないでください

【出力フォーマット】
- トップノード：章タイトルや節タイトルなど、最上位の見出し（Markdown見出し記号「#」を使用）
- サブノード：小見出しや段落ごとの重要キーワード・要点（インデント2スペース＋「-」）
- 枝ノード：関連キーワードや具体例（インデント4スペース＋「+」や「*」）
- 補足説明が必要な場合は「（例：～）」「補足：～」を追加
- 表形式で示すことが適切な情報（比較表など）がある場合は、Markdownのテーブル記法を使用してください
- 不確かな情報には必ず "(Hallucination?)" というマーカーを付けてください

【統合と最適化の詳細プロセス】
1. 意味的分析：各マインドマップのノードが表す概念とその関係性を意味的に分析
   - 概念間の類似性、包含関係、因果関係などを特定
   - 同じ概念に対する異なる表現や異なる粒度の記述を識別
   - 概念のドメイン分析と主題分類を実施
   - 暗黙の関係性や概念間のパターンを発見

2. 意味ネットワークの構築：
   - 概念をノードとし、関係性をエッジとする意味ネットワークを仮想的に構築
   - 中心的概念（高い接続性を持つノード）と周辺概念を識別
   - 概念クラスターを特定し、概念的まとまりを形成

3. 階層構造の再設計：
   - 最適なトップレベルカテゴリを特定（カテゴリ間の概念的独立性を最大化）
   - 概念の抽象度に基づいて階層の深さを調整（抽象→具体の流れを明確に）
   - 関連性の強い概念をグループ化して近接配置
   - 概念の重要度に基づく階層レベルの最適化

4. 知識の統合：
   - 重複する情報を意味的に統合し、最も包括的な表現を選択
   - 異なるマインドマップからの補完的情報を融合
   - 対立する情報がある場合は、より詳細または信頼性の高い情報を優先
   - 意味的連続性を保ちながら相互補完的な情報を結合

5. 論理的構造の最適化：
   - 概念間の論理的つながりを強化し、思考の流れを最適化
   - 関連概念間のクロスリンクを暗示するような配置
   - 適切な抽象レベルでの情報の集約と詳細化
   - 概念の発展過程や因果関係を反映した構造設計

6. コンテキスト関係の明確化：
   - 概念間の文脈依存性を考慮した配置
   - 隣接する概念間の意味的一貫性の確保
   - 複数の視点から概念を分析し最適な配置を決定

7. 表現の洗練：
   - 各ノードの記述を簡潔かつ明確に統一
   - 同様の概念に対する表現方法を一貫させる
   - 情報の重要度に応じた階層レベルを調整
   - 用語の統一と概念表現の最適化
   - 比較情報や構造化データには表形式を活用して視覚的理解を促進

【補足】
- マークダウン形式のマインドマップのみを出力してください。余計な説明や前置き、コメントは不要です。
- すべての見出し番号、章番号、節番号などのナンバリングは省略し、意味的な見出しのみを使用してください。
- 元のマインドマップの情報をすべて保持しつつ、最適な意味的構造に再編成してください。
- ノード間の関係性が明確になるように、階層の深さや配置を工夫してください。
- 比較データや特性一覧などは、必要に応じてMarkdownのテーブル形式を使用して表現してください。
- 入力データにない情報は絶対に追加せず、不確かな内容には必ず "(Hallucination?)" と明記してください。
"""

    # 強化されたユーザープロンプト (ハルシネーション防止の指示を追加)
    user_prompt = f"""以下の{'マインドマップを分析し、最適化' if is_single_file else '複数のマインドマップを分析し、それらを統合'}した単一の包括的なマインドマップを作成してください。

【ハルシネーション防止の厳格なルール】
- あなたは絶対にハルシネーション（入力データにない情報の創作）を起こしてはいけません
- 元のマインドマップに明示的に含まれていない情報や概念は追加しないでください
- もし不確かな情報や推測に基づく内容を含める必要がある場合は、その部分を "(Hallucination?)" と明示的にマークしてください
- 曖昧な概念や解釈が複数可能な場合も "(Hallucination?)" と付記してください
- 入力データを超えた創作や拡張は行わないでください
- 確信が持てない関係性や概念の統合を行う場合も "(Hallucination?)" とマークしてください

【分析と{task_description}の重要ポイント】
1. コンセプトマッピング：{'マインドマップ内の' if is_single_file else '各マインドマップの'}ノードが表す概念を抽出し、概念同士の関係性（上位-下位、原因-結果、部分-全体など）を詳細に分析してください
2. 意味的ネットワーク構築：概念間の意味的なつながりを特定し、概念のクラスター（意味的にまとまりのあるグループ）を形成してください
3. 知識{'の整理' if is_single_file else '融合'}：{'概念の' if is_single_file else ''}冗長性を排除しながら、すべての重要な情報と関係性を保持してください
4. 階層的最適化：
   - 最も重要で包括的な概念をトップレベルに配置
   - 関連概念を意味的なまとまりでグループ化
   - 抽象的概念から具体的な詳細へと階層を形成
   - 同じ抽象レベルの概念は同じ階層に配置
5. 流れの最適化：概念間の論理的つながりや思考の流れが自然になるよう配置を工夫してください
6. {'構造分析：より効果的な知識表現のために、最適な表示形式（階層構造、表形式など）を選択してください' if is_single_file else '新たな洞察の創出：複数のマインドマップからのインプットを統合することで生まれる新たな概念関係や洞察を取り入れてください'}

【表形式の活用】
- 複数の項目を比較する情報（例：特性比較、長所短所、分類表など）は表形式で表現してください
- リスト形式では伝わりにくい構造化情報は、適宜表形式を用いて視覚的に整理してください
- 表形式が適切な場合のフォーマット例：

```
| カテゴリ | 特性1 | 特性2 | 特性3 |
|---------|------|------|------|
| 項目1   | 内容  | 内容  | 内容  |
| 項目2   | 内容  | 内容  | 内容  |
```

【期待される{task_description}結果】
- 単なる情報の寄せ集めではなく、意味的に一貫した{'知識構造' if is_single_file else '新たな知識構造'}
- 概念間の関係性が明確で、論理的な流れを持つ構造
- {'元の情報を保持しながらも、より最適化された形での概念整理' if is_single_file else '複数の情報源からの知識が有機的に結合された統合的な視点'}
- 知識の階層性と関連性が視覚的に理解しやすい配置
- 情報の種類に応じて適切な表現形式（階層構造・表形式）を使い分けた構造
- 不確かな情報には必ず "(Hallucination?)" と明記すること

{combined_content}

{task_description}されたマークダウン形式のマインドマップのみを出力してください。余計な説明は不要です。必ず入力データに忠実に、ハルシネーションを避けてください。不確かな情報や解釈には "(Hallucination?)" というマーカーを付けてください。"""
    
    print(f"\n{len(mindmap_files)}個のマインドマップファイルを統合します...")
    
    # タイムアウト処理を含むリクエスト関数
    def make_api_request(retry_count=0):
        try:
            start_time = time.time()
            
            # REST APIリクエスト
            api_url = f"{host}/api/chat"
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "options": {"num_ctx": 32768},
                "stream": False  # ストリーミングを無効化
            }
            
            # タイムアウトを設定してリクエスト
            print(f"APIリクエスト送信（タイムアウト: {REQUEST_TIMEOUT}秒）...")
            response = requests.post(api_url, json=payload, timeout=REQUEST_TIMEOUT)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                print(f"APIレスポンス取得完了（処理時間: {end_time - start_time:.2f}秒）")
                
                if "message" in result and "content" in result["message"]:
                    return result["message"]["content"]
                else:
                    print("APIからの応答が想定と異なります")
                    print(f"応答内容: {result}")
                    return None
            else:
                print(f"APIエラー: ステータスコード {response.status_code}")
                print(f"エラー内容: {response.text}")
                
                # 再試行可能なエラーの場合
                if retry_count < MAX_RETRY_COUNT and response.status_code in [408, 429, 500, 502, 503, 504]:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # 指数バックオフ
                    print(f"リトライ ({retry_count}/{MAX_RETRY_COUNT})... {wait_time}秒後に再試行します")
                    time.sleep(wait_time)
                    return make_api_request(retry_count)
                
                return None
                
        except requests.exceptions.Timeout:
            print(f"\nAPIリクエストがタイムアウトしました（{REQUEST_TIMEOUT}秒）")
            
            # 再試行処理
            if retry_count < MAX_RETRY_COUNT:
                retry_count += 1
                wait_time = 2 ** retry_count  # 指数バックオフ
                print(f"リトライ ({retry_count}/{MAX_RETRY_COUNT})... {wait_time}秒後に再試行します")
                time.sleep(wait_time)
                return make_api_request(retry_count)
            else:
                print("最大再試行回数に達しました。処理を中止します。")
                return None
                
        except Exception as e:
            print(f"\nAPIリクエスト中にエラーが発生しました: {e}")
            
            # 再試行処理
            if retry_count < MAX_RETRY_COUNT:
                retry_count += 1
                wait_time = 2 ** retry_count
                print(f"リトライ ({retry_count}/{MAX_RETRY_COUNT})... {wait_time}秒後に再試行します")
                time.sleep(wait_time)
                return make_api_request(retry_count)
            else:
                print("最大再試行回数に達しました。処理を中止します。")
                return None
    
    # リクエスト実行
    result = make_api_request()
    
    if result:
        # 出力ディレクトリの確認
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 結果を保存
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"\n統合されたマインドマップを {output_file} に保存しました")
            return True
        except Exception as e:
            print(f"ファイル保存中にエラーが発生しました: {e}")
            return False
    else:
        print("マインドマップの統合に失敗しました")
        return False

def main():
    parser = argparse.ArgumentParser(description='マインドマップのマークダウンファイルを統合するツール')
    parser.add_argument('--mindmaps', nargs='+', required=True, help='統合するマインドマップファイルのパス')
    parser.add_argument('--output', default='merged_mindmap.md', help='統合結果の出力ファイルパス')
    parser.add_argument('--model', default='llama3', help='使用するOllamaモデル名')
    parser.add_argument('--host', default='http://localhost:11434', help='Ollamaのホストアドレス（デフォルト: http://localhost:11434）')
    parser.add_argument('--timeout', type=int, default=180, help='APIリクエストのタイムアウト秒数')
    parser.add_argument('--debug', action='store_true', help='デバッグモードで実行')
    
    args = parser.parse_args()
    
    # タイムアウト設定を更新
    global REQUEST_TIMEOUT
    REQUEST_TIMEOUT = args.timeout
    
    # デバッグモード
    if args.debug:
        print(f"デバッグモード: 有効")
        print(f"Python バージョン: {sys.version}")
        print(f"指定されたモデル: {args.model}")
        print(f"Ollamaホスト: {args.host}")
        print(f"APIタイムアウト: {REQUEST_TIMEOUT}秒")
        print(f"入力ファイル: {args.mindmaps}")
        print(f"出力ファイル: {args.output}")
    
    # Ollamaサーバーの接続確認
    if not check_ollama_server(args.host):
        return
    
    # マインドマップの統合
    print(f"\nOllamaを使用してマインドマップを統合します...")
    success = merge_mindmaps_with_ollama(
        args.mindmaps,
        args.model,
        args.output,
        args.host
    )
    
    if success:
        print(f"マインドマップの統合が完了しました")
    else:
        print("マインドマップの統合に失敗しました")

if __name__ == "__main__":
    main()
