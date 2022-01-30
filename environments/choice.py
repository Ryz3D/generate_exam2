import environments._envhelper
import random

choices = {}
correct = {}

def format_choice(checked, text):
    return "\\framebox[15px][c]{%s} %s" % ("X" if checked else "\\phantom{X}", text)

def init_choice(id, c, w):
    global choices
    global correct
    choices[id] = random.sample([*c, *w], len(c) + len(w))
    correct[id] = [*c]

def choice_task(id, choice_join = "\n\n"):
    return choice_join.join(map(lambda s: format_choice(False, s), choices[id]))

def choice_sol(id, choice_join = "\n\n"):
    return choice_join.join(map(lambda s: format_choice(s in correct[id], s), choices[id]))

def gen_env():
    return {
        # settings overrideable by files
        "settings": {
        },

        # functions used in variable definition
        "context": {
            "init_choice": init_choice,
        },

        # formatters used in latex
        "formatters": {
            "choice_task": choice_task,
            "choice_sol": choice_sol,
        }
    }
