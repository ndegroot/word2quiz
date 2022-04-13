"""main module of word2quiz"""
import re
# from docx import Document  # package - python-docx !
# import docx2python as d2p

# from xdocmodel import iter_paragraphs

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
    """ determine the type and parsed values of a string by matching and returning
    tuple (question number, value (if answer), text, type)
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


if __name__ == 'main':
    parse('1) Question')
