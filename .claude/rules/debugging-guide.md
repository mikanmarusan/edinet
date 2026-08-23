# Debugging Guide

XBRL抽出で実際に繰り返し起きた不具合と、その切り分け手順。汎用的なデバッグ作法は省く。

## 1. 連結ではなく個別データが抽出される

**症状**: 従業員数が想定より極端に少ない。財務指標が企業規模と釣り合わない。1社のレコードにスケールの異なる値が混在する。

**切り分け**:

```python
# その企業に連結データが存在するか
print(f"Has consolidated data: {parser._has_consolidated_data(root)}")

# 該当タグのコンテキストを列挙する
for elem in root.iter():
    if elem.text and 'Employee' in elem.tag:
        print(elem.tag, elem.get('contextRef'), elem.text)
```

**よくある原因**: `ReportingCompany` コンテキストのスキップ漏れ、`BusinessResultsOfGroup` を優先していない、指標ごとの `_calculate_*_priority` の間でフィルタ条件が揃っていない。**新しい指標を足したときに既存指標と同じフィルタを適用し忘れる**のが最頻。

## 2. 単体決算企業でデータが空になる

**症状**: 特定企業だけ全フィールドが `null`。抽出自体は成功しているのに結果が空。

**切り分け**: `_has_consolidated_data()` が単体決算のみの企業で `True` を返していないか確認する。`True` になっていると `NonConsolidatedMember` が誤って除外され、候補が1つも残らない。

**原則**: 連結が存在しない場合、`NonConsolidatedMember` は除外してはならない。

## 3. 正しい値があるのに別の候補が選ばれる

**切り分け**: 選択前に全候補を出す。

```python
for value, priority, tag, context in candidates:
    logger.debug(f"Candidate: {tag} = {value} (priority: {priority})")
```

同点だった場合は、決定的なタイブレークが入っているかを確認する。入っていなければ実行ごとに結果が変わりうる。

## 4. 抽出結果が変わったかどうかを確かめたい

ゴールデン回帰ハーネスが唯一の判定基準：

```bash
python -m pytest tests/test_golden_regression.py -v
```

`REGRESSION` が1件でも出たらCIは落ちる。意図した変更なら `EXPECTED_CHANGES` に追記する。手順の詳細は `running-tests` スキルを参照。

## 5. XBRLのパースそのものが失敗する

名前空間の定義漏れを最初に疑う：

```python
for prefix, uri in XBRL_NAMESPACES.items():
    print(prefix, len(root.findall(f'.//{prefix}:*', XBRL_NAMESPACES)))
```

IFRS（`jpigp`）と銀行業スキーマは名前空間が異なる。対応するフィクスチャが `tests/fixtures/xbrl/` にあるので、再現はそこから始める。

## 再現用フィクスチャ

問題が起きた企業のパターンは、実企業の報告値ではなく**架空企業の丸い数値**に置き換えてフィクスチャ化し、回帰テストとして残すこと。
