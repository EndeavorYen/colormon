# 顏色寶可夢探險

和小朋友一起玩的抓寶可夢遊戲：用手機拍下身邊的東西，照片的顏色最像哪隻寶可夢，牠就會出現，再丟球把牠抓起來。

網址：https://endeavoryen.github.io/colormon/

## 怎麼玩
畫面依流程切換，一次只顯示一個步驟：

1. **拍照**：按「打開相機」即時取景，或用「用手機相機拍一張」。
2. **分析顏色**：顯示照片的主要色盤。
3. **遭遇**：寶可夢從黑影現身。按住黃色按鈕蓄力，在綠色區放開丟球，球最多晃三下，晃完就抓到，否則寶可夢會跳出來；三顆球用完牠就逃走。
4. **抓到了**：顯示抓到的寶可夢，存進圖鑑（存在這支手機的瀏覽器裡）。

## 運作方式
- 照片縮成 48×48，中心加權，在 CIELAB 色彩空間用 k-means 抓出 3～4 個主色。
- 每隻寶可夢有主色與配色，挑出色盤最像的 6 隻，再依稀有度與「色盤 + 日期」的 hash 選一隻；同一個東西同一天結果固定。
- 圖片即時讀取自 [PokeAPI sprites](https://github.com/PokeAPI/sprites)，本 repo 不存放任何寶可夢圖片。

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
- `Hardware.notifyEncounter(mon)`：出現寶可夢時送出震動指令給寶貝球。
- `window.onBallThrow(score)`：寶貝球偵測到投擲後，以 0～1 的分數呼叫。

## 部署
push 到 `main` 後，GitHub Actions 會檢查資料格式與網頁語法，再部署到 GitHub Pages。

本機測試：`cd site && python3 -m http.server`，再打開 http://localhost:8000 （直接雙擊 index.html 會讀不到資料檔）。

寶可夢名稱與圖片版權屬於 Nintendo / Creatures / GAME FREAK，本專案為非商業的家庭自用遊戲。
