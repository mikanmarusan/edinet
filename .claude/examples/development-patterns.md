# Development Patterns

## よくある作業パターン

### 新機能追加時のテンプレート
1. 要件を.ai-rules/に文書化
2. lib/に共通機能を実装
3. bin/にエントリーポイント作成
4. CLAUDE.mdとREADME更新

### バグ修正時の確認事項
1. エラーログの確認
2. 影響範囲の特定（単一企業 or 全体）
3. lib/での修正を優先
4. データ再取得の必要性確認

### リファクタリング時の注意点
1. lib/への機能移動を検討
2. 後方互換性の維持（JSON形式）
3. エラーハンドリングの改善
4. ログ出力の整合性確認

## デプロイプロセス
GitHub Actionsによる自動実行：
- 毎日午前3時（JST）に自動実行
- mainブランチへのプッシュで起動

## テストの実行方法
現在、明示的なテストスイートは未実装。
動作確認は以下の手順：
1. `python bin/fetch_edinet_financial_documents.py`の実行
2. 出力JSONの形式確認
3. ログファイルでエラー確認

## 開発時の注意事項

### モジュール設計の原則
- 共通処理はlib/に集約
- bin/は薄いラッパーとして実装
- 単一責任の原則を遵守

### エラー処理のパターン
- 個別エラーで全体を停止しない
- ログに詳細を記録
- 最後にサマリーを出力

### データ品質の確保
- 入力値の検証を徹底
- 不正なデータのスキップ
- 処理結果の統計を記録

## Contributing Guidelines

### Code Style
1. Follow PEP 8 Python style guide
2. Use descriptive variable and function names
3. Add docstrings to all functions
4. Keep functions focused and under 50 lines

### Before Submitting

#### Code Quality Checklist
- [ ] Code follows existing patterns in the codebase
- [ ] All functions have docstrings
- [ ] Error handling is consistent with project standards
- [ ] Logging is appropriate (not too verbose, not too sparse)
- [ ] No hardcoded values or credentials

#### Testing Requirements
- [ ] Manual testing completed successfully
- [ ] Test with real EDINET data
- [ ] Verify error handling works as expected
- [ ] Check memory usage for large datasets
- [ ] Ensure rate limiting is respected

### Adding New Features

1. **Discuss First**: Open an issue to discuss the feature
2. **Design Review**: Share your approach before implementing
3. **Incremental Changes**: Break large features into smaller PRs
4. **Documentation**: Update relevant documentation files
5. **Examples**: Provide usage examples in PR description

### Bug Fix Process

1. **Reproduce**: Ensure you can reproduce the bug
2. **Root Cause**: Identify the root cause, not just symptoms
3. **Test Case**: Add a test case that would catch this bug
4. **Fix**: Implement the minimal fix needed
5. **Verify**: Test with various edge cases

### Documentation Updates

- Keep README.md user-focused
- Add technical details to .ai-rules/ files
- Update CLAUDE.md for AI-specific guidance
- Include examples where helpful

### Commit Best Practices

```bash
# Good commit messages
git commit -m "fix: Handle missing secCode in XBRL parser"
git commit -m "feat: Add dynamic search for cash equivalents"
git commit -m "docs: Update installation instructions"

# Bad commit messages
git commit -m "fix bug"
git commit -m "update code"
git commit -m "misc changes"
```

### Pull Request Guidelines

1. **Title**: Clear, descriptive title with type prefix
2. **Description**: Explain what and why, not just how
3. **Testing**: Describe testing performed
4. **Screenshots**: Include output examples if relevant
5. **Breaking Changes**: Clearly mark any breaking changes

### Code Review Etiquette

- Be constructive and respectful
- Suggest improvements, don't demand
- Explain the reasoning behind suggestions
- Approve PRs promptly when satisfied
- Ask questions if something is unclear