// 進化樹測試：已知的幾個家族 + 全部掃一遍（CI 會執行）
import { readFileSync } from "node:fs";
const base = new URL("../site/data/", import.meta.url);
const read = p => JSON.parse(readFileSync(new URL(p, base), "utf8"));
const evo = read("evolutions.json");
const cfg = read("config.json");
const ids = new Set();
for (const p of cfg.packs) for (const m of read(p).pokemon) ids.add(m.id);

// 和 app.js 的 evoRoot / evoFamily 同樣的走法（從最初的型態往下走完整棵樹）
const root = id => { let n = 0; while (evo[id]?.from && n++ < 12) id = evo[id].from; return id; };
const family = id => { const out = [], walk = x => { out.push(x); (evo[x]?.to || []).forEach(walk); }; walk(root(id)); return out; };

const errors = [];
const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
const CASES = {                    // 任何一隻 → 整個家族（依 DFS 順序）
  4:   [4, 5, 6],                  // 小火龍 → 火恐龍 → 噴火龍（三階，直接下一階只有火恐龍）
  5:   [4, 5, 6], 6: [4, 5, 6],
  1:   [1, 2, 3], 7: [7, 8, 9], 25: [172, 25, 26], 172: [172, 25, 26], 26: [172, 25, 26],
  133: [133, 134, 135, 136, 196, 197, 470, 471, 700], 196: [133, 134, 135, 136, 196, 197, 470, 471, 700],  // 伊布：8 種分支
  265: [265, 266, 267, 268, 269], 269: [265, 266, 267, 268, 269],                                           // 毛毛蟲：兩條各自再進化
  60:  [60, 61, 62, 186], 186: [60, 61, 62, 186],                                                          // 蚊香蝌蚪：蚊香君、蚊香泳士／蚊香蛙皇
  236: [236, 106, 107, 237],                                                                              // 無畏小子：三種
  129: [129, 130], 131: [131],                                                                            // 鯉魚王→暴鯉龍；拉普拉斯沒有進化
};
for (const [id, want] of Object.entries(CASES)) {
  const got = family(+id);
  if (!same(got, want)) errors.push(`#${id} 的家族應該是 ${want.join(",")}，實際是 ${got.join(",")}`);
}
// 小火龍：每一階的「直接下一階」和「前一階」
if (!same(evo[4]?.to || [], [5]) || !same(evo[5]?.to || [], [6]) || evo[6]?.from !== 5 || evo[5]?.from !== 4 || evo[4]?.from) errors.push("小火龍 4→5→6 的關係不對");

// 全掃：每個家族都是一棵樹（沒有環、沒有重複、只有一個根）、編號都存在
const seen = new Set(); let families = 0, maxSize = 0;
for (const k of Object.keys(evo)) {
  const id = +k; if (seen.has(id)) continue;
  const fam = family(id); families++; maxSize = Math.max(maxSize, fam.length);
  if (new Set(fam).size !== fam.length) errors.push(`#${id} 的家族有重複／環：${fam.join(",")}`);
  if (fam.length < 2) errors.push(`#${id} 在 evolutions.json 裡，卻沒有任何進化關係`);
  for (const x of fam) {
    if (seen.has(x)) errors.push(`#${x} 同時在兩個家族裡`);
    seen.add(x);
    if (!ids.has(x)) errors.push(`#${x}（#${id} 的家族）不在任何資料包裡`);
    const par = evo[x]?.from;
    if (par && !(evo[par]?.to || []).includes(x)) errors.push(`#${x} 的上一階 #${par} 沒有把牠列在 to`);
    if (x !== fam[0] && !par) errors.push(`#${x} 沒有上一階卻不是根`);
  }
}
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
console.log(`進化樹測試通過：${families} 個家族（最大 ${maxSize} 隻）、${Object.keys(CASES).length} 個已知案例`);
