from environments._envhelper import settings, ftos, symbol_to_tex
import math, random

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
        },

        # formatters used in latex
        "formatters": {
            "test":     lambda: symbol_to_tex(""),
            "dec":      lambda: settings["decimal_separator"],
            "val":      lambda x, v: ftos(v.value),
            "geg":      lambda x, v: "${}={}$".format(x, ftos(v.value)),
            "ges":      lambda x, v: "${}$".format(x),
            "ges2":     lambda x, v: "${}$ (ansonsten mit {} rechnen)".format(x, ftos(v.value)),
            "sol":      lambda x, v: "{}={}={}".format(x, v.expression.replace("**", "^"), ftos(v.value)),
            "e_base":   lambda x, v: ftos(v.value / (10 ** math.floor(math.log10(v.value))), True),
            "e_expo":   lambda x, v: str(math.floor(math.log10(v.value))),
        }
    }
