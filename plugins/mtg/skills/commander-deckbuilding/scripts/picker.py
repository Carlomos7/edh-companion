#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build a card picker page for close calls: the user sees the options with images and reasons,
picks per slot, and copies the result back into the chat.

Input JSON:
{"title": "Vader B3: close calls",
 "slots": [{"slot": "Card draw #9", "pick": 1, "note": "replacing Divination",
            "options": [{"name": "Phyrexian Arena", "why": "...", "price": 4.5, "img": "https://cards.scryfall.io/...",
                         "theme": "off-theme", "evidence": "EDHREC 41% of 1,203 decks"}]}]}

Usage: picker.py candidates.json --out picker.html
Output is one self-contained HTML file (images load from cards.scryfall.io). Open it in a browser,
or publish it as an artifact (then bundle images, since artifacts block outside images).
"""
import argparse, html, json

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--bg:#f7f7f5;--fg:#1b1b1b;--card:#fff;--muted:#666;--line:#ddd;--acc:#6b3fd1}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141416;--fg:#eee;--card:#1e1e22;--muted:#aaa;--line:#333;--acc:#a98bff}}}}
body{{margin:0;font:15px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg)}}
main{{max-width:1100px;margin:0 auto;padding:16px}} h1{{font-size:20px}} h2{{font-size:16px;margin:24px 0 4px}}
.note{{color:var(--muted);margin:0 0 8px}} .opts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}}
label{{background:var(--card);border:2px solid var(--line);border-radius:12px;padding:8px;cursor:pointer;display:block}}
label:has(input:checked){{border-color:var(--acc)}} input{{margin-right:6px}} img{{width:100%;border-radius:8px;display:block;margin-bottom:6px}}
.meta{{font-size:13px;color:var(--muted)}} .bar{{position:sticky;bottom:0;background:var(--bg);padding:12px 0;border-top:1px solid var(--line)}}
button{{font:inherit;padding:10px 16px;border-radius:10px;border:0;background:var(--acc);color:#fff;cursor:pointer}}
textarea{{width:100%;min-height:60px;margin-top:8px;font:13px monospace;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px}}
</style></head><body><main><h1>{title}</h1><p class="note">Pick per slot, then copy your picks back into the chat.</p>
{slots}
<div class="bar"><button id="copy">Copy my picks</button><textarea id="outbox" readonly></textarea></div></main>
<script>
const out=document.getElementById('outbox');
function picks(){{const lines=[];document.querySelectorAll('section').forEach(s=>{{const chosen=[...s.querySelectorAll('input:checked')].map(i=>i.value);
lines.push(s.dataset.slot+': '+(chosen.join(', ')||'(none)'));}});return 'My picks:\\n'+lines.join('\\n');}}
document.addEventListener('change',()=>{{out.value=picks();}});
document.getElementById('copy').onclick=async()=>{{out.value=picks();try{{await navigator.clipboard.writeText(out.value);}}catch(e){{out.select();}}}};
out.value=picks();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates"); ap.add_argument("--out", default="picker.html")
    a = ap.parse_args()
    data = json.load(open(a.candidates, encoding="utf-8"))
    e = html.escape
    parts = []
    for i, s in enumerate(data["slots"]):
        kind = "checkbox" if s.get("pick", 1) > 1 else "radio"
        opts = []
        for o in s["options"]:
            img = f'<img src="{e(o["img"])}" alt="{e(o["name"])}" loading="lazy">' if o.get("img") else ""
            meta = " · ".join(x for x in (f'${o["price"]:.2f}' if o.get("price") is not None else "", o.get("theme", ""),
                                          o.get("evidence", "")) if x)
            opts.append(f'<label><input type="{kind}" name="s{i}" value="{e(o["name"])}">{img}<b>{e(o["name"])}</b>'
                        f'<div>{e(o.get("why", ""))}</div><div class="meta">{e(meta)}</div></label>')
        note = f'<p class="note">{e(s.get("note", ""))}</p>' if s.get("note") else ""
        parts.append(f'<section data-slot="{e(s["slot"])}"><h2>{e(s["slot"])}'
                     f'{" (pick " + str(s["pick"]) + ")" if s.get("pick", 1) > 1 else ""}</h2>{note}'
                     f'<div class="opts">{"".join(opts)}</div></section>')
    open(a.out, "w", encoding="utf-8").write(PAGE.format(title=e(data.get("title", "Card picker")), slots="".join(parts)))
    print(a.out)


if __name__ == "__main__":
    main()
