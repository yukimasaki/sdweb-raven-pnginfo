# sdweb-raven-pnginfo

Stable Diffusion WebUI (A1111/Forge/EasyReforge) の拡張機能。
画像生成時に自動で [Raven](https://github.com/yukimasaki/raven) に画像とメタデータを送信します。

## インストール

1. SD WebUI の **Extensions** → **Install from URL** を開く
2. 以下の URL を入力して **Install** をクリック:
   ```
   https://github.com/yukimasaki/sdweb-raven-pnginfo.git
   ```
3. SD WebUI を再起動する

## 設定

**Settings** → **Raven Pnginfo** セクションで設定します。

| 設定項目 | デフォルト | 説明 |
|----------|-----------|------|
| Enable Raven integration | OFF | 連携の有効/無効 |
| Raven server URL | `http://localhost:3000` | Raven サーバーの URL |

## 動作

有効化すると、画像生成のたびに以下の情報が Raven に自動送信されます:

- 画像ファイル（ファイルパス経由でコピー）
- ポジティブプロンプト（タグ配列）
- ネガティブプロンプト（タグ配列）
- 生成パラメータ（Steps, Sampler, CFG scale, Seed, Model 等）

Raven が起動していない場合や API 呼び出しに失敗した場合でも、画像生成は中断されません。

## 必要環境

- Stable Diffusion WebUI (A1111/Forge/EasyReforge)
- [Raven](https://github.com/yukimasaki/raven) が同一マシン上で起動していること

## 開発

```bash
# テスト実行
uv run --with pytest --with requests pytest tests/ -v
```

## ライセンス

MIT
