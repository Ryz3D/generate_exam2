"""
More info here: https://github.com/Ryz3D/generate_exam2

TODO:
    - plotting
        - per variable? buffer and change parameter
"""

import xml.etree.ElementTree as ET
import os, sys, subprocess, jinja2, importlib, environments._envhelper

factory_settings = {
    "precision": "4",
    "decimal_separator": ".",
    "task_join": "\\n",
    "subtask_join": "\\n",
    "e_max": "2",
    "e_min": "-2",
}

default_settings = {}
default_context = {}
default_formatters = {}

comment_separator = "#"
#file_ext = ".xml"
output_dir = "generate"
file_ext = ""

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

def load_env(name):
    global default_settings
    global default_context
    global default_formatters

    try:
        env = importlib.import_module("environments." + name)
        e = env.gen_env()

        default_settings.update(e["settings"])
        default_context.update(e["context"])
        default_formatters.update(e["formatters"])
    except ModuleNotFoundError as err:
        print("ERROR: environment \"" + name + "\" was not found")
        raise err

# parses generic "a = b # comment" syntax, returns dict
# exception_cb: called with part of incorrect syntax
def parse_dict(text, exception_cb=None):
    if text == None:
        return {}

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
    generic.settings = base.generics.settings or default_settings
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
def generate_single_formatter(vars, func, settings):
    def handler(key = None, *args):
        environments._envhelper.settings = settings
        environments._envhelper.vars = vars

        if type(key) == type(""):
            # try looking up variable
            value = None
            try:
                value = vars[key]
            except KeyError as err:
                print("WARNING: could not find variable \"" + err.args[0] + "\". passing as string")
                return func(key, *args)
            return func(environments._envhelper.symbol_to_tex(key), value, *args)
        else:
            if key == None:
                return func()
            else:
                return func(key, *args)

    return handler

# generates dictionary of formatter handlers for all formatters
def generate_formatters(vars, s):
    results = {}

    for name, func in default_formatters.items():
        results[name] = generate_single_formatter(vars, func, s)

    return results

# finishes processing and inserts data, returns processed latex as string tuple (no_sol, sol)
def process_file(base: BaseFile):
    base.exec_context.update(**default_context)
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
            "POINTSUM_TOTAL": 0,
            "POINT_ARRAY": [],
            "SHORTNAME_ARRAY": [],
            **generate_formatters(base.global_vars, base.generics.settings),
        }

        task_join = base.generics.settings["task_join"].replace("\\n", "\n")

        environments._envhelper.settings = base.generics.settings
        for k, v in base.global_vars.items():
            if type(v.value) == type(0):
                jcontext_shared[k] = environments._envhelper.ftos(v.value)
            else:
                jcontext_shared[k] = v.value

        for t in base.tasks:
            jvars = {}
            environments._envhelper.settings = t.generics.settings
            for k, v in t.local_vars.items():
                if type(v.value) == type(0):
                    jvars[k] = environments._envhelper.ftos(v.value)
                else:
                    jvars[k] = v.value

            jcontext_task = {
                **jcontext_shared,
                **jvars,
                "SUBTASKS": "",
                "POINTSUM_TASK": 0,
                "POINT_ARRAY_TASK": [],
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
                    **jvars,
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
                    # if there is an UndefinedError here, a formatter or variable could not be found
                    jinja2.Template(s.latex).render(jcontext_subtask) + subtask_join
                )
                jcontext_task["POINTSUM_TASK"] += s.points
                jcontext_base["POINTSUM_TOTAL"] += s.points
                jcontext_task["POINT_ARRAY_TASK"].append(s.points)
            jcontext_base["POINT_ARRAY"].append(jcontext_task["POINTSUM_TASK"])
            #todo: If shortname (e.g. "Ü-Bonus" is availabe, replace by shortname. Else by current task number
            jcontext_base["SHORTNAME_ARRAY"].append("DummySN")  
            jcontext_base["TASKS"] += (
                jinja2.Template(t.generics.latex).render(jcontext_task)
                + task_join
            )

        # adds final result to tuple
        result += (jinja2.Template(base.generics.latex).render(
            {**jcontext_shared, **jcontext_base}
        ), )

    return result

