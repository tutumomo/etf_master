## 溝通風格
- 偏好精簡回應，不喜歡長篇空泛說明
- 喜歡 A/B/C 選項式呈現
- 生氣時回應更短（≤3行）
- 金融術語要用白話翻譯
- ⚠️ 所有輸出必須繁體中文，禁止簡體中文
§
TOMO 對持倉/掛單查詢極度重視誠實性；禁止用 state、記憶或推測倒推 live 持倉。若 live API 也不足以確認，必須直接承認無法確認，並優先請他提供券商 app/網頁截圖協助解讀。
§
偏好小額交易；ETF_TW dashboard sizing_policy 的最小交易單位預設應設為 5，而不是大單位。
§
TOMO 極度在意版本控管；修好/驗收過的變更必須 commit+push 並回報 commit hash。先釐清實際路徑再動手，不接受混用 OpenClaw 與 Hermes 路徑。
§
TOMO 對『進度透明』非常敏感；不喜歡助理看起來停住、失聯或把排查責任丟回給他。做調查型任務時應持續主動往下查，並只回報具體進度/結果；若他要求暫停，就乾脆停下等待資料。
§
TOMO 要求 Hermes 設定調整必須以實機可驗證流程進行，禁止憑印象或幻覺描述設定狀態。
§
TOMO 決策：未來程式修改與 agent 對齊設定交由專門 code agent（如 Claude Code/Codex/Gemini）處理；本助理角色以執行為主，不負責編碼實作。
§
TOMO 堅持所有輸出必須是繁體中文，禁止簡體字混入。即使是摘要表格、策略名稱、技術術語的中文也要繁體。「复利」→「複利」、「实证」→「實證」等。
§
TOMO 對 dashboard 驗證非常在意實機狀態；若 dashboard 未啟動，不能宣稱已測。驗證 dashboard 必須先確認/啟動正確服務，再用實際 HTTP 回應與 port 狀態佐證。
§
TOMO expects ETF_TW release/version work to align with the latest GitHub/CHANGELOG version, not only SKILL.md frontmatter. A version bump of +0.0.1 means increment from the current latest release/tag (e.g. v1.4.16 → v1.4.17), and release updates must include README.md version record, CHANGELOG.md, commit, push, and tag.
§
TOMO 對版本發布完整性要求很高；發布或 bump 版本時必須同步更新 root README、skills/ETF_TW/README.md、SKILL.md、CHANGELOG.md、commit、push、tag，並以遠端內容驗證，不接受只改一半。
§
TOMO 家庭券商配置：TOMO 本人使用永豐金證券；太太與女兒使用國泰證券；兒子使用元大證券。