# Performance Guidelines

## 実装済みの制約（変更しないこと）

- **EDINET API: 1リクエスト/秒。** `lib/edinet_common.py` の各APIコール後に `time.sleep(1)` で担保している。**並列化・非同期化してはならない。** レート制限違反はAPIキーの停止につながる。
- **リトライ**: 指数バックオフ付きで既定3回（1s → 2s → 4s）。`--max-retries` で変更可能。

## 現在のボトルネック

1. API待ち時間が処理時間の大半を占める（レート制限由来のため、改善の余地は事実上ない）
2. XBRL解析: `lib/xbrl_parser.py` は現在DOM全体をメモリに載せる。大規模ファイルで問題が出た場合は `etree.iterparse` によるストリーミングへの切替を検討する（**未実装**）
3. 複数企業の同時処理時のメモリ使用量

## 目安となる処理時間

- 単一文書: 5秒未満
- 日次バッチ（100文書）: 15分未満
- 統合処理（30日分）: 1分未満

これを大きく超える場合は、XPathの評価回数か、レート制限以外の待ちを疑うこと。

## 最適化を検討する際の注意

このファイルには過去、未実装の `RateLimiter` クラス・`asyncio` 版取得・`lru_cache` によるキャッシュ・`memory_profiler` の使用例が「将来的な実装案」として記載されていたが、実装済み機能と誤読されうるため削除した。**未実装の構想はここではなくIssueに書くこと。**

最適化を入れる場合は、まず実測してから着手する：

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name):
    start = time.time()
    yield
    logger.info(f"{name}: {time.time() - start:.2f}秒")
```
