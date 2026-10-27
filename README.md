# 顏色寶可夢探險

和小朋友一起玩的抓寶可夢遊戲：用手機拍下身邊的東西，照片的顏色最像哪隻寶可夢，牠就會出現，再丟球把牠抓起來。

## 怎麼玩
1. 用手機打開 GitHub Pages 網址。
2. 按「打開相機取景」即時對準，或按「用手機相機拍一張」。
3. 按住黃色按鈕蓄力，在綠色區放開丟球；抓到的會存進圖鑑（存在這支手機的瀏覽器裡）。

## 運作方式
- 照片縮成 48×48，中心加權，在 CIELAB 色彩空間用 k-means 抓出 3～4 個主色。
- 每隻寶可夢有主色與配色，挑出色盤最像的 6 隻，再依稀有度與「色盤 + 日期」的 hash 選一隻；同一個東西同一天結果固定。
- 圖片即時讀取自 [PokeAPI sprites](https://github.com/PokeAPI/sprites)，本 repo 不存放任何寶可夢圖片。

## 接硬體（規劃中）
`site/index.html` 預留兩個介面：
- `Hardware.notifyEncounter(mon)`：出現寶可夢時送出震動指令給寶貝球。
- `window.onBallThrow(score)`：寶貝球偵測到投擲後，以 0～1 的分數呼叫。

## 部署
push 到 `main` 後，GitHub Actions 會檢查語法並部署到 GitHub Pages。

寶可夢名稱與圖片版權屬於 Nintendo / Creatures / GAME FREAK，本專案為非商業的家庭自用遊戲。
