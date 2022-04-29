"""main module of word2quiz"""
import re
import os
from os.path import exists
import pathlib
import io
import glob
import logging
from dataclasses import dataclass
import gettext
import tkinter as tk
import customtkinter as ctk
from tkhtmlview import HTMLLabel

from tkinter import filedialog
from tkinter.filedialog import askopenfilename, asksaveasfile

from lxml import etree
from rich.console import Console
from rich.pretty import pprint
from rich.prompt import Prompt
import docx2python as d2p

from canvas_robot import CanvasRobot, Answer

GUI = True

_ = gettext.gettext
console = Console(force_terminal=True)  # too trick Pycharm console into show textattributes
cur_dir = os.getcwd()


class InterActiveButton(tk.Button):
    """
    This button expands when the user hovers over it and shrinks when
    the cursor leaves the button.

    If you want the button to expand in both directions just use:
        button = InterActiveButton(root, text="Button", width=200, height=50)
        button.pack()
    If you want the button to only expand to the right use:
        button = InterActiveButton(root, text="Button", width=200, height=50)
        button.pack(anchor="w")

    This button should work with all geometry managers.
    """

    def __init__(self, master, max_expansion: int = 12, bg="dark blue",
                 fg="#dad122", **kwargs):
        # Save some variables for later:
        self.max_expansion = max_expansion
        self.bg = bg
        self.fg = fg

        # To use the button's width in pixels:
        # From here: https://stackoverflow.com/a/46286221/11106801
        self.pixel = tk.PhotoImage(width=1, height=1)

        # The default button arguments:
        button_args = dict(cursor="hand2", bd=0, font=("arial", 18, "bold"),
                           height=50, compound="c", activebackground=bg,
                           image=self.pixel, activeforeground=fg)
        button_args.update(kwargs)
        super().__init__(master, bg=bg, fg=fg, **button_args)

        # Bind to the cursor entering and exiting the button:
        super().bind("<Enter>", self.on_hover)
        super().bind("<Leave>", self.on_leave)

        # Save some variables for later:
        self.base_width = button_args.pop("width", 200)
        self.width = self.base_width
        # `self.mode` can be "increasing"/"decreasing"/None only
        # It stops a bug where if the user wuickly hovers over the button
        # it doesn't go back to normal
        self.mode = None

    def increase_width(self) -> None:
        if self.width <= self.base_width + self.max_expansion:
            if self.mode == "increasing":
                self.width += 1
                super().config(width=self.width)
                super().after(5, self.increase_width)

    def decrease_width(self) -> None:
        if self.width > self.base_width:
            if self.mode == "decreasing":
                self.width -= 1
                super().config(width=self.width)
                super().after(5, self.decrease_width)

    def on_hover(self, event: tk.Event = None) -> None:
        # Improvement: use integers instead of "increasing" and "decreasing"
        self.mode = "increasing"
        # Swap the `bg` and the `fg` of the button
        super().config(bg=self.fg, fg=self.bg)
        super().after(5, self.increase_width)

    def on_leave(self, event: tk.Event = None) -> None:
        # Improvement: use integers instead of "increasing" and "decreasing"
        self.mode = "decreasing"
        # Reset the `fg` and `bg` of the button
        super().config(bg=self.bg, fg=self.fg)
        super().after(5, self.decrease_width)


