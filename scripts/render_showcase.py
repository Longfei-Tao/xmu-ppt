"""Render the original showcase with PowerPoint; compose its actual slide PNGs.

Windows only, optional maintainer tool: python -m pip install pywin32
Does not edit the PPTX. Refuses to run while PowerPoint is already running.
"""
from pathlib import Path
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples/quickstart"


def main():
    if os.name != "nt":
        raise RuntimeError("This optional renderer requires Windows and Microsoft PowerPoint")
    # PowerPoint COM may share a process even when DispatchEx is used.
    # Never attach to, close, or quit a pre-existing interactive session.
    processes = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE", "/FO", "CSV", "/NH"],
        capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if b'powerpnt.exe' in processes.stdout.lower():
        raise RuntimeError("PowerPoint is running. Save and close it yourself before rendering.")
    import win32com.client

    output = SAMPLE / "preview"
    output.mkdir(exist_ok=True)
    app = win32com.client.DispatchEx("PowerPoint.Application")
    deck = None
    try:
        if app.Presentations.Count:
            raise RuntimeError("PowerPoint acquired another presentation; rendering stopped.")
        deck = app.Presentations.Open(str(SAMPLE / "demo.pptx"), ReadOnly=True,
                                      Untitled=False, WithWindow=False)
        findings = []
        fonts = set()
        for i in range(1, deck.Slides.Count + 1):
            slide = deck.Slides(i)
            slide.Export(str(output / f"slide-{i:02d}.png"), "PNG", 1600, 900)
            for shape in slide.Shapes:
                if not shape.HasTextFrame or not shape.TextFrame.HasText:
                    continue
                fonts.add(str(shape.TextFrame.TextRange.Font.Name))
                text = shape.TextFrame2.TextRange
                if (text.BoundWidth > shape.Width + 3 or
                        text.BoundHeight > shape.Height + 3):
                    findings.append({"slide": i, "shape": shape.Name, "issue": "text bounds exceed frame"})
        report = {"renderer": f"Microsoft PowerPoint {app.Version}",
                  "slides": deck.Slides.Count, "fonts_reported": sorted(fonts),
                  "text_bounds_findings": findings}
        (output / "render.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        if deck is not None:
            deck.Close()
        # A user could have opened a deck after our initial process check.
        if app.Presentations.Count == 0:
            app.Quit()

    # Compose unchanged screenshots. No synthetic slide content is added.
    canvas = Image.new("RGB", (1664, 1028), "#EDF3F8")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    for i, label in enumerate(("01 / 封面", "02 / 目录", "03 / 正文", "04 / 示意图表"), 1):
        x = 24 + ((i - 1) % 2) * 820
        y = 20 + ((i - 1) // 2) * 510
        draw.text((x, y), label, fill="#17324D", font=font)
        with Image.open(output / f"slide-{i:02d}.png") as page:
            page = page.convert("RGB").resize((800, 450), Image.Resampling.LANCZOS)
            canvas.paste(page, (x, y + 42))
    canvas.save(output / "overview.png", optimize=True)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