# loads base file from path, returns BaseFile
def load_base(path):
    global default_settings
    global default_context
    global default_formatters

    global env_loaded
    env_loaded = False

    default_settings = {**factory_settings}
    default_context = {}
    default_formatters = {}

    def base_extra(e: ET.Element):
        global env_loaded
        if e.tag == "env":
            load_env(e.text.strip())
            env_loaded = True

    base = BaseFile()
    base.generics = load_generic(path, base, base_extra)

    if not env_loaded:
        print("WARNING: no environment loaded in file \"" + path + "\"")

    if not "tasks" in base.generics.variables:
        print("WARNING: no \"tasks\" in file \"" + path + "\"")
        base.tasks = []
    else:
        path_parts = path.replace("\\", "/").split("/")
        rel_path = ""
        for p in range(len(path_parts) - 1):
            rel_path += path_parts[p] + "/"
        for t in eval(base.generics.variables["tasks"]):
            base.tasks.append(load_task(rel_path + t + file_ext, base))
        del base.generics.variables["tasks"]

    return base

# renders file with and without solution, returns nothing
def generate_latex(path, sol):
    res1, res2 = process_file(load_base(path + file_ext))

    name = path.replace("\\", "/").split("/")[-1]
    name = os.path.splitext(name)[0]
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    with open(output_dir + "/" + name + ".tex", "w", encoding="utf-8") as f:
        f.write(res1)
    if sol:
        with open(output_dir + "/" + name + "_sol.tex", "w", encoding="utf-8") as f:
            f.write(res2)

# converts path from .tex to .pdf, returns nothing
def convert_pdf(path):
    name = path.replace("\\", "/").split("/")[-1]
    args = [
        "pdflatex",
        "--output-directory=" + output_dir,
        "-quiet",
        "-interaction",
        "nonstopmode",
        "\"" + name + "\"",
    ]

    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    comm = proc.communicate()
    if comm[1]:
        print("ERROR pdflatex: " + comm[1].decode("utf-8"))
    if comm[0]:
        print("pdflatex: " + comm[0].decode("utf-8"))

# deletes .aux and .log files
def clean_aux(del_tex):
    for f in os.listdir(output_dir):
        if f.endswith(".aux") or f.endswith(".log") or f.endswith(".out"):
            os.remove(output_dir + "/" + f)
        if del_tex and f.endswith(".tex"):
            os.remove(output_dir + "/" + f)

# handle file with cli options
def handle_file(name, tex_only, sol):
    generate_latex(name, sol)
    name = os.path.splitext(name)[0]
    if not tex_only:
        convert_pdf(name + ".tex")
        if sol:
            convert_pdf(name + "_sol.tex")

def handle_folder(name, tex_only, sol):
    for f in os.listdir(name):
        p = os.path.join(name, f)
        if os.path.isfile(p):
            handle_file(p[:-4], tex_only, sol)

def help():
    print("""
generate_exam.py V2

Usage:
    python generate_exam.py [OPTIONS] [FILE/FOLDER]

Options:
    -h Help
    -t Generate TeX only, no pdf conversion
        -> Without this flag pdflatex is required!
    -s Generate no-solution only
        -> Normally generates both files
    -k Keep log files (.aux .log .out)
    -d Delete .tex files too (keep only .pdf)
    -o <OUTPUT DIRECTORY>
""")

def main():
    if "-h" in sys.argv or len(sys.argv) == 1:
        help()
        return
    
    if os.path.isdir(sys.argv[-1]):
        handle_folder(sys.argv[-1], "-t" in sys.argv, not "-s" in sys.argv)
    else:
        handle_file(sys.argv[-1], "-t" in sys.argv, not "-s" in sys.argv)

    if not "-k" in sys.argv:
        clean_aux("-d" in sys.argv)

    #todo: Handle -o <OUTPUT DIRECTORY> and overwrite output_dir

if __name__ == "__main__":
    main()
