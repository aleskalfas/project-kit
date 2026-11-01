"""Ask Mural which fonts a text box accepts: send one text box with a font it cannot know; Mural refuses
it (nothing is created) and lists the fonts it accepts. Uses the mural-boards tool's own client, loaded
with its error messages left whole.

Usage: uv run --no-project --with pyyaml --with jsonschema python mural_fonts.py <tool.py> <map.yaml>
"""

import re
import sys
import types

import yaml

src = open(sys.argv[1], encoding="utf-8").read().replace('decode(errors="replace")[:300]', 'decode(errors="replace")[:20000]')
mb = types.ModuleType("mural_boards")
mb.__file__ = sys.argv[1]
sys.modules["mural_boards"] = mb
exec(compile(src, sys.argv[1], "exec"), mb.__dict__)
data = yaml.safe_load(open(sys.argv[2]))
api = mb.Mural()
try:
    api.call("POST", f"/murals/{data['mural']}/widgets/textbox",
             [{"x": -99999, "y": -99999, "width": 100, "height": 40, "text": "font probe", "style": {"font": "no-such-font-probe"}}])
    print("accepted: a text box was created (unexpected)")
except mb.ApiError as err:
    fonts = re.findall(r"'([a-z0-9-]+)'", str(err))
    print(len(fonts), "fonts:", " ".join(fonts))
