import math, decimal

settings = {}
vars = {}

# converts float to nice human-readable string
def ftos(f, disable_exp=False):
    if f == 0:
        return "0"

    if not disable_exp:
        digits = math.floor(math.log10(f))
        if digits < int(settings["e_min"]) or digits > int(settings["e_max"]):
            return ftos(f * 10 ** -digits, True) + "*10^{" + str(digits) + "}"

    ctx = decimal.Context(prec=int(settings["precision"]), Emin=decimal.MIN_EMIN, Emax=decimal.MAX_EMAX)
    s = format(ctx.create_decimal_from_float(f), "f")
    if "." in s:
        short = s.rstrip("0").replace(".", settings["decimal_separator"])
        if short[-1] == ".":
            return short[:-1]
        else:
            return short
    else:
        return s

# converts sub- and supertext to proper tex notation
def symbol_to_tex(sym):
    tex = ""

    for g in ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega"]:
        if sym.lower().startswith(g):
            tex = "\\"

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
