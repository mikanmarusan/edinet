# Git Workflow

コミットメッセージ・ブランチ名・PRタイトル・Issueタイトルは **Conventional Commits** に従う。
共通仕様はユーザーグローバルの `08-conventional-commits.md` にあり、本ファイルはこのリポジトリ固有の運用のみを記す。

## ブランチ

- メインブランチ: `main`。**mainブランチでの直接作業は厳禁。**
- 形式: `<type>/<kebab-case-description>`（例: `feat/add-user-auth`）
- Issue対応時: `<type>/<issue番号>-<kebab-case-description>`（例: `fix/123-null-pointer`）
- Claude Code生成: `claude/issue-<番号>-<タイムスタンプ>`

## コミット

- 1行目: `<type>(<scope>): <short summary>`（72文字以内、命令形、末尾ピリオドなし）
- 空行を挟み、変更内容と理由を1〜3個の箇条書きで記す
- 例: `fix(xbrl): set stock price to null when eps is negative`

## PR

マージ前に確認すること：

1. `python -m pytest tests/ -v` が通ること（CIでも Python 3.11/3.12/3.13 で実行される）
2. `web/` を変更した場合は `node --test web/tests/` を手動実行すること（CI未接続）
3. ログ出力とエラーハンドリングが設計原則（フェイルセーフ）に沿っていること

## マージ戦略

- mainへの直接プッシュは避け、PR経由でマージする
- スカッシュマージで履歴を整理する
