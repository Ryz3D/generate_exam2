from environments._envhelper import settings, ftos, symbol_to_tex
import math, random

def unit_helper(f, u1, u2, factor):
    return "{}{}/{}{}".format(ftos(f), u1, ftos(f * factor), u2)

def gen_env():
    return {
        # settings overrideable by files
        "settings": {
            "precision": "2",
            "decimal_separator": ".",
            "task_join": "\\n",
            "subtask_join": "\\n",
            "e_max": "10",
            "e_min": "-10",
        },

        # functions used in variable definition
        "context": {
        },

        # formatters used in latex
        "formatters": {
            "kmh":  lambda f: unit_helper(f, "$\\frac{km}{h}$", "mph", 0.62137),
            "km":   lambda f: unit_helper(f, "km", "mi", 0.62137),
            "m":    lambda f: unit_helper(f, "m", "ft", 3.28084),
            "cm":   lambda f: unit_helper(f, "cm", "\"", 0.3937),
            "km2":  lambda f: unit_helper(f, "km$^2$", "mi$^2$", 0.3861),

#            "kmh":  lambda f: "{}kmh/{}mph".format(ftos(f), ftos(f * 0.62137)),
#            "km":   lambda f: "{}km/{}mi".format(ftos(f), ftos(f * 0.62137)),
#            "m":    lambda f: "{}m/{}ft".format(ftos(f), ftos(f * 3.28084)),
#            "cm":   lambda f: "{}cm/{}\"".format(ftos(f), ftos(f / 2.54)),
#            "km2":  lambda f: "{}km$^2$/{}mi$^2$".format(ftos(f), ftos(f * 2.59)),
        }
    }
