---
name: macos-pdf-ui-review-fallback
description: 在 vision 工具不可用時，用 macOS Quick Look + Vision OCR 從 PDF/截圖抓 UI 版面問題
version: 1.0.0
---

# macOS PDF UI Review Fallback

適用情境：
- 使用者丟 PDF 或截圖，要我抓 UI/UX / dashboard 版面問題
- `vision_analyze` / browser vision 回報模型不支援 image input
- 仍需要快速、可執行地指出擁擠、層級混亂、欄位過密等問題

## 核心流程

### 1. 先確認檔案存在
用 terminal 檢查目標 PDF 或圖片路徑存在。

### 2. PDF 先轉成縮圖 PNG
優先用 macOS Quick Look：
```bash
mkdir -p /tmp/pdf_preview
qlmanage -t -s 2000 -o /tmp/pdf_preview /absolute/path/to/file.pdf
```
輸出通常會是：
`/tmp/pdf_preview/<filename>.pdf.png`

補充：
- Quick Look 這條路很適合「單頁 dashboard 截圖被包成 PDF」的情境。
- 若 PDF 是多頁文件，Quick Look thumbnail 可能只給首頁；先確認這份 PDF 是否本質上就是單張截圖。
- 這次實測 `qlmanage` 很穩，適合先拿來做 UI 版面檢視入口。

### 3. 不要依賴 vision 工具
若 vision 工具報：
- `this model does not support image input`
- browser_vision 同樣失敗
就直接放棄影像模型，改走本機 OCR。

### 4. 用 macOS Vision Framework OCR
建立臨時 Swift 腳本，用 `Vision` + `AppKit` 讀 PNG：
```swift
import Foundation
import Vision
import AppKit

let path = "/tmp/pdf_preview/file.pdf.png"
let url = URL(fileURLWithPath: path)
guard let image = NSImage(contentsOf: url) else { exit(1) }
guard let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cgImage = bitmap.cgImage else { exit(1) }

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hant", "en-US"]
request.usesLanguageCorrection = true
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try handler.perform([request])
for o in request.results ?? [] {
    if let top = o.topCandidates(1).first {
        print(top.string)
    }
}
```
執行：
```bash
swift /tmp/ocr.swift | sed -n '1,260p'
```

### 5. 從 OCR 文字反推 UI 問題
重點不要假裝看見每個 pixel；要根據 OCR 可辨識的結構，抓「版面層級問題」：
- 表格欄位是否過多
- 票據/表單是否直接塞在資料表列內
- 操作控制項是否太碎、太密
- 主次層級是否混亂
- 長句說明是否重複出現在每列

### 6. 回答格式
優先輸出：
1. 最大問題
2. 次要問題
3. 可執行修法（P1/P2/P3）
4. 建議下一步實作

## 這次驗證到的實務教訓
- `vision_analyze` 可能完全不支援 image input，即使工具存在也不能假設可用。
- `browser_vision` 也可能同樣失敗；不要卡在重試影像模型。
- `pdftotext -layout` 對純截圖型 PDF 常常抓不到內容。
- `tesseract` 在這個環境可能因圖檔讀取/語言包問題失敗；macOS 原生 Vision OCR 更穩。
- 這次實測甚至出現「PNG 檔存在、file 可辨識、但 tesseract / leptonica 仍回 image file not found」的怪狀況；遇到這種情形不要卡，直接切 Swift + Vision。
- OCR 不求逐字正確，目標是抓 dashboard 的結構失衡與資訊密度問題。

## 適合產出的結論類型
- 「持倉表被交易票據塞爆，應改成按鈕 + drawer/modal」
- 「主表欄位過多，來源/狀態應降級」
- 「按鈕/輸入框過密，應改成兩段式或垂直表單」
- 「首頁資訊卡過多，需收斂成 KPI / 持倉 / 決策三層」

## 不該做的事
- 不要假裝自己看到了影像細節如果實際只拿到 OCR。
- 不要在看不到圖片時硬講配色或像素級對齊。
- 不要把 OCR 雜訊逐字轉述給使用者；要轉成版面診斷。
