""" tests for word2quiz"""
from word2quiz.main import parse


def test_q_or_a_simple():
    src = r'<span style="font-size:32pt"><u>De titel</u>'
    qa_id, weight, text, p_type, fontsize = parse(src)
    assert qa_id in (None, "")
    assert weight == 0
    assert text == "De titel"
    assert p_type == "Title"
    assert fontsize == '32pt'

    qa_id, weight, text, p_type, fontsize = parse('<font size="32"><u>De titel</u></font>')
    assert qa_id in (None, "")
    assert weight == 0
    assert text == "De titel"
    assert p_type == "Title"
    assert fontsize == 32
    question_nr, weight, text, p_type, fontsize = parse('1) fdfdsfffsd')
    assert p_type == "Question"
    assert question_nr == 1
    question_nr, weight, text, p_type, fontsize = parse('a) answer')
    assert p_type == 'Answer' and weight == 0
    question_nr, weight, text, p_type, fontsize = parse('a) !answer')
    assert p_type == 'Answer' and weight == 100
    question_nr, weight, text, p_type, fontsize = \
        parse('d)	!liturgieën een bredere werkelijkheid bestrijken '
              'dan de zeven sacramenten die door de Kerk erkend worden')
    assert p_type == 'Answer' and weight == 100


def test_q_or_a_fontsize():
    src = '61)	<font size="24">αἱ ἀδελφαὶ αὐτῆς </font>'
    question_nr, weight, text, p_type, fontsize = parse(src)
    assert question_nr == 61
    assert text == 'αἱ ἀδελφαὶ αὐτῆς'
    assert p_type == "Question" and fontsize == 24
    question_nr, weight, text, p_type, fontsize = parse('a) <font size="24">haar zusters</font>')
    assert p_type == 'Answer' and weight == 0 and fontsize == 24
    question_nr, weight, text, p_type, fontsize = parse('a) <font size="24">!haar zusters</font>')
    assert p_type == 'Answer' and weight == 100 and fontsize == 24
    question_nr, weight, text, p_type, fontsize = \
        parse('d)	!liturgieën een bredere werkelijkheid bestrijken '
              'dan de zeven sacramenten die door de Kerk erkend worden')
    assert p_type == 'Answer' and weight == 100


# def test_version():
#     assert __version__ == '0.1.1'
