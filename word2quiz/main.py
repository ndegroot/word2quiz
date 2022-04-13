"""main module of word2quiz"""
import re
import os
from pprint import pprint
import attrs
import docx2python as d2p


# from docx import Document  # package - python-docx !
# import docx2python as d2p

# from xdocmodel import iter_paragraphs
@attrs.define
class Answer:  # pylint: disable=too-few-public-methods
    """canvas answer see for complete list of (valid) fields
    https://canvas.instructure.com/doc/api/quiz_questions.html#:~:text=An%20Answer-,object,-looks%20like%3A
    """
    answer_html: str
    answer_weight: int


FULL_SCORE = 100
NORMALIZE_FONTSIZE = True

# the patterns
title_pattern = re.compile(r"^<font size=\"(?P<fontsize>\d+)\"><u>(?P<text>.*)</u></font>")
title_style_pattern = \
    re.compile(r"^<span style=\"font-size:(?P<fontsize>[\dpt]+)\"><u>(?P<text>.*)</u>")

quiz_name_pattern = \
    re.compile(r"^<font size=\"(?P<fontsize>\d+[^\"]+)\"><b>(?P<text>.*)\s*</b></font>")
quiz_name_style_pattern = re.compile(
    r"^<span style=\"font-size:(?P<fontsize>[\dpt]+)"
    r"(;text-transform:uppercase)?\"><b>(?P<text>.*)\s*</b></span>")
# special match Sam
page_ref_style_pattern = re.compile(r'(\(pp\.\s+[\d-]+)')

q_pattern_fontsize = re.compile(r'^(?P<id>\d+)[).]\s+'
                                r'<font size="(?P<fontsize>\d+)">(?P<text>.*)</font>')
q_pattern = re.compile(r"^(?P<id>\d+)[).]\s+(?P<text>.*)")

# '!' before the text of answer marks it as the right answer
# idea: use [\d+]  for partially correct answer the sum must be FULL_SCORE
a_ok_pattern_fontsize = re.compile(
    r'^(?P<id>[a-d])\)\s+<font size="(?P<fontsize>\d+)">.*(?P<fullscore>!)(?P<text>.*)</font>')
a_ok_pattern = re.compile(r"^(?P<id>[a-d])\)\s+.*(?P<fullscore>!)(?P<text>.*)")
# match a-d then ')' then skip whitespace and all chars up to '!' after answer skip </font>

a_wrong_pattern_fontsize = re.compile(r'^(?P<id>[a-d])\)\s+'
                                      r'<font size="(?P<fontsize>\d+)(?P<text>.*)</font>')
a_wrong_pattern = re.compile(r"^(?P<id>[a-d])\)\s+(?P<text>.*)")

rules = [
    dict(name='title', pattern=title_pattern, type='Title'),
    dict(name='title_style', pattern=title_style_pattern, type='Title'),
    dict(name='quiz_name', pattern=quiz_name_pattern, type='Quizname'),
    dict(name='quiz_name_style', pattern=quiz_name_style_pattern, type='Quizname'),
    dict(name='page_ref_style', pattern=page_ref_style_pattern, type='PageRefStyle'),
    dict(name='question_fontsize', pattern=q_pattern_fontsize, type='Question'),
    dict(name='question', pattern=q_pattern, type='Question'),
    dict(name='ok_answer_fontsize', pattern=a_ok_pattern_fontsize, type='Answer'),
    dict(name='ok_answer', pattern=a_ok_pattern, type='Answer'),
    dict(name='wrong_answer_fontsize', pattern=a_wrong_pattern_fontsize, type='Answer'),
    dict(name='wrong_answer', pattern=a_wrong_pattern, type='Answer'),
]


def parse(text: str):
    """ determine the type and parsed values of a string by matching and returning a
    tuple (question number/answer char, score (if answer), text, type, fontsize)

    type is one of (Question, Answer, Title, Pageref, Quizname)"""

    # this should be a datastructure: a list of dicts 'rules' with fields name, pattern

    for rule in rules:
        match = rule['pattern'].match(text)
        if match:
            if rule['name'] in ('page_ref_style',):
                # just skip it
                continue
            id_str = match.group('id') if 'id' in match.groupdict() else ''
            id_norm = int(id_str) if id_str.isdigit() else id_str
            score = FULL_SCORE if 'fullscore' in match.groupdict() else 0
            text = match.group('text').strip()
            fs_str = match.group('fontsize') if 'fontsize' in match.groupdict() else None
            fontsize = int(fs_str) if fs_str and fs_str.isdigit() else fs_str
            return id_norm, score, text, rule['type'], fontsize

    return None, 0, "", 'Not recognized', None


def parse_document_d2p(filename: str, check_num_questions: int):
    """
        :param  filename: filename of the Word docx to parse
        :param check_num_questions: number of questrions in a section
        :return List[
            Tuples[ quiz_names: str,questions: List[ question_name: str,
                                                     List[ Answers: Tuple[name, weight]]]"""
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
        question_nr, weight, text, p_type, fontsize = parse(par)
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
            assert nr_questions == check_num_questions, \
                f"Questionlist {question_list[0]} has {nr_questions} " \
                f"this should be {check_num_questions} questions"
        for questions in question_list[1]:
            assert len(questions[1]) == 4, f"{questions[0]} only {len(questions[1])} of 4 answers"
            tot_weight = 0
            for ans in questions[1]:
                tot_weight += ans.answer_weight
            assert tot_weight == FULL_SCORE, \
                f"Check right/wrong marking and weights in Q '{questions[0]}'\n Ans {questions[1]}"

    # if not_recognized:
    print('--- not recognized --' if not_recognized else '--- all lines were recognized ---')
    for line in not_recognized:
        print(line)

    return result


if __name__ == '__main__':
    parse('1) Question')
    os.chdir('../data')
    print(f"We are in folder {os.getcwd()}")
    result = parse_document_d2p(r'version1.docx', check_num_questions=5)
    pprint(result)
    result = parse_document_d2p(r'version2.docx', check_num_questions=64)
    pprint(result)
