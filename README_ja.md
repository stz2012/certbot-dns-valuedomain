# certbot-dns-valuedomain

[![CI](https://github.com/chrono-meter/certbot-dns-valuedomain/workflows/CI/badge.svg)](https://github.com/chrono-meter/certbot-dns-valuedomain/actions)
[![PyPI version](https://badge.fury.io/py/certbot-dns-valuedomain.svg)](https://badge.fury.io/py/certbot-dns-valuedomain)
[![Python Versions](https://img.shields.io/pypi/pyversions/certbot-dns-valuedomain.svg)](https://pypi.org/project/certbot-dns-valuedomain/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Certbot用のValueDomain DNSプラグインです。

このプラグインは、ValueDomain APIを使用してTXTレコードを作成・削除することで、`dns-01`チャレンジのプロセスを自動化します。

[English Documentation](README.md)

## 機能

- ✅ DNS-01チャレンジの自動完了
- ✅ ワイルドカード証明書のサポート
- ✅ TXTレコードの自動クリーンアップ
- ✅ 指数バックオフによるリトライ処理
- ✅ レート制限の処理
- ✅ 包括的なエラーハンドリング
- ✅ 安全な認証情報管理

## インストール

### PyPIからインストール（推奨）

```bash
pip install certbot-dns-valuedomain
```

### ソースからインストール

```bash
git clone https://github.com/chrono-meter/certbot-dns-valuedomain.git
cd certbot-dns-valuedomain
pip install -e .
```

## 必要条件

- Python 3.9以上
- Certbot 1.1.0以上
- ValueDomainアカウント（API利用可能）
- ValueDomainで管理されているドメイン

## 設定

### コマンドライン引数

| 引数 | 説明 | デフォルト |
|------|------|-----------|
| `--dns-valuedomain-credentials` | ValueDomain認証情報ファイル（必須） | なし |
| `--dns-valuedomain-propagation-seconds` | DNS伝播の待機時間（秒） | 60 |

### 認証情報ファイル

ValueDomain APIの情報を含む認証情報ファイルを作成します：

```ini
# ValueDomain API認証情報
dns_valuedomain_api_key = あなたのAPIキー
dns_valuedomain_domain = example.com
```

このファイルのパスは、`--dns-valuedomain-credentials`コマンドライン引数で指定します。

#### セキュリティのベストプラクティス

**重要:** 認証情報ファイルは適切なパーミッションで保護してください：

```bash
chmod 600 /path/to/valuedomain.ini
```

推奨される保存場所：`~/.secrets/certbot/valuedomain.ini`

## 使用例

### 証明書の取得

```bash
certbot certonly 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com
```

### ワイルドカード証明書の取得

```bash
certbot certonly 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com 
  -d '*.example.com'
```

### カスタム伝播時間での証明書取得

DNS伝播の問題が発生する場合は、待機時間を増やしてください：

```bash
certbot certonly 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  --dns-valuedomain-propagation-seconds 120 
  -d example.com
```

### 証明書の更新

```bash
certbot renew 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini
```

### cronによる自動更新

crontabに追加（`crontab -e`）：

```cron
# 毎日深夜0時に証明書を更新
0 0 * * * certbot renew --authenticator dns-valuedomain --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini --quiet
```

または、systemdタイマーを使用（モダンなシステムで推奨）：

```bash
# certbotタイマーを有効化
systemctl enable --now certbot-renew.timer
```

### テスト実行（ドライラン）

```bash
certbot certonly --dry-run 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com
```

## ValueDomain APIキーの取得方法

1. [ValueDomain](https://www.value-domain.com/)にログイン
2. アカウント設定に移動
3. API設定セクションへ移動
4. 新しいAPIキーを生成
5. APIキーを認証情報ファイルにコピー
6. ドメインがValueDomainで適切に設定されていることを確認

## トラブルシューティング

### DNS伝播エラー

DNS伝播タイムアウトエラーが発生する場合：

```bash
# 伝播待機時間を増やす
--dns-valuedomain-propagation-seconds 120
```

### API認証エラー

**エラー:** `API authentication failed`

**解決方法:**
- APIキーが正しく、有効であることを確認
- ドメインがValueDomainアカウントで管理されていることを確認
- 認証情報ファイルのパーミッションが正しいことを確認（`chmod 600`）
- 認証情報ファイルのパスが正しいことを確認

### パーミッション拒否エラー

**エラー:** 認証情報ファイル読み込み時の`Permission denied`

**解決方法:**
```bash
chmod 600 ~/.secrets/certbot/valuedomain.ini
```

### レート制限エラー

プラグインは指数バックオフを使用してレート制限を自動的に処理します。継続的にレート制限に達する場合：
- 証明書リクエストの頻度を減らす
- ValueDomainサポートに連絡してAPI制限の引き上げを依頼

### デバッグモード

詳細なエラー情報を表示するには、`--debug`フラグを使用：

```bash
certbot certonly --debug 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com
```

### よくある問題

#### 問題：「プラグインが見つかりません」

```bash
# プラグインを再インストール
pip uninstall certbot-dns-valuedomain
pip install certbot-dns-valuedomain
```

#### 問題：「認証情報の形式が無効です」

認証情報ファイルが以下の形式に従っていることを確認：
```ini
dns_valuedomain_api_key = your_key
dns_valuedomain_domain = example.com
```

## 開発

### 開発環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/chrono-meter/certbot-dns-valuedomain.git
cd certbot-dns-valuedomain

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venvScriptsactivate

# 開発用依存関係をインストール
pip install -r requirements-dev.txt

# 編集可能モードでインストール
pip install -e .
```

### テストの実行

```bash
# すべてのテストを実行
pytest tests/

# カバレッジ付きで実行
pytest tests/ --cov=certbot_dns_valuedomain --cov-report=html

# カバレッジレポートを表示
open htmlcov/index.html
```

### コード品質

```bash
# コードフォーマット
black certbot_dns_valuedomain tests

# コードリント
flake8 certbot_dns_valuedomain tests

# 型チェック
mypy certbot_dns_valuedomain --ignore-missing-imports
```

### コミット前のテスト実行

```bash
# すべてのチェックを実行
black certbot_dns_valuedomain tests && 
flake8 certbot_dns_valuedomain tests && 
pytest tests/ --cov=certbot_dns_valuedomain
```

## コントリビューション

プルリクエストを歓迎します!お気軽にご提出ください。

### コントリビューションガイドライン

1. リポジトリをフォーク
2. フィーチャーブランチを作成（`git checkout -b feature/amazing-feature`）
3. 変更を加える
4. 新機能のテストを追加
5. すべてのテストが通ることを確認（`pytest tests/`）
6. コードをフォーマット（`black .`）
7. 変更をコミット（`git commit -m '素晴らしい機能を追加'`）
8. ブランチにプッシュ（`git push origin feature/amazing-feature`）
9. プルリクエストを開く

### コードスタイル

- PEP 8ガイドラインに従う
- コードフォーマットにBlackを使用
- 該当する場合は型ヒントを追加
- 包括的なドキュメント文字列を記述
- 新機能にはユニットテストを含める

## セキュリティ

### セキュリティ問題の報告

セキュリティ脆弱性を発見した場合は、issue trackerを使用せず、メンテナーに直接メールしてください。

### セキュリティのベストプラクティス

- バージョン管理に認証情報をコミットしない
- 認証情報ファイルに厳格なファイルパーミッション（600）を使用
- APIキーを定期的にローテーション
- 環境固有の認証情報を使用
- 機密情報の漏洩がないかログを確認

## ライセンス

このプロジェクトはApache License 2.0の下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。

## サポート

- **Issues:** [GitHub Issues](https://github.com/chrono-meter/certbot-dns-valuedomain/issues)
- **ドキュメント:** [GitHub Wiki](https://github.com/chrono-meter/certbot-dns-valuedomain/wiki)
- **ディスカッション:** [GitHub Discussions](https://github.com/chrono-meter/certbot-dns-valuedomain/discussions)

## 謝辞

- [Certbot](https://github.com/certbot/certbot) - Let's Encryptクライアント
- [ValueDomain](https://www.value-domain.com/) - DNSプロバイダー
- このプロジェクトのすべてのコントリビューター

## 関連プロジェクト

- [Certbot](https://github.com/certbot/certbot) - 公式Certbotクライアント
- [certbot-dns-cloudflare](https://github.com/certbot/certbot/tree/master/certbot-dns-cloudflare) - Cloudflare DNSプラグイン
- [certbot-dns-route53](https://github.com/certbot/certbot/tree/master/certbot-dns-route53) - Route53 DNSプラグイン

## 変更履歴

各バージョンの変更リストについては[CHANGELOG.md](CHANGELOG.md)をご覧ください。

## ロードマップ

- [ ] 単一の認証情報ファイルでの複数ドメインサポート
- [ ] 強化されたロギングオプション
- [ ] Dockerコンテナサポート
- [ ] ValueDomain APIサンドボックスとの統合テスト
- [ ] パフォーマンスの最適化

## 著者

**chrono-meter**
**stz2012**

## プロジェクトステータス

このプロジェクトは積極的にメンテナンスされています。IssueとPull Requestは定期的にレビューされます。

---

**注意:** このプラグインはValueDomainまたはLet's Encryptとは公式には提携していません。