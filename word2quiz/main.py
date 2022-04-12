from docx import Document  # package - python-docx !
# import docx2python as d2p

from xdocmodel import iter_paragraphs
import docx2python as d2p
import re

FULL_SCORE = 100
NORMALIZE_FONTSIZE = True

# the patterns
title_pattern = re.compile(r"^<font size=\"(?P<fontsize>\d+)\"><u>(?P<text>.*)")
title_style_pattern = re.compile(r"^<span style=\"font-size:(?P<fontsize>[\dpt])+\"><u>(?P<text>.*)")
# some fontsizei
quiz_name_pattern = re.compile(r"^<font size=\"(?P<fontsize>\d+[^\"]+)\"><b>(?P<text>.*)\s*</b></font>")
quiz_name_style_pattern = \
    re.compile(
        r"^<span style=\"font-size:(?P<fontsize>[\dpt]+)(;text-transform:uppercase)?\"><b>(?P<text>.*)\s*</b></span>")
# special match Sam
page_ref_style_pattern = re.compile(
    r'(\(pp\.\s+[\d-]+)'
)
q_pattern_fontsize = re.compile(r'^(?P<id>\d+)[).]\s+<font size="(?P<fontsize>\d+)">(?P<text>.*)<\/font>')
q_pattern = re.compile(r"^(?P<id>\d+)[).]\s+(?P<text>.*)")
# '!' before the text of answer marks it as the right answer
# idea use [\d+]  for partially correct answer The sum must be TOT_WEIGHT
a_ok_pattern_fontsize = re.compile(
    r'^(?P<id>[a-d])\)\s+<font size="(?P<fontsize>\d+)">.*(?P<fullscore>!)(?P<text>.*)<\/font>')
a_ok_pattern = re.compile(r"^(?P<id>[a-d])\)\s+.*(?P<fullscore>!)(?P<text>.*)")
# match a-d then ')' then skip whitespace and all chars up to '!' after answer skip </font>
a_wrong_pattern_fontsize = re.compile(r'^(?P<id>[a-d])\)\s+<font size="(?P<fontsize>\d+)(?P<text>.*)<\/font>')
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


# if text:
#    return parse(text)


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
            id_str = match.group('id')
            id_norm = int(id_str) if id_str.isdigit() else id_str
            score = FULL_SCORE if 'fullscore' in match.groupdict() else 0
            text = match.group('text').strip()
            fontsize = int(match.group('fontsize')) if 'fontsize' in match.groupdict() else None
            print(' bingo!')
            return id_norm, score, text, rule['type'], fontsize
    else:
        return None, 0, "", 'Not recognized', None

    q_match_fontsize = q_pattern_fontsize.match(text)
    q_match = q_pattern.match(text)
    a_ok_match_fontsize = a_ok_pattern_fontsize.match(text)
    a_ok_match = a_ok_pattern.match(text)
    a_wrong_match_fontsize = a_wrong_pattern_fontsize.match(text)
    a_wrong_match = a_wrong_pattern.match(text)
    title_match = title_pattern.match(text)
    title_style_match = title_style_pattern.match(text)
    page_ref_match = page_ref_style_pattern.match(text)
    quiz_name_match = quiz_name_pattern.match(text)
    quiz_name_style_match = quiz_name_style_pattern.match(text)

    if q_match_fontsize:  # returns font size
        id_str = q_match_fontsize.group('id')
        id_norm = int(id_str) if id_str.isdigit() else id_str
        text = q_match_fontsize.group('text').strip()
        fontsize = int(q_match_fontsize.group('fontsize'))
        return id_norm, 0, text, "Question", fontsize
    elif q_match:
        return int(q_match.group('id')), 0, q_match.group('text').strip(), "Question", None
    elif a_ok_match_fontsize:
        a_text = a_ok_match_fontsize.group('text')
        fontsize = int(a_ok_match_fontsize.group('fontsize'))
        return None, FULL_SCORE, a_text, "Answer", fontsize
    elif a_ok_match:
        a_text = a_ok_match.group(1)
        return None, FULL_SCORE, a_text, "Answer", None
    elif a_wrong_match_fontsize:
        a_text = a_wrong_match_fontsize.group('text')
        fontsize = int(a_wrong_match_fontsize.group('fontsize'))
        return None, 0, a_text, "Answer", fontsize
    elif a_wrong_match:
        return None, 0, a_wrong_match.group('text'), "Answer", None
    elif title_match:
        return None, 0, title_match.group('text'), "Title", None
    elif title_style_match:
        return None, 0, title_style_match.group('text'), "Title", None
    elif page_ref_match:
        return None, 0, page_ref_match.group('text'), "Pageref", None
    elif quiz_name_match:
        return None, 0, quiz_name_match.group('text'), "Quizname", None
    elif quiz_name_style_match:
        return None, 0, quiz_name_style_match.group('text'), "Quizname", None
    else:
        return None, 0, "", 'Not recognized', None


if __name__ == 'main':
    parse('1) Question')
