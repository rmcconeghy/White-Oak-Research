/* Run against the two locally served revisions in home-visual.yml. */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
const browser = await chromium.launch({channel:"chrome",headless:true});
const output="screenshots";
await mkdir(output,{recursive:true});
const results=[], failures=[];
try {
  for(const [width,height] of [[1920,1080],[1080,1920],[390,844]]){
    for(const [revision,port] of [["before",8765],["after",8766]]){
      const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1});
      const errors=[];
      page.on("pageerror",e=>errors.push(e.message));
      await page.goto("http://127.0.0.1:"+port,{waitUntil:"networkidle"});
      await page.evaluate(()=>document.fonts.ready);
      if(revision==="after"){
        await page.locator('[data-chart="spending"] svg').waitFor();
        await page.locator('[data-chart="dialysis"] svg').waitFor();
      }
      await page.screenshot({path:output+"/"+revision+"-"+width+"x"+height+".png"});
      const metrics=await page.evaluate(()=>{
        const tiles=[...document.querySelectorAll(".analysis-tile")];
        const rects=tiles.map(t=>{const {x,y,width,height,bottom}=t.getBoundingClientRect();return{x,y,width,height,bottom};});
        const textSizes=[...document.querySelectorAll(".tile-chart svg text")].map(t=>{
          const scale=t.getScreenCTM();
          return parseFloat(getComputedStyle(t).fontSize)*Math.hypot(scale.a,scale.b);
        });
        return {
          cards:rects,
          columns:new Set(rects.map(r=>Math.round(r.x))).size,
          horizontalOverflow:document.documentElement.scrollWidth>innerWidth,
          minSvgText:textSizes.length?Math.min(...textSizes):null,
          chartsLoaded:document.querySelectorAll("[data-chart] svg").length,
          essaysOutside:!document.querySelector(".top-analyses .essay-panel"),
          directLabels:[...document.querySelectorAll('[data-chart="spending"] text')].map(t=>t.textContent)
        };
      });
      results.push({revision,width,height,errors,...metrics});
      if(revision==="after"){
        const assert=(ok,msg)=>{if(!ok)failures.push(width+"x"+height+": "+msg);};
        assert(metrics.cards.length===4,"four cards");
        assert(metrics.columns===(width>=900?2:1),"responsive columns");
        assert(metrics.cards.every(r=>Math.abs(r.width-metrics.cards[0].width)<1&&Math.abs(r.height-metrics.cards[0].height)<1),"equal tile dimensions");
        assert(!metrics.horizontalOverflow,"horizontal overflow");
        assert(metrics.minSvgText>=11,"chart text minimum size");
        assert(metrics.chartsLoaded===2,"SVG charts loaded");
        assert(metrics.essaysOutside,"essays outside grid");
        assert(!errors.length,"no page errors");
        assert(["$1.64T","$1.12T","$0.93T","$0.56T","$1.03T","$5.28T"].every(v=>metrics.directLabels.some(t=>t.includes(v))),"source values");
        if(width===1920)assert(metrics.cards.every(r=>r.bottom<=height),"all cards above fold");
      }
      await page.close();
    }
  }
} finally {
  await browser.close();
  await writeFile(output+"/measurements.json",JSON.stringify({results,failures},null,2));
}
if(failures.length)throw new Error(failures.join("\n"));
