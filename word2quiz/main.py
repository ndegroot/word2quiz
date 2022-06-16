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

from lxml import etree
import docx2python as d2p
from rich.console import Console

from canvasrobot import CanvasRobot, Answer


_ = gettext.gettext
console = Console(force_terminal=True)  # too trick Pycharm console into show textattributes
cur_dir = os.getcwd()


# define Python user-defined exceptions
class Error(Exception):
    """ Base class for other exceptions"""
    pass


class IncorrectNumberofQuestions(Error):
    """ the quiz contains unexpected number of questions"""
    pass


class IncorrectAnswerMarking(Error):
    """ the answers of a particular question should have
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


def get_document_html_old(filename: str, normalized_fontsize: int = 0):
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
    Parse a line of (limited: tags B,I) html text (paragraph) determine the type, number (question,answer)
    and score(if answer) using a list of rules. Optinally change the fontsize of
    question and answers
    :param text : text to parse
    :param normalized_fontsize: if non-zero change fontsizes in q & a
    :return tuple:
        - question number/answer: int/char,
        - score :int (if answer),
        - text :str,
        - type :str. One of ('Question','Answer', 'Title, 'Pageref', 'Quizname') or 'Not recognized'
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


def parse_document_d2p(filename: str, check_num_questions: int, normalize_fontsize=0):
    """ Parse the docx file, while checking number of questions and optionally normalize fontsize
        of the questions and answers (the fields in Canvas with HTML formatted texts)
        :param  filename: filename of the Word docx to parse
        :param check_num_questions: number of questions in a section
        :param normalize_fontsize: if > 0 change fontsizes Q&A
        :returns Tuple of [
          quiz_data: a List of Tuples[
            - quiz_names: str
            - questions: List[
                - question_name: str,
                - List[ Answers: List of Tuple[
                    name:str,
                    weight:int]]],
          not_recognized: List of not recognized lines]"""
    #  from docx produce a text with minimal HTML formatting tags b,i, font size
    #  1) question title
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
        logging.debug(f"{par} = {p_type} {weight}")
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
                logging.debug("New quiz is being parsed")
                if section_nr > 0:  # after first section add the quiz+questions
                    result.append((last_quiz_name, question_list))
                question_list = []
                section_nr += 1

        last_p_type = p_type
    # handle last question
    question_list.append((question_text, answers))
    # handle last section
    result.append((quiz_name, question_list))
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

    logging.debug('--- not recognized:' if not_recognized else
                  '--- all lines were recognized ---')
    for line in not_recognized:
        logging.debug(line)

    return result, not_recognized


def word2quiz(filename: str,
              course_id: int,
              check_num_questions,
              normalize_fontsize=False,
              testrun=False):
    """
    """
    os.chdir('../data')
    logging.debug(f"We are in folder {os.getcwd()}")
    quiz_data, not_recognized_lines = parse_document_d2p(filename=filename,
                                                         check_num_questions=check_num_questions,
                                                         normalize_fontsize=normalize_fontsize)
    if testrun:
        return quiz_data
    canvasrobot = CanvasRobot()
    result, stats = canvasrobot.create_quizzes_from_data(course_id=course_id,
                                                         data=quiz_data)

    return stats


if __name__ == "__main__":
    ADMIN = 6
    A_TEACHER = 8
    cr = CanvasRobot()
    courses = cr.get_courses_in_account(ADMIN, [8], this_year=False)
    user = cr.get_user(8)
    for course in cr.get_courses(enrollment_type="teacher"):
        print(f"{course.id} {course.name}")
    print(f"{len(courses)} courses for {user} as teacher")