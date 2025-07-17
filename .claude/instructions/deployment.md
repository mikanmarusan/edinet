# Deployment

## 環境別の設定管理
- 現在は本番環境のみ
- GitHub Actionsで自動実行

## デプロイ前のチェックリスト
1. requirements.txtの更新確認
2. APIキーの設定確認
3. 出力ディレクトリの権限確認

## GitHub Actions設定
```yaml
# .github/workflows/daily_edinet_fetch.yml
- 実行時刻: 毎日午前3時（JST）
- 使用するPythonバージョン: 3.x
- 必要なsecrets: EDINET_API_KEY
```

## ロールバック手順
1. 前日のデータが残っているため、処理失敗時は前日データを使用
2. 必要に応じて手動で再実行

## 監視・ログの設定
- ログファイル: fetch_edinet_financial_documents_YYYYMMDD.log
- エラー通知: GitHub Actionsの通知機能を使用

## 本番環境での注意事項
- API制限（1リクエスト/秒）の遵守
- 大量データ処理時のメモリ使用量
- ディスク容量の定期的な確認