class Word2Quiz(ctk.CTkFrame):

    def __init__(self):
        super().__init__()

        self.tkvar_font_normalize = None
        self.cb_font_normalize = None
        self.html_lbl_docsample = None
        self.btn_convert2data = None
        self.data_dict = None
        self.lbl_quiz_data = None
        self.entry_file_name = None
        self.background_image = None
        self.background_image_label = None

    def init_ui(self):
        """
        ---------------------------------------------
                [filename]            box text docx

                         [ Open file]
        ---------------------------------------------

            #question [dropbox]
                                     box parsed data
            [v] check box testrun

                        [ Convert ]
        ---------------------------------------------

            course_id [ input ]

                                    browserbox/link

                        [ Create quiz]
        ---------------------------------------------

        :return:
        """

        self.master.title("Word to Canvasquiz Converter")  # that's the tk root
        self.pack(fill="both", expand=True)

        # img_filepath = os.path.abspath(os.path.join(os.pardir, "data", "witraster.png"))
        # assert os.path.exists(img_filepath)

        # self.background_image = tk.PhotoImage(file=img_filepath)
        # self.background_image_label = tk.Label(self, image=self.background_image)
        # self.background_image_label.place(x=0, y=0)

        # self.canvas = tk.Canvas(self, width=500, height=700,
        #                        background='white',
        #                        highlightthickness=0,
        #                        borderwidth=0)
        # self.canvas.place(x=50, y=60)
        try:
            self.master.wm_iconbitmap("../data/word2quiz.ico")
        except FileNotFoundError:
            print('icon file is not available')
            pass
        file = ""
        default_text = ("Your extracted quizdata will "
                        "appear here.\n\n please check the data")

        # the frames
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill=tk.X)
        data_frame = ctk.CTkFrame(self)
        data_frame.pack(fill=tk.X)
        canvas_frame = ctk.CTkFrame(self)
        canvas_frame.pack(fill=tk.X)

        # File_frame Input: button Output: filename label, box with sample
        btn_open_file = ctk.CTkButton(file_frame,
                                      text=" Open ",
                                      width=30,
                                      corner_radius=8,
                                      command=self.open_word_file)
        btn_open_file.pack(side="bottom", padx=5, pady=5)
        # # Select word file
        lbl_file = ctk.CTkLabel(file_frame,
                                width=120,
                                height=25,
                                text="Select docx file",
                                text_font=("Arial", 20)
                                )
        lbl_file.pack(side="top", pady=5)

        self.entry_file_name = ctk.CTkEntry(file_frame,
                                            placeholder_text="no file selected",
                                            width=200,
                                            height=25,
                                            border_width=2,
                                            corner_radius=10)
        self.entry_file_name.pack(side="top", pady=5, padx=5)

        # # Select word file
        lbl_font_normalize = ctk.CTkLabel(file_frame,
                                          width=80,
                                          height=25,
                                          text="Normalize fontsize?",
                                          text_font=("Arial", 12)
                                          )
        lbl_font_normalize.pack(side="left", pady=5)

        # Create a Tkinter variable
        tkvar_font_normalize = tk.StringVar(self.master)

        # Dictionary with options
        choices = {'no change', '12', '14', '16'}
        self.tkvar_font_normalize = tkvar_font_normalize
        self.tkvar_font_normalize.set('no change')  # set the default option
        self.cb_font_normalize = tk.OptionMenu(file_frame, self.tkvar_font_normalize, *choices, )
        self.cb_font_normalize.config(width=10)

        # link function to change dropdown
        self.tkvar_font_normalize.trace('w', self.on_change_cb_normalize_fontsize)

        self.cb_font_normalize.pack(side="left", pady=5)

        self.html_lbl_docsample = HTMLLabel(file_frame,
                                            # width=100,
                                            html="""
            <p><i>no content yet</i></p>
            """)

        self.html_lbl_docsample.pack(side="right", pady=20, padx=20)

        # data_frame Inputs: num questions, testrun Output: box quizdata
        self.btn_convert2data = ctk.CTkButton(data_frame,
                                              text="Convert",
                                              width=30,
                                              command=self.show_quizdata,
                                              state=tk.DISABLED)
        self.btn_convert2data.pack(side="bottom", padx=5, pady=5)

        #  ======================= Box to show quizdata
        self.lbl_quiz_data = ctk.CTkLabel(data_frame,
                                          width=350,
                                          height=120,
                                          )
        self.lbl_quiz_data.configure(text=default_text)
        self.lbl_quiz_data.pack(side="right", padx=20, pady=80)

        # ===============================Button to access save2word method=================
        # save2canvas = Button(root, text="Save to Word File", font=('arial', 10, 'bold'),
        #                      bg="RED", fg='WHITE', command=save2canvas)
        # save2canvas.place(x=255, y=320)

        # button = InterActiveButton(self,
        #                           text="Button",
        #                           width=200,
        #                           height=50)
        # Using `anchor="w"` forces the button to expand to the right.
        # If it's removed, the button will expand in both directions
        # button.pack(padx=20, pady=20, anchor="w")

    def on_change_cb_normalize_fontsize(self, *args):
        print(self.tkvar_font_normalize.get())

    def open_word_file(self):
        f = askopenfilename(defaultextension=".docx",
                            filetypes=[("Word docx", "*.docx")])
        if f == "":
            f = None
        else:
            self.entry_file_name.delete(0, tk.END)
            self.entry_file_name.config(fg="blue")
            self.entry_file_name.insert(0, f)

        normalize = self.tkvar_font_normalize.get()
        normalize = int(normalize) if normalize.isdigit() else 0
        par_list, not_recognized_list = get_document_html(filename=f,
                                                          normalized_fontsize=normalize)
        tot_html = ''
        for p_type, ans_weight, text, html in par_list:
            tot_html += f'<p style="color: green">{p_type} {html}</p>' \
                if ans_weight else f"<p>{p_type} {html}</p>"
        if not_recognized_list:
            html += "<hr><p>Not recognized:</p>"
            for _, _, html in not_recognized_list:
                tot_html += html
        self.html_lbl_docsample.set_html(tot_html)
        # enable next step

        self.btn_convert2data.configure(state=tk.NORMAL)

    def show_quizdata(self):
        """
        put quiz_dat in textbox as text
        :return:
        """
        normalize = self.tkvar_font_normalize.get()
        normalize = int(normalize) if normalize.isdigit() else 0
        self.data_dict = parse_document_d2p(filename=f,
                                            check_num_questions=self.check_num_questions,
                                            normalize_fontsize=normalize)
        self.lbl_quiz_data.delete(1.0, END)
        data_text = pprint.pformat(self.data_dict)
        self.lbl_quiz_data.insert(INSERT, data_text)

    def save2canvas(self):
        """
        Create the quiz in Canvas using ghe quizdata
        :return: not used"
        """
        canvasrobot = CanvasRobot()
        stats, canvasrobot.create_quizzes_from_data(course_id=course_id,
                                                    data=self.quiz_data)


