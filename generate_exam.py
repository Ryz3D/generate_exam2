"""
generate_exam.py V2

pip dependencies:
    pip install jinja2

TODO:
    - zu dokumentierendes dokumentieren
    - check pdflatex accessibility
    - symbol_to_tex greek (i.e. pi -> \pi)
    - units (meter incl. centi)
        - *10^ beyond Mega/pico
    - plotting
        - per variable? buffer and change parameter
    - handbuch
        - base
            TASKS
            POINTS_TOTAL
        - task
            SUBTASKS
            POINTS_TASK
        - subtask
            POINTS
"""

from environments.exam import gen_env

import xml.etree.ElementTree as ET
import math, decimal, subprocess, jinja2

settings = {}

# converts float to nice human-readable string
def ftos(f, disable_exp=False):
    if not disable_exp:
        digits = math.floor(math.log10(f))
        if digits < int(settings["e_min"]) or digits > int(settings["e_max"]):
            return ftos(f * 10 ** -digits, True) + "*10^{" + str(digits) + "}"

    ctx = decimal.Context(prec=4, Emin=decimal.MIN_EMIN, Emax=decimal.MAX_EMAX)
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

env = gen_env({
    "settings": lambda: settings,
    "ftos": ftos,
    "symbol_to_tex": symbol_to_tex,
})

default_settings = env["settings"]
default_context = env["context"]
default_formatters = env["formatters"]

comment_separator = "#"
file_ext = ".xml"

class Variable:
    def __init__(self):
        self.value = 0
        self.expression = ""

class GenericFile:
    def __init__(self):
        self.settings = {}
        self.variables = {}
        self.latex = ""

class Subtask:
    def __init__(self):
        self.points = 0
        self.latex = ""

class TaskFile:
    def __init__(self):
        self.generics = GenericFile()
        self.subtasks = []
        self.local_vars = {}

class BaseFile:
    def __init__(self):
        self.generics = GenericFile()
        self.tasks = []
        self.exec_context = {}
        self.global_vars = {}

# parses generic "a = b # comment" syntax, returns dict
# exception_cb: called with part of incorrect syntax
def parse_dict(text, exception_cb=None):
    if exception_cb == None:

        def exception_cb(part):
            print('WARNING: could not parse "' + part + '"')

    dic = {}

    for line in text.split("\n"):
        for part in line.split(";"):
            part = part.split(comment_separator)[0].strip()  # cuts off comments
            if part != "":
                if "=" in part:
                    key = part.split("=")[0].strip()
                    value = part.split("=")[1].strip()
                    dic[key] = value
                else:
                    exception_cb(part)

    return dic

# parses settings from text definition, returns dict, omitted settings are set to defaults
# base_settings: used instead of default settings
def parse_settings(text, base_settings=None):
    settings = base_settings or default_settings

    def except_setting(part):
        raise AssertionError("Invalid setting: " + part)

    overrides = parse_dict(text, except_setting)

    for k, v in overrides.items():
        settings[k] = v.strip('"')

    return settings

# parses variables from text definition, returns dict with Variable objects
# base: BaseFile to execute for
def parse_vars(text, base: BaseFile):
    def except_vars(part):
        exec(part, base.exec_context)

    vars = parse_dict(text, except_vars)

    return vars

# loads generic data from file, returns GenericFile
# extra_handler: called to handle unknown tags
# base: if a task is being loaded, pass its corresponding base, else itself
def load_generic(path, base: BaseFile, extra_handler=None):
    if extra_handler == None:

        def extra_handler(e):
            print("WARNING: unknown tag <" + e.tag + '> in file "' + path + '"')

    xml = ET.parse(path)
    generic = GenericFile()
    has_latex = False

    for e in xml.getroot():
        if e.tag == "settings":
            generic.settings = parse_settings(e.text, base.generics.settings)
        elif e.tag == "variables":
            generic.variables = parse_vars(e.text, base)
        elif e.tag == "latex":
            generic.latex = e.text
            has_latex = True
        else:
            extra_handler(e)

    if not has_latex:
        raise AssertionError('Missing <latex> tag in file "' + path + '"')

    return generic

# loads task file from path, returns TaskFile
# base: corresponding BaseFile
def load_task(path, base: BaseFile):
    task = TaskFile()

    def task_extra(e: ET.Element):
        if e.tag == "subtask":
            sub = Subtask()
            for e_child in e.iter():
                if e_child.tag == "points":
                    try:
                        sub.points = int(e_child.text)
                    except ValueError:
                        print(
                            "ERROR: Could not parse tag <points>"
                            + e_child.text
                            + "</points> as int"
                        )
                elif e_child.tag == "latex":
                    sub.latex = (e_child.text or "").strip() + (
                        e_child.tail or ""
                    ).strip()
            task.subtasks.append(sub)

    task.generics = load_generic(path, base, task_extra)

    return task

