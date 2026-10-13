"""UI strings for English and Japanese."""

STRINGS = {
    "en": {
        "title": "WebP Converter",
        "lang_btn": "日本語",
        "drop_main": "Drag & drop images here",
        "drop_sub": "or click to browse",
        "drop_active": "Release to add these images",
        "add_files": "Add files",
        "add_folder": "Add folder",
        "clear": "Clear",
        "count_one": "{n} image",
        "count_many": "{n} images",
        "convert_to": "Convert to",
        "png_lossless": "PNG is always lossless",
        "quality": "Quality",
        "preset_small": "Smallest",
        "preset_balanced": "Balanced",
        "preset_high": "High quality",
        "preview_empty": "Preview",
        "estimating": "estimating…",
        "est_size": "≈ {size}",
        "lossless": "Lossless",
        "overwrite": "Overwrite existing files",
        "save_to": "Save to",
        "same_folder": "Same folder as original",
        "custom_folder": "Custom folder",
        "choose": "Choose…",
        "convert_to_fmt": "Convert to {fmt}",
        "cancel": "Stop",
        "open_folder": "Open folder",
        "no_files": "Add some images first.",
        "no_outdir": "Choose an output folder first.",
        "converting": "Converting {i} of {n}",
        "row_wait": "Waiting",
        "row_busy": "Converting",
        "failed_row": "Failed",
        "summary": "{ok} converted · {fail} failed · {saved} saved ({pct}%)",
        "summary_ok": "{ok} converted · {saved} saved ({pct}%)",
        "cancelled": "Stopped",
        "theme": "Dark",
        "theme_alt": "Light",
        "help_title": "How this app works",
        "help_sub": "What every control does.",
        "close": "Close",
        "open_img": "Open",
        "scan_limit": "Only the first {n} images were added.",
    },
    "ja": {
        "title": "WebP 変換ツール",
        "lang_btn": "English",
        "drop_main": "ここに画像をドラッグ＆ドロップ",
        "drop_sub": "クリックして選択",
        "drop_active": "ドロップして画像を追加",
        "add_files": "ファイルを追加",
        "add_folder": "フォルダを追加",
        "clear": "クリア",
        "count_one": "{n} 枚",
        "count_many": "{n} 枚",
        "convert_to": "変換先",
        "png_lossless": "PNG は常にロスレスです",
        "quality": "画質",
        "preset_small": "軽量",
        "preset_balanced": "標準",
        "preset_high": "高画質",
        "preview_empty": "プレビュー",
        "estimating": "計算中…",
        "est_size": "約 {size}",
        "lossless": "ロスレス",
        "overwrite": "既存のファイルを上書きする",
        "save_to": "保存先",
        "same_folder": "元の画像と同じ場所",
        "custom_folder": "フォルダを指定",
        "choose": "選択…",
        "convert_to_fmt": "{fmt} に変換",
        "cancel": "中止",
        "open_folder": "フォルダを開く",
        "no_files": "先に画像を追加してください。",
        "no_outdir": "保存先フォルダを選択してください。",
        "converting": "変換中 {i} / {n}",
        "row_wait": "待機中",
        "row_busy": "変換中",
        "failed_row": "失敗",
        "summary": "{ok} 枚変換 · {fail} 枚失敗 · {saved} 削減（{pct}%）",
        "summary_ok": "{ok} 枚変換 · {saved} 削減（{pct}%）",
        "cancelled": "中止しました",
        "theme": "ダーク",
        "theme_alt": "ライト",
        "help_title": "このアプリの使い方",
        "help_sub": "各機能とボタンの説明です。",
        "close": "閉じる",
        "open_img": "開く",
        "scan_limit": "最初の {n} 枚のみ追加しました。",
    },
}


