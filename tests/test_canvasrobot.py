from word2quiz import CanvasRobot

cr = CanvasRobot()


def test_getcourses():
    courses = cr.getcourses(6,"teacher")
    assert len(courses) == 6