# sets variables from definition, returns dict
def set_vars(variables, context):
    vars = {}

    for k, v in variables.items():
        var = Variable()
        var.expression = v
        try:
            exec("exec_output = " + v, context)
            var.value = context[k] = context["exec_output"]
        except Exception as e:
            print('ERROR: Setting variable "' + k + " = " + v + '": ' + str(e))
            context[k] = 0
        vars[k] = var

    return vars

# generates formatter handler to add variable data into formatter call
def generate_single_formatter(vars, func, local_settings):
    def handler(key = None, *args):
        global settings
        settings = local_settings

        if key == None:
            return func(*args)
        else:
            try:
                return func(symbol_to_tex(key), vars[key], *args)
            except KeyError:
                return "?"

    return handler

# generates dictionary of formatter handlers for all formatters
def generate_formatters(vars, settings):
    results = {}

    for name, func in default_formatters.items():
        results[name] = generate_single_formatter(vars, func, settings)

    return results

# finishes processing and inserts data, returns processed latex as string
def process_file(base: BaseFile):
    base.exec_context = {
        **base.exec_context,
        **default_context,
    }

    base.global_vars = set_vars(base.generics.variables, base.exec_context)
    for t in base.tasks:
        t.local_vars = set_vars(t.generics.variables, base.exec_context)

    result = ()

    for sol in range(2):
        jcontext_shared = {
            "SHOW_SOL": sol == 1,
        }

        jcontext_base = {
            "TASKS": "",
            "POINTS_TOTAL": 0,
            **generate_formatters(base.global_vars, base.generics.settings),
        }

        task_join = base.generics.settings["task_join"].replace("\\n", "\n")

        for k, v in base.global_vars.items():
            jcontext_shared[k] = v.value

        for t in base.tasks:
            jvars = {}
            for k, v in t.local_vars.items():
                jvars[k] = v.value

            jcontext_task = {
                "SUBTASKS": "",
                "POINTS_TASK": 0,
                **generate_formatters(
                    {
                        **base.global_vars,
                        **t.local_vars,
                    },
                    t.generics.settings
                ),
            }

            subtask_join = t.generics.settings["subtask_join"].replace("\\n", "\n")

            for s in t.subtasks:
                jcontext_subtask = {
                    **jcontext_shared,
                    "POINTS": s.points,
                    **generate_formatters(
                        {
                            **base.global_vars,
                            **t.local_vars,
                        },
                        t.generics.settings
                    ),
                }
                jcontext_task["SUBTASKS"] += (
                    jinja2.Template(s.latex).render(jcontext_subtask) + subtask_join
                )
                jcontext_task["POINTS_TASK"] += s.points
                jcontext_base["POINTS_TOTAL"] += s.points
            jcontext_base["TASKS"] += (
                jinja2.Template(t.generics.latex).render(
                    {
                        **jcontext_shared,
                        **jcontext_task,
                    }
                )
                + task_join
            )

        result += (jinja2.Template(base.generics.latex).render(
            {**jcontext_shared, **jcontext_base}
        ),)

    return (result)

# loads base file from path, returns BaseFile
def load_base(path):
    base = BaseFile()
    base.generics = load_generic(path, base)

    if not "tasks" in base.generics.variables:
        raise AssertionError('Missing "tasks" variable in file: "' + path + '"')

    for t in eval(base.generics.variables["tasks"]):
        base.tasks.append(load_task(t + file_ext, base))
    del base.generics.variables["tasks"]

    return base

# renders file with and without solution, returns nothing
def generate_latex(name):
    res1, res2 = process_file(load_base(name + file_ext))

    with open("aux_files/" + name + "_aufg.tex", "w", encoding="utf-8") as f:
        f.write(res1)
    with open("aux_files/" + name + "_lösg.tex", "w", encoding="utf-8") as f:
        f.write(res2)

# converts path from .tex to .pdf, returns nothing
def convert_pdf(path):
    args = "pdflatex --output-directory=aux_files -quiet -interaction nonstopmode \"{}\"".format(path)

    proc = subprocess.Popen(args.split(" "), stdout=subprocess.PIPE)
    comm = proc.communicate()
    if comm[1]:
        print("ERROR pdflatex: " + comm[1].decode("utf-8"))
    if comm[0]:
        print("pdflatex: " + comm[0].decode("utf-8"))

def main():
    generate_latex("beispiel1")
    convert_pdf("beispiel1_aufg.tex")
    convert_pdf("beispiel1_lösg.tex")

if __name__ == "__main__":
    main()
