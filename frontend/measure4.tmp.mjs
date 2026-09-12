import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://localhost:5173", { waitUntil: "networkidle" });

const info = await page.evaluate(() => {
  const main = document.querySelector("main");
  const row1 = main.children[0];
  const row2 = main.children[1];
  const detailScroll = row1.children[1].querySelector(".overflow-y-auto");
  const queueScroll = row2.children[0].querySelector(".overflow-y-auto");
  const resourceScroll = row2.children[1].querySelector(".overflow-y-auto");
  const rect = (el) => el ? { h: Math.round(el.getBoundingClientRect().height), scrollHeight: el.scrollHeight } : null;
  return {
    mainH: Math.round(main.getBoundingClientRect().height),
    row1H: rect(row1),
    row2H: rect(row2),
    detailScroll: rect(detailScroll),
    queueScroll: rect(queueScroll),
    resourceScroll: rect(resourceScroll),
  };
});
console.log(JSON.stringify(info, null, 2));
await browser.close();
