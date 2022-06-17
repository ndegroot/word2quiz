from word2quiz import CanvasRobot

"""
1. please adjust the 4 constants below, note that this is real 
   live testing
2. at first instance of CanvasRobot you have to supply
   a Canvas API key and the URL of your Canvas
   production or test environment
   Both will be recorded in a secure location using the 
   [keyring](https://pypi.org/project/keyring/) library
"""

ADMIN_ID = 6 # No admin_id available: set to 0
A_TEACHER_ID = 8
NR_COURSES_USER = 5
NR_COURSES_ADMIN = 128

cr = CanvasRobot(ADMIN_ID)


def test_getcourses_current_user():
    """ for current user get the courses"""
    courses = cr.get_courses("teacher")
    assert len(list(courses)) == NR_COURSES_USER


def test_getcourses_admin():
    """ for the admin accpunt (if available) get the courses"""
    if ADMIN_ID:
        courses = cr.get_courses_in_account("teacher")
        assert len(list(courses)) == NR_COURSES_ADMIN
