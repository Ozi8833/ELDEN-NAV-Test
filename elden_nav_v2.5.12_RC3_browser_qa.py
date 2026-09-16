#!/usr/bin/env python3
import asyncio,json,sys
from pathlib import Path
from playwright.async_api import async_playwright

HTML=Path(sys.argv[1] if len(sys.argv)>1 else "ELDEN_NAV_v2.5.12_RC3_single.html").resolve()

async def main():
    results=[]
    def rec(name,ok,detail=""):
        results.append({"name":name,"ok":bool(ok),"detail":str(detail)})
        print(("PASS" if ok else "FAIL"),name,detail)

    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,executable_path="/usr/bin/chromium")
        for width,height in [(320,568),(390,844),(768,1024)]:
            page=await browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
            errs=[]
            page.on("pageerror",lambda e,errs=errs:errs.append(str(e)))
            await page.set_content(HTML.read_text(encoding="utf-8"),wait_until="load")
            await page.wait_for_timeout(250)

            rec(f"{width}px startup",await page.evaluate("APP_VERSION")== "2.5.12")
            sw=await page.evaluate("document.documentElement.scrollWidth")
            rec(f"{width}px no horizontal overflow",sw<=width+2,f"{sw}/{width}")

            if width==390:
                summary=await page.evaluate("""(()=>{const s=hereNavProductionGateSummary();return{
                    total:s.rows.length,errors:s.errors.length,primary:s.primary.length,
                    secondary:s.secondary.length,overview:s.overview.length,
                    back:hereNavPosterGateFor('backhandBlade').mode,
                    gold:hereNavPosterGateFor('goldenVow').mode,
                    milady:hereNavPosterGateFor('milady').mode,
                    dragon:hereNavPosterGateFor('dragoncrestGreatshield').mode,
                    alex:hereNavPosterGateFor('shardAlexander').mode,
                    solitude:hereNavPosterGateFor('solitudeSet').mode
                }})()""")
                rec("gate counts",summary["total"]==36 and summary["errors"]==0 and summary["primary"]==8 and summary["secondary"]==3 and summary["overview"]==2,summary)
                rec("priority6 all primary",all(summary[k]=="FORMAL_PRIMARY" for k in ["back","gold","milady","dragon","alex","solitude"]),summary)

                # Open all six HERE NAV dialogs to ensure rendering path works.
                for gid in ["backhandBlade","goldenVow","milady","dragoncrestGreatshield","shardAlexander","solitudeSet"]:
                    result=await page.evaluate(f"""(()=>{{try{{openLocationGuide('{gid}');const d=document.querySelector('#guideDialog');const img=d.querySelector('.here-nav-visual img');const mode=hereNavPosterGateFor('{gid}').mode;const ok=d.open&&!!img&&img.src.startsWith('data:image/');d.close();return{{ok,mode}};}}catch(e){{return{{ok:false,error:e.message}}}}}})()""")
                    rec(f"{gid} HERE NAV render",result.get("ok") and result.get("mode")=="FORMAL_PRIMARY",result)

                world=await page.evaluate("""(()=>{state.spoilerMode='standard';state.noHintMode=false;goalRevealed=false;renderWorldMap();return{
                    img:document.querySelector('#worldMapImg')?.src.slice(0,30),
                    live:document.querySelector('.world-map-live-goal')?.innerText||''
                }})()""")
                rec("spoiler map preserved",world["img"].startswith("data:image/svg+xml;base64,") and "？？？" in world["live"],world)

            rec(f"{width}px no JS errors",len(errs)==0,errs)
            await page.close()
        await browser.close()

    out=HTML.parent/"ELDEN_NAV_v2.5.12_RC3_BROWSER_QA.json"
    out.write_text(json.dumps({"html":str(HTML),"results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    if not all(x["ok"] for x in results): raise SystemExit(1)
    print("PASS browser QA",out)

asyncio.run(main())