# define Python user-defined exceptions
class Error(Exception):
    """Base class for other exceptions"""
    pass


class IncorrectNumberofQuestions(Error):
    """ quiz contains unexpected number of questions"""
    pass


class IncorrectAnswerMarking(Error):
    """ the aswers of a particular question should have
        only one good (!) marking (or total of 100 points) """
    pass


# from docx import Document  # package - python-docx !
# import docx2python as d2p
# from xdocmodel import iter_paragraphs

def normalize_size(text: str, size: int):
    parser = etree.XMLParser()
    try:  # can be html or not
        tree = etree.parse(io.StringIO(text), parser)
        # text could contain style attribute
        ele = tree.xpath('//span[starts-with(@style,"font-size:")]')
        if ele is not None and len(ele):
            ele[0].attrib['style'] = f"font-size:{size}pt"
            return etree.tostring(ele[0], encoding='unicode')
    except etree.XMLSyntaxError as e:
        # assume simple html string no surrounding tags
        return f'<span style="font-size:{size}pt">{text}</span>'


FULL_SCORE = 100
TITLE_SIZE = 24
QA_SIZE = 12

# the patterns
title_pattern = \
    re.compile(r"^<font size=\"(?P<fontsize>\d+)\"><u>(?P<text>.*)</u></font>")
title_style_pattern = \
    re.compile(r"^<span style=\"font-size:(?P<fontsize>[\dpt]+)\"><u>(?P<text>.*)</u>")

quiz_name_pattern = \
    re.compile(r"^<font size=\"(?P<fontsize>\d+[^\"]+)\"><b>(?P<text>.*)\s*</b></font>")
quiz_name_style_pattern = re.compile(
    r"^<span style=\"font-size:(?P<fontsize>[\dpt]+)"
    r"(;text-transform:uppercase)?\"><b>(?P<text>.*)\s*</b></span>")
# special match Sam
page_ref_style_pattern = \
    re.compile(r'(\(pp\.\s+[\d-]+)')

q_pattern_fontsize = \
    re.compile(r'^(?P<id>\d+)[).]\s+'
               r'(?P<prefix><font size="(?P<fontsize>\d+)">)(?P<text>.*</font>)')
q_pattern = \
    re.compile(r"^(?P<id>\d+)[).]\s+(?P<text>.*)")

# '!' before the text of answer marks it as the right answer
# idea: use [\d+]  for partially correct answer the sum must be FULL_SCORE
a_ok_pattern_fontsize = re.compile(
    r'^(?P<id>[a-d])\)\s+(?P<prefix><font size="(?P<fontsize>\d+)">.*)'
    r'(?P<fullscore>!)(?P<text>.*</font>)')
a_ok_pattern = \
    re.compile(r"^(?P<id>[a-d])\)\s+(?P<prefix>.*)(?P<fullscore>!)(?P<text>.*)")
# match a-d then ')' then skip whitespace and all chars up to '!' after answer skip </font>

a_wrong_pattern_fontsize = \
    re.compile(r'^(?P<id>[a-d])\)\s+'
               r'(?P<prefix><font size="(?P<fontsize>\d+)">)(?P<text>.*</font>)')
