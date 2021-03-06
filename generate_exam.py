# https://github.com/Ryz3D/generate_exam2

import xml.etree.ElementTree as ET
import os, sys, subprocess, jinja2, importlib, environments._envhelper

factory_settings = {
    "precision": "4",
    "decimal_separator": ".",
    "task_join": "\\n",
    "subtask_join": "\\n",
    "e_max": "2",
    "e_min": "-2",
    "short_name_format": "A{}",
}

default_settings = {}
default_context = {}
default_formatters = {}

comment_separator = "#"
output_dir = "generate"


class Variable:
    def __init__(self):
        self.value = 0
        self.expression = ""


class GenericFile:
    def __init__(self):
        self.settings = {}
        self.var_code = ""
        self.definitions = {}
        self.latex = ""


class Subtask:
    def __init__(self):
        self.points = 0
        self.latex = ""


class TaskFile:
    def __init__(self):
        self.generic = GenericFile()
        self.subtasks = []
        self.local_vars = {}


class BaseFile:
    def __init__(self):
        self.generic = GenericFile()
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
        print('ERROR: environment "' + name + '" was not found')
        raise err


# returns unique human-readable name
def path_to_name(path):
    return path.split("/")[-1].split(".")[0]


# parses generic "a = b # comment" syntax, returns dict
# exception_cb: called with part of incorrect syntax
def parse_dict(text, exception_cb=None, any_cb=None):
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
                if any_cb == None:
                    if "=" in part:
                        key = part.split("=")[0].strip()
                        value = "=".join(part.split("=")[1:]).strip()
                        dic[key] = value
                    else:
                        exception_cb(part)
                else:
                    any_cb(part)

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
# generic: object to store output data
def parse_vars(text, generic: GenericFile):
    definitions = {}

    def vars_cb(part):
        if "=" in part:
            key = part.split("=")[0].strip()
            definitions[key] = "=".join(part.split("=")[1:]).strip()

    parse_dict(text, None, vars_cb)

    generic.var_code = text
    generic.definitions.update(**definitions)


# loads generic data from file, returns GenericFile
# extra_handler: called to handle unknown tags
# base: if a task is being loaded, pass its corresponding base, else itself
def load_generic(path, base: BaseFile, extra_handler=None):
    if extra_handler == None:

        def extra_handler(e):
            print("WARNING: unknown tag <" + e.tag + '> in file "' + path + '"')

    xml = ET.parse(path)
    generic = GenericFile()
    generic.settings = base.generic.settings or default_settings
    has_latex = False

    for e in xml.getroot():
        txt = e.text
        if e.tag == "settings":
            generic.settings = parse_settings(txt, base.generic.settings)
        elif e.tag == "variables":
            parse_vars(txt, generic)
        elif e.tag == "latex":
            generic.latex = txt
            has_latex = True
        elif e.tag == "latexfile":
            rel_path = "/".join(path.split("/")[:-1]) + "/"
            with open(rel_path + txt.strip(), encoding="utf-8") as f:
                generic.latex = f.read()
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
                    except (ValueError, TypeError):
                        print(
                            "ERROR: Could not parse tag <points>"
                            + (e_child.text or "")
                            + "</points> as int"
                        )
                elif e_child.tag == "latex":
                    sub.latex = (e_child.text or "").strip()
                elif e_child.tag == "latexfile":
                    rel_path = "/".join(path.split("/")[:-1]) + "/"
                    with open(
                        rel_path + (e_child.text or "").strip(), encoding="utf-8"
                    ) as f:
                        sub.latex = f.read().strip()
            task.subtasks.append(sub)

    task.generic = load_generic(path, base, task_extra)

    return task


