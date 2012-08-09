# -*- coding: utf-8 -*-

import string
import math


STRF = lambda x: '%.6f' % x


# some code from chicken exporter
def egg_safe_same(s):
    """
    Function that converts names into something suitable for the egg file format - simply puts " around names
    that contain spaces and prunes bad characters, replacing them with an underscore.
    """
    s = s.replace('"', '_')
    if ' ' in s:
        return '"' + s + '"'
    else:
        return s


def indent_string(string, level):
    # indent size is 2 chars
    return string.rjust(len(string) + (level * 2))


def fix_name(name):
    # currently only removes spaces
    return name.replace(" ", "")


def vec_subtract(v1, v2):
    return v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]


def vec_add(v1, v2):
    return v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]


def get_matrix(t):
    return ((1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (t[0], t[1], t[2], 1))


def radians_to_degrees(rads):
    return (rads[0] * 180 / math.pi, rads[1] * 180 / math.pi, rads[2] * 180 / math.pi)


############################################################
# Egg Writing Functions
############################################################


def write_comment(comment, level):
    r = [indent_string('<Comment> {\n', level)]
    for ln in comment.splitlines():
        r.append(indent_string('"%s"' % ln, level + 1))
    r.append(indent_string('\n}\n', level))
    return string.join(r)


def write_transform(matrix, level):
    r = [indent_string('<Transform> {\n', level)]
    r += indent_string('<Matrix4> {\n', level + 1)
    for row in matrix:
        s = " ".join([str(f) for f in row])
        r.append(indent_string(s, level + 2))
        r.append('\n')
    r.append(indent_string('}\n', level + 1))
    r.append(indent_string('}\n', level))
    return r