a_wrong_pattern = \
    re.compile(r"^(?P<id>[a-d])\)\s+(?P<text>.*)")


@dataclass()
class Rule:
    name: str
    pattern: re.Pattern
    type: str
    normalized_size: int = QA_SIZE


rules = [
    Rule(name='title', pattern=title_pattern, type='Title'),
    Rule(name='title_style', pattern=title_style_pattern, type='Title'),
    Rule(name='quiz_name', pattern=quiz_name_pattern, type='Quizname'),
    Rule(name='quiz_name_style', pattern=quiz_name_style_pattern, type='Quizname'),
    Rule(name='page_ref_style', pattern=page_ref_style_pattern, type='PageRefStyle'),
    Rule(name='question_fontsize', pattern=q_pattern_fontsize, type='Question'),
    Rule(name='question', pattern=q_pattern, type='Question'),
    Rule(name='ok_answer_fontsize', pattern=a_ok_pattern_fontsize, type='Answer'),
    Rule(name='ok_answer', pattern=a_ok_pattern, type='Answer'),
    Rule(name='wrong_answer_fontsize', pattern=a_wrong_pattern_fontsize, type='Answer'),
    Rule(name='wrong_answer', pattern=a_wrong_pattern, type='Answer'),
]


def get_document_html(filename: str, normalized_fontsize: int = 0):
    """
        :param normalized_fontsize: 0 is no normalization
        :param  filename: filename of the Word docx to parse
        :returns the first X paragraphs as HTML
    """
    #  from docx produce a text with minimal HTML formatting tags b,i, font size
    #  1) questiontitle
    #    a) wrong answer
    #    b) !right answer
    doc = d2p.docx2python(filename, html=True)
    # print(doc.body)
    section_nr = 0  # state machine

    #  the Word text contains one or more sections
    #  quiz_name (multiple)
    #    questions (5) starting with number 1
    #       answers (4)
    # we save the question list into the result list when we detect new question 1
    last_p_type = None
    par_list = []
    not_recognized = []
    # stop after the first question
    for par in d2p.iterators.iter_paragraphs(doc.body):
        par = par.strip()
        if not par:
            continue
        question_nr, weight, text, p_type = parse(par, normalized_fontsize)
        print(f"{par} = {p_type} {weight}")
        if p_type == 'Not recognized':
            not_recognized.append(par)
            continue

        if p_type == 'Quizname':
            quiz_name = text
            par_list.append((p_type, None, text, par))
        if last_p_type == 'Answer' and p_type in ('Question', 'Quizname'):  # last answer
            break
        if p_type == 'Answer':
            # answers.append(Answer(answer_html=text, answer_weight=weight))
            par_list.append((p_type, weight, text, par))
        if p_type == "Question":
            par_list.append((p_type, None, text, par))

        last_p_type = p_type

    return par_list, not_recognized


def parse(text: str, normalized_fontsize: int = 0):
    """
    :param text : text to parse
    :param normalized_fontsize: if non-zero change fontsizes in q & a
    :return determine the type and parsed values of a string by matching a ruleset and returning a
    tuple:
    - question number/answer: int/char,
    - score :int (if answer),
    - text: str,
    - type: str. One of ('Question','Answer', 'Title, 'Pageref', 'Quizname') or 'Not recognized'
    """

    def is_qa(rule):
        return rule.type in ('Question', 'Answer')

    for rule in rules:
        match = rule.pattern.match(text)
        if match:
            if rule.name in ('page_ref_style',):
                # just skip it
                continue
            id_str = match.group('id') if 'id' in match.groupdict() else ''
            id_norm = int(id_str) if id_str.isdigit() else id_str
            score = FULL_SCORE if 'fullscore' in match.groupdict() else 0
            prefix = match.group('prefix') if 'prefix' in match.groupdict() else ''
            text = prefix + match.group('text').strip()
            text = normalize_size(text, normalized_fontsize) if (normalized_fontsize > 0
                                                                 and is_qa(rule)) else text
            return id_norm, score, text, rule.type

    return None, 0, "", 'Not recognized'


