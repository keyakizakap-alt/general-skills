# 形式ごとの作り方

## PowerPoint（.pptx）

- pptx スキル（Anthropic 提供の `pptx` 等）が使えれば、その手順に従う
- 使えない場合は、環境に python-pptx があるか確認する。あれば `scripts/slide_kit.py` の部品（`Deck`、`txt`、`table`、`rect`、`note` など）で組む。文字・図形・表を編集できる形で置き、ページ表記「1 / N」を保存時に入れる。フォントは `Deck(font=...)` で指定する（既定は BIZ UDPゴシック）
- python-pptx が無ければ導入せず（承認が必要）、原稿（Markdown）を作って「pptx 未作成」と報告する
- PDF は LibreOffice で作る（例: `soffice --headless --convert-to pdf --outdir <出力先> <ファイル>.pptx`）。PDF を作る環境に指定フォントが無いと別のフォントで描画され、改行位置が変わる。その場合は報告に書く
- 16:9。テンプレート（.potx）の指定があればそれを使う
- 出典はスライド下部に小さく、話者メモは各スライドのノートに入れる

## claude.ai の Slides / Docs

- その環境に Slides / Docs の作成機能（アーティファクトやドキュメント機能）があれば、それで作る
- 共有・公開は利用者の確認後に行う
- 作れない環境では、1スライドごとに見出し・本文・話者メモ・出典を並べた原稿を Markdown で渡す

## HTML 資料

- 1ファイル（`index.html`）。外部スクリプトを読み込まない。フォントは必要なら Google Fonts のみ
- 16:9 のスライドを縦に並べる。矢印キーで送れるようにしてもよい
- 色は `:root` の CSS 変数で定義し、`prefers-color-scheme: dark` でダークモードを用意する
- 幅390pxで横スクロールが出ない。左右に16px以上の余白。本文は16px以上
- 印刷（PDF化）したとき1スライド1ページになるよう `@media print` で改ページを入れる
