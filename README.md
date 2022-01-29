# generate_exam V2

### This tool provides a Python interface in LaTeX, tailored towards writing exams, with scientific and technical documents easily created aswell

Have a look at the [Wiki](https://github.com/Ryz3D/generate_exam2/wiki) if you want to learn more.

And use the [Documentation](https://github.com/Ryz3D/generate_exam2/wiki/Documentation) as reference.

## Installation

You need the newest version of [Python 3](https://www.python.org/downloads/) and [Jinja2](https://pypi.org/project/Jinja2/). On Linux you sometimes need to use ``python3`` instead of ``python`` and ``pip3`` instead of ``pip``. You can check the current version of ``python`` using ``python --version``.

Once you have Python (and pip) installed, you can install Jinja2 by running:

```
pip install Jinja2
```

If you want to generate .pdf files automatically, you will need ``pdflatex``. It ships with typical LaTeX distributions like [MiKTeX]() and [TeX Live](https://www.tug.org/texlive/). You can check your ``pdflatex`` installation by running ``pdflatex -version``.

## Usage

```
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
```

## Generating examples

To generate the files ``generate/EXAMple.pdf`` and ``generate/EXAMple_sol.pdf`` run:

```
python generate_exam.py -p examples/EXAMple.xml
```

To generate all examples run:

```
python generate_exam.py -p examples
```
