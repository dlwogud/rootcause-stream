"""시연 영상 만들기 — 재생 파일(deck/replay/demo.html)을 브라우저로 열어 사건을 차례로 누르고 녹화한다.

화면을 1920×1080 으로 초당 약 12장 캡처해, 각 장의 실제 표시 시간대로 이어 붙인다(글씨가 선명하다).
클릭한 곳에는 주황 동그라미가 잠깐 보인다. 결론에서 몇 초 머문다(발표장에서 읽을 시간).

준비 (프로젝트 환경과 분리): python3 -m venv pw && pw/bin/pip install playwright imageio-ffmpeg
                              && pw/bin/playwright install chromium
사용: pw/bin/python scripts/record_demo_video.py [--cases E-323 E-357] → deck/assets/demo.mp4
그다음 발표자료를 다시 만들면 6번 뒤에 영상 슬라이드가 들어간다 (deck/build.js).
"""
import argparse
import asyncio
import subprocess
import tempfile
import time
from pathlib import Path

from playwright.async_api import async_playwright
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "deck" / "replay" / "demo.html").as_uri() + "?speed=4&cap=3"
OUT = ROOT / "deck" / "assets" / "demo.mp4"
CLICK_FX = """document.addEventListener('click', e => {
  const d = document.createElement('div');
  Object.assign(d.style, {position:'fixed', left:(e.clientX-22)+'px', top:(e.clientY-22)+'px', width:'44px', height:'44px',
    borderRadius:'50%', border:'3px solid #FF6A2B', background:'rgba(255,106,43,.25)', zIndex:9999, pointerEvents:'none',
    transition:'all .6s ease-out'});
  document.body.appendChild(d);
  requestAnimationFrame(() => { d.style.transform = 'scale(2)'; d.style.opacity = '0'; });
  setTimeout(() => d.remove(), 700);
}, true);"""
FINAL = ("!document.querySelector('#final').classList.contains('hidden') && "
         "document.querySelector('#final').innerText.includes('결론')")


async def record(cases, hold, tmp: Path) -> Path:
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        await pg.goto(SRC); await pg.evaluate(CLICK_FX); await pg.wait_for_timeout(800)
        frames, stop = [], False

        async def grab():
            i = 0
            while not stop:
                t = time.time()
                f = tmp / f"f{i:05d}.jpg"
                await pg.screenshot(path=str(f), type="jpeg", quality=88)
                frames.append((f, t)); i += 1
                await asyncio.sleep(max(0, 1 / 12 - (time.time() - t)))
        task = asyncio.create_task(grab())
        await asyncio.sleep(2.0)
        for cid in cases:
            await pg.click(f"#case-{cid}")
            await pg.wait_for_timeout(1500)
            await pg.wait_for_function(FINAL, timeout=120000)
            await asyncio.sleep(hold)
        stop = True; await task
        await b.close()
    lst = tmp / "frames.txt"
    with open(lst, "w") as fh:
        for (f, t), nxt in zip(frames, frames[1:] + [(None, frames[-1][1] + 0.1)]):
            fh.write(f"file '{f}'\nduration {max(0.01, nxt[1] - t):.4f}\n")
        fh.write(f"file '{frames[-1][0]}'\n")
    return lst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=["E-323", "E-357"])
    ap.add_argument("--hold", type=float, default=6.0, help="결론에서 머무는 초")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as d:
        lst = asyncio.run(record(a.cases, a.hold, Path(d)))
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-vf", "fps=30,scale=out_range=tv:out_color_matrix=bt709,format=yuv420p",
                        "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "20",
                        "-movflags", "+faststart", str(OUT)], check=True)
    print(f"→ {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
