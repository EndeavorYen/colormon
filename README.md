# 顏色寶可夢探險

和小朋友一起玩的抓寶可夢遊戲：用手機拍下身邊的東西，照片的顏色最像哪隻寶可夢，牠就會出現，再丟球把牠抓起來。

網址：https://endeavoryen.github.io/colormon/

## 怎麼玩
畫面依流程切換，一次只顯示一個步驟：

1. **拍照**：按「打開相機」即時取景，或用「用手機相機拍一張」。
2. **分析顏色**：顯示照片的主要色盤。
3. **遭遇**：寶可夢從草叢跳出來。丟出寶貝球後，球最多晃三下，晃完就抓到，否則寶可夢會跳出來；三顆球用完牠就逃走。抓到的機率只看稀有度，不看丟得好不好。
4. **抓到了**：顯示抓到的寶可夢，存進圖鑑（存在這支手機的瀏覽器裡）。

## 運作方式
- 照片縮成 48×48，中心加權，在 CIELAB 色彩空間用 k-means 抓出 3～4 個主色。
- 每隻寶可夢有主色與配色，雙向比對：照片的顏色要在牠身上找得到，牠的顏色（尤其主色）也要在照片裡找得到。
- 只在「和最像的那隻差不多像」的範圍內隨機挑選（`similarityWindow`），再依相似度、稀有度加權；同一張照片每次可能遇到不同寶可夢，但都是顏色相近的（`randomness` 越大越隨機，`sameResultPerDay: true` 則同色同天結果固定）。
- 圖片即時讀取自 [PokeAPI sprites](https://github.com/PokeAPI/sprites)，本 repo 不存放任何寶可夢圖片。

## 真球模式
不用任何硬體，用手機後鏡頭偵測真的球被丟進畫面。手機可以立在支架上，也可以拿在手上。

1. 遇到寶可夢後，按「真球模式」。
2. 後鏡頭朝向前方地板，遊戲背景會變成鏡頭畫面。
3. 把球丟進鏡頭拍到的範圍：看到球飛進來就是丟出，畫面安靜下來就是落地。

偵測分兩層：
- **移動偵測**：每秒約 15 張、96×72 的畫面，比較前後兩張找出「一小團、方向連貫在移動」的東西。先抵消整個畫面的位移（手持晃動），有紋理的地方門檻自動提高，太大的移動（人）或整個畫面變化（開燈）會被忽略；手機大幅晃動時暫停。
- **球辨識**：用 MediaPipe 物件偵測模型（EfficientDet-Lite0，COCO 的 sports ball 類別）在手機上辨識球。移動之後 1.5 秒內要真的看到一顆球才算丟出，或直接看到球在移動也算。模型載入失敗時自動退回只用移動偵測。

畫面上綠框是辨識到的球，黃圈是只偵測到移動。

設定在 `config.json` 的 `ball`：
- `objectDetection.requireBall`：設成 `false` 就不要求辨識到球（報紙球、襪子球這類模型不一定認得出來時使用）。
- `objectDetection.scoreThreshold`：球辨識的信心門檻，越低越容易認成球。
- `phoneMotionDeg`：手機轉動超過每秒幾度才暫停偵測。
- `diffThreshold`、`maxSize`、`stillMs` 等：移動偵測的靈敏度。

## 資料與擴充
寶可夢不寫死在網頁裡，全部放在 `site/data/`：

```
site/data/
├── config.json        要載入哪些資料包、捕捉率、每次遭遇幾顆球、圖片網址
├── types.json         屬性（名稱、顏色、圖示的 SVG path）
└── packs/
    └── gen1-starter.json
```

資料包格式：

```json
{
  "name": "第一代精選",
  "pokemon": [
    { "id": 25, "name": "皮卡丘", "type": "electric", "rarity": 1, "colors": ["#F8D030", "#E85030"] }
  ]
}
```

- `id`：全國圖鑑編號，也用來抓 PokeAPI 圖片。
- `type`：`types.json` 裡的 key。
- `rarity`：1～3，越高越難遇到也越難抓。
- `colors`：牠的代表色，第一個是主色，比對照片時主色最重要。

**新增寶可夢**：在 `packs/` 加一個新檔，再把路徑加進 `config.json` 的 `packs`。後面的資料包可以覆蓋前面同編號的寶可夢（例如調整顏色）。要新增屬性就在 `types.json` 加一筆。

push 之前可以先跑 `node tools/validate-data.mjs` 檢查格式，CI 部署前也會自動檢查。

## 接硬體（規劃中）
`site/index.html` 預留兩個介面：
寶貝球只要回報「丟出」和「落地」兩件事：
- `window.onBallThrown()`：偵測到被丟出去時呼叫，畫面上的球會飛出去。
- `window.onBallLanded()`：偵測到落地時呼叫，球開始晃動並決定結果。
- `Hardware.notifyEncounter(mon)`：寶可夢出現時呼叫，可在這裡送出提醒指令。

目前是模擬模式：按「丟出寶貝球！」等於丟出，0.7 秒後自動回報落地。

## 部署
push 到 `main` 後，GitHub Actions 會檢查資料格式與網頁語法，再部署到 GitHub Pages。

本機測試：`cd site && python3 -m http.server`，再打開 http://localhost:8000 （直接雙擊 index.html 會讀不到資料檔）。

寶可夢名稱與圖片版權屬於 Nintendo / Creatures / GAME FREAK，本專案為非商業的家庭自用遊戲。
