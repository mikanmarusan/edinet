# Git Workflow

## ブランチ戦略
- メインブランチ: main
- 機能開発: feature/機能名
- バグ修正: fix/issue-番号-説明
- Claude生成: claude/issue-番号-タイムスタンプ

## コミットメッセージの規則
- 形式: `<type>: <description>`
- タイプ: feat, fix, docs, refactor, test, chore
- 例: `fix: Set stock price to null when eps is negative`

## PR作成時のチェックリスト
1. テストが通ること（将来実装予定）
2. ログ出力の確認
3. エラーハンドリングの確認
4. コードレビューの観点

## レビュー時の観点
- PEP 8準拠
- エラーハンドリングの適切性
- パフォーマンスへの影響
- セキュリティの考慮

## マージ戦略
- mainブランチへの直接プッシュは避ける
- PRを通じたマージを推奨
- スクワッシュマージで履歴を整理