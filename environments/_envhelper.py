import math, decimal

settings = {}

# converts float to nice human-readable string
def ftos(f, disable_exp=False):
    if not disable_exp:
        digits = math.floor(math.log10(f))
        if digits < int(settings["e_min"]) or digits > int(settings["e_max"]):
            return ftos(f * 10 ** -digits, True) + "*10^{" + str(digits) + "}"

    ctx = decimal.Context(prec=int(settings["precision"]), Emin=decimal.MIN_EMIN, Emax=decimal.MAX_EMAX)
    s = format(ctx.create_decimal_from_float(f), "f")
    if "." in s:
        return s.rstrip("0").replace(".", settings["decimal_separator"])
    else:
        return s.replace(".", settings["decimal_separator"])

# converts sub- and supertext to proper tex notation
def symbol_to_tex(sym):
    tex = ""
    level = 0

    for ci in range(len(sym)):
        if sym[ci] == "^":
            tex += "}" * level
            level = 0
            tex += "^{" + symbol_to_tex(sym[ci + 1:]) + "}"
            break
        elif sym[ci] == "_":
            tex += "_{"
            level += 1
        else:
            tex += sym[ci]

    return tex + "}" * level
