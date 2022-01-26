import environments._envhelper
from environments._envhelper import ftos, symbol_to_tex
import math, random
from datetime import datetime

def date():
    return datetime(*reversed(environments._envhelper.vars["date"].value))

def year():
    form = "{time} {year}"
    summer = "SoSe"
    winter = "WiSe"
    if date().month <= 3:
        return form.format_map({"time": winter,"year": date().year - 1})
    else:
        return form.format_map({
            "time": summer if date().month <= 9 else winter,
            "year": date().year,
        })

def gen_env():
    return {
        # settings overrideable by files
        "settings": {
            "precision": "4",
            "decimal_separator": ".",
            "task_join": "\\n",
            "subtask_join": "\\n",
            "e_max": "2",
            "e_min": "-2",
        },

        # functions used in variable definition
        "context": {
            "rand":     lambda min, max, step: random.randint(0, int((max - min) / step)) * step + min,
            "shuffle":  lambda l: random.sample(l, len(l)),
        },

        # formatters used in latex
        "formatters": {
            "year":     year,
            "date":     lambda: date().strftime("%d.%m.%Y"),
            "dec":      lambda: environments._envhelper.settings["decimal_separator"],
            "val":      lambda x, v: ftos(v.value),
            "geg":      lambda x, v: "${}={}$".format(x, ftos(v.value)),
            "ges":      lambda x, v: "${}$".format(x),
            "ges2":     lambda x, v: "${}$ (ansonsten mit {} rechnen)".format(x, ftos(v.value)),
            "sol":      lambda x, v: "{}={}={}".format(x, v.expression.replace("**", "^"), ftos(v.value)),
            "e_base":   lambda x, v: ftos(v.value / (10 ** math.floor(math.log10(v.value))), True),
            "e_expo":   lambda x, v: str(math.floor(math.log10(v.value))),
            "points":   lambda a: " & ".join(map(lambda f: "/ " + str(f), a)),
            "taskColLeftSep":  lambda a: "l|" * len(a),
            "shortname":   lambda a: " & ".join(map(lambda f: str(f), a)),
        }
    }