def parse_document_d2p(filename: str, check_num_questions: int, normalize_fontsize=False):
    """
        :param  filename: filename of the Word docx to parse
        :param check_num_questions: number of questrions in a section
        :param normalize_fontsize: if True change fontsizes
        :returns a list of Tuples[
        - quiz_names: str
        - questions: List[
            - question_name: str,
            - List[ Answers: list of Tuple[name:str, weight:int]]]"""
    #  from docx produce a text with minimal HTML formatting tags b,i, font size
    #  1) questiontitle
    #    a) wrong answer
    #    b) !right answer
    doc = d2p.docx2python(filename, html=True)
    # print(doc.body)
    section_nr = 0  # state machine
    last_p_type = None
    quiz_name = None
    not_recognized = []
    result = []
    answers = []

    #  the Word text contains one or more sections
    #  quiz_name (multiple)
    #    questions (5) starting with number 1
    #       answers (4)
    # we save the question list into the result list when we detect new question 1

    for par in d2p.iterators.iter_paragraphs(doc.body):
        par = par.strip()
        if not par:
            continue
        question_nr, weight, text, p_type = parse(par, normalize_fontsize)
        print(f"{par} = {p_type} {weight}")
        if p_type == 'Not recognized':
            not_recognized.append(par)
            continue

        if p_type == 'Quizname':
            last_quiz_name = quiz_name  # we need it, when saving question_list
            quiz_name = text
        if last_p_type == 'Answer' and p_type in ('Question', 'Quizname'):  # last answer
            question_list.append((question_text, answers))
            answers = []
        if p_type == 'Answer':
            answers.append(Answer(answer_html=text, answer_weight=weight))
        if p_type == "Question":
            question_text = text
            if question_nr == 1:
                print("New quiz is being parsed")
                if section_nr > 0:  # after first section add the quiz+questions
                    result.append((last_quiz_name, question_list))
                question_list = []
                section_nr += 1

        last_p_type = p_type
    # handle last question
    question_list.append((question_text, answers))
    # handle last section
    result.append((quiz_name, question_list))
    # should_be = 'Questions pertaining to the Introduction'
    # assert result[0][0] == should_be,
    # f"Error: is now \n{result[0][0]}<eol> should be \n{should_be}<eol>"
    for question_list in result:
        nr_questions = len(question_list[1])
        if check_num_questions:
            if nr_questions != check_num_questions:
                raise IncorrectNumberofQuestions(f"Questionlist {question_list[0]} has "
                                                 f"{nr_questions} questions "
                                                 f"this should be {check_num_questions} questions")
        for questions in question_list[1]:
            assert len(questions[1]) == 4, f"{questions[0]} only {len(questions[1])} of 4 answers"
            tot_weight = 0
            for ans in questions[1]:
                tot_weight += ans.answer_weight
            if tot_weight != FULL_SCORE:
                raise IncorrectAnswerMarking(f"Check right/wrong marking and weights in "
                                             f"Q '{questions[0]}'\n Ans {questions[1]}")

    print('--- not recognized --' if not_recognized else '--- all lines were recognized ---')
    for line in not_recognized:
        print(line)

    return result


def word2quiz(filename: str,
              course_id: int,
              check_num_questions,
              normalize_fontsize=False,
              testrun=False):
    """
    """
    os.chdir('../data')
    logging.debug(f"We are in folder {os.getcwd()}")
    quiz_data = parse_document_d2p(filename=filename,
                                   check_num_questions=check_num_questions,
                                   normalize_fontsize=normalize_fontsize)
    if testrun:
        return quiz_data
    canvasrobot = CanvasRobot()
    stats, canvasrobot.create_quizzes_from_data(course_id=course_id,
                                                data=quiz_data)

    return stats


if __name__ == '__main__':
    level = logging.DEBUG  # global loggig level, affects canvasapi too
    logging.basicConfig(filename=f'word2quiz.log', encoding='utf-8', level=level)
    # os.environ['LANGUAGE'] = 'en'
    if GUI:
        ctk.set_appearance_mode("Light")  # Modes: system (default/Mac), light, dark
        ctk.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green
        root = ctk.CTk()
        root.geometry("600x800")
        root.resizable(False, False)

        app = Word2Quiz()
        app.init_ui()

        root.mainloop()
        exit()

    # CMD bversion
    lc = gettext.find('base', 'locales')
    logging.debug(f"locales: {lc}")
    files = glob.glob('../data/*.docx')
    filename = Prompt.ask(_("Enter filename"), choices=files, show_choices=True)
    with console.status(_("Working..."), spinner="dots"):
        try:
            result = word2quiz(filename,
                               course_id=34,
                               check_num_questions=6,
                               testrun=False)
        except FileNotFoundError as e:
            console.print(f'\n[bold red]Error:[/] {e}')
        except (IncorrectNumberofQuestions, IncorrectAnswerMarking) as e:
            console.print(f'\n[bold red]Error:[/] {e}')
        else:
            pprint(result)