# sets variables from definition, returns dict
# generic: object storing loaded variables, definitions
# base: object containing context
def set_vars(generic: GenericFile, base: BaseFile):
    try:
        exec(generic.var_code, base.exec_context)
    except Exception as e:
        print('ERROR: Executing "' + generic.var_code + '": ' + str(e))

    vars = {}
    for k, v in generic.definitions.items():
        var = Variable()
        var.expression = v
        var.value = base.exec_context[k]
        vars[k] = var

    return vars


# generates formatter handler to add variable data into formatter call
def generate_single_formatter(vars, func, settings):
    def handler(key=None, *args):
        environments._envhelper.settings = settings
        environments._envhelper.vars = vars

        if type(key) == type(""):
            # try looking up variable
            value = None
            try:
                value = vars[key]
            except KeyError as err:
                print(
                    'WARNING: could not find variable "'
                    + err.args[0]
                    + '". passing as string'
                )
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
def process_file(base: BaseFile, path):
    base.exec_context = {}
    base.exec_context.update(**default_context)
    base.global_vars = set_vars(base.generic, base)
    base.tasks = []

    if not "TASK_FILES" in base.global_vars:
        print('WARNING: no "TASK_FILES" in file "' + path + '"')
    else:
        rel_path = "/".join(path.split("/")[:-1]) + "/"
        for t in base.global_vars["TASK_FILES"].value:
            base.tasks.append(load_task(rel_path + t, base))

    for t in base.tasks:
        t.local_vars = set_vars(t.generic, base)

    result = ()

    for sol in range(2):
        jcontext_shared = {
            "SHOW_SOL": sol == 1,
        }

        jcontext_base = {
            "TASKS": "",
            "POINTSUM_TOTAL": 0,
            "POINT_ARRAY": [],
            "SHORT_NAME_ARRAY": [],
            **generate_formatters(base.global_vars, base.generic.settings),
        }

        task_join = base.generic.settings["task_join"].replace("\\n", "\n")

        environments._envhelper.settings = base.generic.settings
        for k, v in base.global_vars.items():
            if type(v.value) == type(0):
                jcontext_shared[k] = environments._envhelper.ftos(v.value)
            else:
                jcontext_shared[k] = v.value

        for t_index in range(len(base.tasks)):
            t = base.tasks[t_index]
            jvars = {}
            environments._envhelper.settings = t.generic.settings
            for k, v in t.local_vars.items():
                if type(v.value) == type(0):
                    jvars[k] = environments._envhelper.ftos(v.value)
                else:
                    jvars[k] = v.value

            jcontext_task_shared = {
                "POINTSUM_TASK": 0,
                "POINT_ARRAY_TASK": [],
                "TASK_N": t_index + 1,
                **generate_formatters(
                    {
                        **base.global_vars,
                        **t.local_vars,
                    },
                    t.generic.settings,
                ),
            }
            jcontext_task = {
                **jcontext_shared,
                **jcontext_task_shared,
                **jvars,
                "SUBTASKS": "",
            }

            subtask_join = t.generic.settings["subtask_join"].replace("\\n", "\n")

            for s_index in range(len(t.subtasks)):
                s = t.subtasks[s_index]
                jcontext_subtask = {
                    **jcontext_shared,
                    **jcontext_task_shared,
                    **jvars,
                    "POINTS": s.points,
                    "SUBTASK_N": s_index + 1,
                    **generate_formatters(
                        {
                            **base.global_vars,
                            **t.local_vars,
                        },
                        t.generic.settings,
                    ),
                }
                jcontext_task["SUBTASKS"] += (
                    # if there is an UndefinedError here, a formatter or variable could not be found
                    jinja2.Template(s.latex).render(jcontext_subtask)
                    + subtask_join
                )
                jcontext_task["POINTSUM_TASK"] += s.points
                jcontext_base["POINTSUM_TOTAL"] += s.points
                jcontext_task["POINT_ARRAY_TASK"].append(s.points)
            jcontext_base["POINT_ARRAY"].append(jcontext_task["POINTSUM_TASK"])
            jcontext_base["SHORT_NAME_ARRAY"].append(
                jcontext_task["SHORT_NAME"]
                if "SHORT_NAME" in jcontext_task
                else base.generic.settings["short_name_format"].format(t_index + 1)
            )
            jcontext_base["TASKS"] += (
                jinja2.Template(t.generic.latex).render(jcontext_task) + task_join
            )

        # adds final result to tuple
        result += (
            jinja2.Template(base.generic.latex).render(
                {**jcontext_shared, **jcontext_base}
            ),
        )

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
    base.generic = load_generic(path, base, base_extra)

    if not env_loaded:
        print('WARNING: no environment loaded in file "' + path + '"')

    return base


