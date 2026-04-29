---
name: etf-tw-graphify-lesson
description: Graphify ETF co-occurrence bias lesson
category: etf-tw
---

# ETF_TW + Graphify 整合 lesson

## 核心教訓：Graphify ETF 共現強度是文件頻率偏差

### 問題
Graphify KG 中 00679B + 00878 節點 dominant（最多連線），看起來最重要，但這是**錯的解讀**。

### 根因
這些 ETF 的高共現是因為：
1. 建構期預設名單殘留（某人之前測試時反覆用這兩檔）
2. 文件頻率 bias：同一個文檔出現多次 → 累計更多 edge

### 正確用法
Graphify co-occurrence = 被動式文獻關聯信號（誰被同一來源提到）
≠ 主動式重要度指標

### 禁止事項
- 勿以 graphify node degree / edge weight 直接做 ETF 推薦排序
- 勿聲稱某 ETF「在知識圖譜中重要」因為共現次數高

### 驗證方法
懷疑時：看 edge 來源是否來自同一文件（用 graphify-out/graph.json 查 source metadata）
