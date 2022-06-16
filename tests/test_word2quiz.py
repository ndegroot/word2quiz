""" tests for word2quiz library"""
from word2quiz import parse
from word2quiz import normalize_size
from word2quiz import get_document_html


def test_q_or_a_simple():
    """simple version no fonts size in Q & A"""
    src = r'<span style="font-size:32pt"><u>De titel</u>'
    qa_id, weight, text, p_type = parse(src)
    assert qa_id in (None, "")
    assert weight == 0
    assert text == "De titel"
    assert p_type == "Title"
    # assert fontsize == '32pt'

    qa_id, weight, text, p_type = parse('<font size="32"><u>De titel</u></font>')
    assert qa_id in (None, "")
    assert weight == 0
    assert text == "De titel"
    assert p_type == "Title"

    src = r'<span style="font-size:32pt"><b>Quiznaam</b></span>'
    qa_id, weight, text, p_type = parse(src)
    assert qa_id in (None, "")
    assert p_type == "Quizname"
    assert weight == 0
    assert text == "Quiznaam"
    # assert fontsize == '32pt'
    # assert fontsize == 32
    question_nr, weight, text, p_type = parse('1) fdfdsfffsd')
    assert p_type == "Question"
    assert question_nr == 1
    question_nr, weight, text, p_type = parse('a) answer')
    assert p_type == 'Answer' and weight == 0
    question_nr, weight, text, p_type = parse('a) !answer')
    assert p_type == 'Answer' and weight == 100
    question_nr, weight, text, p_type = \
        parse('d)	!liturgieën een bredere werkelijkheid bestrijken '
              'dan de zeven sacramenten die door de Kerk erkend worden')
    assert p_type == 'Answer' and weight == 100


def test_q_or_a_fontsize():
    """font size versions"""
    src = '61)	<font size="24">αἱ ἀδελφαὶ αὐτῆς </font>'
    question_nr, weight, text, p_type = parse(src)
    assert p_type == "Question"
    assert question_nr == 61
    assert text == '<font size="24">αἱ ἀδελφαὶ αὐτῆς </font>'
    question_nr, weight, text, p_type = parse('a) <font size="24">haar zusters</font>')
    assert p_type == 'Answer' and weight == 0
    question_nr, weight, text, p_type = parse('a) <font size="24">!haar zusters</font>')
    assert p_type == 'Answer' and weight == 100
    assert text == '<font size="24">haar zusters</font>'
    question_nr, weight, text, p_type = \
        parse('d)	!liturgieën een bredere werkelijkheid bestrijken '
              'dan de zeven sacramenten die door de Kerk erkend worden')
    assert p_type == 'Answer' and weight == 100


def test_normalize_size():

    qa_size = 12

    # quiz_name = 'VRAGEN BIJ HOOFDSTUK 1'
    # tobe_q = 'VRAGEN BIJ HOOFDSTUK 1'

    html_fs = '<span style="font-size:24pt">onze πάτερ zusters</span>'

    html_tags = 'onze <i>πάτερ</i> zusters'
    tobe_tags = f'<span style="font-size:{qa_size}pt">onze <i>πάτερ</i> zusters</span>'

    html_not_really = 'onze πάτερ zusters'
    tobe = f'<span style="font-size:{qa_size}pt">onze πάτερ zusters</span>'

    print(f"\n\nWe have tested:\n{tobe}")

    # result_q = normalize_size(quiz_name, qa_size)
    # assert result_q == tobe_q, f"normalize quiz_name fails! ={result_q}"

    print(tobe)
    result_fs = normalize_size(html_fs, qa_size)
    assert result_fs == tobe, f"normalize html_fs fails! ={result_fs}"

    print(tobe_tags)
    result_tags = normalize_size(html_tags, qa_size)
    assert result_tags == tobe_tags, f"normalize html_tags fails! ={result_tags}"

    print(tobe)
    result_not_really = normalize_size(html_not_really, qa_size)
    assert result_not_really == tobe, f"normalize html_not_really fails! ={result_not_really}"

# def test_version():
#     assert __version__ == '0.1.1'