# renders file, optionally with solution, returns nothing
def generate_latex(path, sol):
    res1, res2 = process_file(load_base(path), path)

    name = path_to_name(path)
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    print('Generating "' + name + '.tex"')
    with open(output_dir + "/" + name + ".tex", "w", encoding="utf-8") as f:
        f.write(res1)
    if sol:
        print('Generating solution "' + name + '_sol.tex"')
        with open(output_dir + "/" + name + "_sol.tex", "w", encoding="utf-8") as f:
            f.write(res2)


# converts path from .tex to .pdf, returns nothing
def convert_pdf(path):
    name = path_to_name(path)
    print('Generating pdf "' + name + '.pdf"')

    args = [
        "pdflatex",
        "--output-directory=" + output_dir,
        "-quiet",
        "-interaction",
        "nonstopmode",
        '"' + name + '"',
    ]

    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    comm = proc.communicate()
    if comm[1]:
        print("ERROR pdflatex: " + comm[1].decode("utf-8"))
    if comm[0]:
        print("pdflatex: " + comm[0].decode("utf-8"))


# deletes .aux and .log files
def clean_aux():
    for f in os.listdir(output_dir):
        if (
            f.endswith(".aux")
            or f.endswith(".log")
            or f.endswith(".out")
            or f.endswith(".tex")
        ):
            os.remove(output_dir + "/" + f)


# handle file with cli options
def handle_file(path, convert_mode, sol):
    generate_latex(path, sol)
    name = path_to_name(path)
    for i in range(convert_mode):
        convert_pdf(name + ".tex")
        if sol:
            convert_pdf(name + "_sol.tex")


# handle folder with cli options
def handle_folder(name, convert_mode, sol):
    for f in os.listdir(name):
        p = name + "/" + f
        if os.path.isfile(p) and f.endswith(".xml"):
            handle_file(p, convert_mode, sol)


def help():
    print(
        """
generate_exam.py V2

Usage:
    python generate_exam.py [OPTIONS] [FILE/FOLDER]

Options:
    -h   Help
    -s   Don't generate solution
          -> Task and solution by default
    -k   Keep LaTeX files (.aux .log .out .tex)
    -o [OUTPUT FOLDER] Set output folder for all files
    -p   Generate pdf (twice)
    -p1  Generate pdf once (faster, but might break LaTeX lastpage)
"""
    )


def main():
    global output_dir

    if "-h" in sys.argv or "--help" in sys.argv or len(sys.argv) == 1:
        help()
        return

    if "-o" in sys.argv:
        output_dir = sys.argv[sys.argv.index("-o") + 1]
        output_dir = output_dir.replace("\\", "/").rstrip("/")

    target = sys.argv[-1].replace("\\", "/")
    convert_mode = 0
    if "-p1" in sys.argv:
        convert_mode = 1
    if "-p" in sys.argv:
        convert_mode = 2
    sol = not "-s" in sys.argv

    if os.path.isdir(target):
        handle_folder(target, convert_mode, sol)
    elif os.path.isfile(target):
        handle_file(target, convert_mode, sol)
    else:
        print('Target "' + target + '" not found')

    if not "-k" in sys.argv and convert_mode > 0:
        clean_aux()


if __name__ == "__main__":
    main()
