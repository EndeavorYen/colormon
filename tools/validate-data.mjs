// 檢查 site/data 裡的設定與資料包格式，CI 會在部署前執行
import { readFileSync } from "node:fs";

const base = new URL("../site/data/", import.meta.url);
const read = p => JSON.parse(readFileSync(new URL(p, base), "utf8"));
const errors = [];
const HEX = /^#[0-9A-Fa-f]{6}$/;

const cfg = read("config.json");
const types = read("types.json");

for (const [key, t] of Object.entries(types)) {
  if (!t.name) errors.push(`types.json：${key} 缺少 name`);
  if (!HEX.test(t.color || "")) errors.push(`types.json：${key} 的 color 不是 #RRGGBB`);
  if (!t.glyph) errors.push(`types.json：${key} 缺少 glyph（SVG path）`);
}

const owner = new Map(), merged = new Map();
let total = 0;
for (const packPath of cfg.packs) {
  const pack = read(packPath);
  if (!Array.isArray(pack.pokemon)) { errors.push(`${packPath}：缺少 pokemon 陣列`); continue; }
  for (const raw of pack.pokemon) {
    const m = { ...(merged.get(raw.id) || {}), ...raw };   // 後面的資料包可以只覆蓋部分欄位
    merged.set(raw.id, m);
    const tag = `${packPath} #${m.id} ${m.name ?? ""}`;
    if (!Number.isInteger(m.id) || m.id < 1) errors.push(`${tag}：id 必須是正整數`);
    if (!m.name) errors.push(`${tag}：缺少 name`);
    if (!types[m.type]) errors.push(`${tag}：type「${m.type}」不在 types.json 裡`);
    if (![1, 2, 3].includes(m.rarity)) errors.push(`${tag}：rarity 必須是 1、2 或 3`);
    if (!Array.isArray(m.colors) || !m.colors.length || !m.colors.every(c => HEX.test(c)))
      errors.push(`${tag}：colors 必須是 #RRGGBB 陣列（第一個是主色）`);

    owner.set(m.id, packPath);
    total++;
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`資料檢查通過：${Object.keys(types).length} 種屬性、${cfg.packs.length} 個資料包、${owner.size} 隻寶可夢`);