# Help window: (heading, body) for every control in the app.
HELP = {
    "en": [
        ("Adding images",
         "Drag files onto the drop zone, or click it to browse. Dropping a folder "
         "adds every supported image inside it. Ctrl+O adds files, Ctrl+Shift+O "
         "adds a folder. PNG, JPEG, WebP, GIF, BMP and TIFF can all be read."),
        ("The file list",
         "Each row is named after the file you are going to get, not the one you "
         "added — switch the output format and the names change with it. Below the "
         "name is the source format, its dimensions and its current size. Hover a "
         "row to reveal Open, and ✕ removes it. Clear empties the whole list."),
        ("Size badges",
         "After converting, a green ▼ badge shows how much smaller the file became. "
         "An amber ▲ badge means it got bigger — usually a flat-coloured PNG turned "
         "into lossy WebP. Turning on Lossless normally fixes that case."),
        ("Convert to",
         "WebP is the smallest for the web and keeps transparency and animation. "
         "PNG is lossless and suits logos, screenshots and anything with sharp "
         "edges or transparency. JPEG suits photographs and has no transparency, "
         "so transparent areas are filled with white."),
        ("Quality",
         "Applies to WebP and JPEG. Higher keeps more detail and produces bigger "
         "files. Smallest (55), Balanced (80) and High quality (92) are shortcuts; "
         "the slider sets anything in between. PNG ignores quality entirely because "
         "PNG is always lossless."),
        ("Lossless",
         "WebP only. Switched off, WebP discards fine detail the way JPEG does and "
         "the quality setting decides how much. Switched on, every pixel is "
         "reproduced exactly and quality no longer applies. Photographs get much "
         "bigger this way, but logos, screenshots and flat graphics often get "
         "smaller — and stay perfectly sharp."),
        ("Preview and estimated size",
         "The thumbnail is the first image in the list, really encoded with your "
         "current settings — not a mock-up. The ≈ figure beside Quality is what "
         "that file would weigh. Both update as you move the slider."),
        ("Save to",
         "'Same folder as original' writes each result next to its source. "
         "'Custom folder' collects everything into one folder you choose. An "
         "existing file is never overwritten silently: the output becomes "
         "'name (2).webp' unless you tick Overwrite existing files."),
        ("Converting",
         "Convert starts the batch and the button turns into Stop while it runs; "
         "Esc also stops. Ctrl+Enter starts it from the keyboard. Open folder "
         "opens wherever the last batch was written."),
        ("Language and theme",
         "日本語 / English switches the interface language and Dark / Light switches "
         "the theme. Both are remembered, along with your quality, format and "
         "output settings."),
        ("Offline by design",
         "Nothing leaves this computer. Every conversion runs inside this program, "
         "and outbound network access is blocked when the app starts."),
    ],
    "ja": [
        ("画像を追加する",
         "ドロップゾーンにファイルをドラッグするか、クリックして選択します。フォルダごと"
         "ドロップすると、その中の対応画像がすべて追加されます。Ctrl+O でファイル追加、"
         "Ctrl+Shift+O でフォルダ追加。PNG・JPEG・WebP・GIF・BMP・TIFF を読み込めます。"),
        ("ファイル一覧",
         "各行の名前は、追加した元ファイルではなく、これから作成される出力ファイルの名前"
         "です。変換先を切り替えると名前も変わります。名前の下には元の形式・寸法・現在の"
         "容量を表示します。行にマウスを乗せると「開く」が現れ、✕ でその行を削除します。"
         "「クリア」で一覧を空にします。"),
        ("削減バッジ",
         "変換後、緑の ▼ はどれだけ小さくなったかを示します。橙の ▲ は逆に大きくなった"
         "ことを意味し、多くは平坦な色の PNG を非可逆 WebP にした場合です。「ロスレス」を"
         "有効にすると改善することがほとんどです。"),
        ("変換先",
         "WebP はウェブ向けに最も小さく、透過とアニメーションを保持できます。PNG は可逆"
         "で、ロゴ・スクリーンショット・輪郭のはっきりした画像や透過画像に適します。"
         "JPEG は写真向けで透過を扱えないため、透明部分は白で塗りつぶされます。"),
        ("画質",
         "WebP と JPEG に適用されます。値が大きいほど細部が残り、ファイルは大きくなり"
         "ます。「軽量」(55)・「標準」(80)・「高画質」(92) はよく使う設定への近道で、"
         "スライダーで自由に指定できます。PNG は常に可逆のため、画質設定は使われません。"),
        ("ロスレス",
         "WebP 専用です。オフのとき、WebP は JPEG と同じように細部を捨て、その度合いを"
         "画質設定で調整します。オンにすると全ピクセルがそのまま再現され、画質設定は"
         "使われません。写真は大幅に大きくなりますが、ロゴ・スクリーンショット・平坦な"
         "図版はむしろ小さくなることが多く、輪郭も完全に保たれます。"),
        ("プレビューと推定容量",
         "サムネイルは一覧の先頭の画像を現在の設定で実際にエンコードした結果で、見本では"
         "ありません。「画質」の隣の ≈ はそのファイルの推定容量です。スライダーを動かすと"
         "どちらも更新されます。"),
        ("保存先",
         "「元の画像と同じ場所」は各結果を元ファイルの隣に保存します。「フォルダを指定」は"
         "すべてを選んだフォルダにまとめます。既存のファイルが黙って上書きされることは"
         "なく、「既存のファイルを上書きする」を有効にしない限り、出力は「name (2).webp」"
         "のような名前になります。"),
        ("変換する",
         "「変換」で開始します。実行中はボタンが「中止」に変わり、Esc でも中止できます。"
         "Ctrl+Enter でキーボードから開始できます。「フォルダを開く」は直前の出力先を"
         "開きます。"),
        ("言語とテーマ",
         "「English / 日本語」で表示言語、「ダーク / ライト」でテーマを切り替えます。画質・"
         "変換先・保存先の設定とあわせて記憶されます。"),
        ("オフライン設計",
         "ファイルがこのパソコンの外に出ることはありません。変換はすべてこのアプリ内で"
         "行われ、起動時に外部へのネットワーク接続を遮断しています。"),
    ],
}


def tr(lang, key, **kw):
    text = STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"][key]
    return text.format(**kw) if kw else text
