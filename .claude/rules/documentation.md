# Documentation

> **正本**: ディレクトリ構成は `CLAUDE.md`「ディレクトリ構成」、モジュール依存関係は `docs/architecture.md`「Module Dependencies」（矛盾する場合は正本を優先）。
ファイルの配置先を決める方針は `CLAUDE.md` の「ドキュメント・ファイル配置の方針」を参照。

## コード内ドキュメント

- docstring は **Google スタイル**を使う（Args / Returns を明記）
- 「なにをするか」ではなく「なぜそうするか」をコメントに書く。コードから読み取れることは書かない
- 特に、複数のXBRLタグを合算する処理では前提条件（二重計上の回避、連結/個別のスコープ整合）をコメントで明示する

## ログファイルの配置

実行ログはリポジトリルートに `<script名>_YYYYMMDD.log` として出力される。生成物であり、コミット対象ではない。

## 変更履歴

`docs/context/changelog.md` に記録する。技術的な学習事項もここに集約し、`CLAUDE.md` の `## Lessons` には再発防止の一般則だけを短く残す。

## 図表

アーキテクチャ図・データフロー図は mermaid で記述し、`docs/architecture.md` に置く。
