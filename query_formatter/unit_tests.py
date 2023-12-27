# -*- coding: utf-8 -*-
""" QUERY FORMATTER UNIT TESTS
"""
__author__ = 'kokarev.nv'

import uuid
from datetime import datetime, date
import unittest

from . import cast_to_type, SqlEscaper, QueryFormatter

QF = QueryFormatter(SqlEscaper())


def unittest_main():
    """ Run unittest suite
    """
    unittest.main(module=__name__, exit=False)


class TestQueryFormatterMethods(unittest.TestCase):
    """ Unit tests of module.

    """
    def test_cast_to_type(self):
        for to_type, value, ans in (
            ('str', "''string_test''", "''string_test''"),
            ('int', '444', 444),
            ('date', str(date.today()), datetime.strptime(str(date.today()), '%Y-%m-%d')),
            ('datetime', str(datetime.now())[:19], datetime.strptime(str(datetime.now())[:19], '%Y-%m-%d %H:%M:%S')),
            ('time', str(datetime.now().time())[:8], datetime.strptime(str(datetime.now().time())[:8], '%H:%M:%S')),
            ('bool', 'True', True),
            ('bool', 'False', False),
            ('NoneType', 'None', None)
        ):
            self.assertEqual(cast_to_type(value, to_type), ans)

    def test_escape_literal(self):
        for value, ans in (
            (None, 'NULL'),
            ("'string_test'", "''string_test''"),
            (444, '444'),
            (True, 'True'),
            (date.today(), f"'{date.today()}'::date"),
            (datetime.now(), f"'{datetime.now()}'::timestamp"),
            (datetime.now().time(), f"'{datetime.now().time()}'::time"),
            (uuid.UUID('39da876c-0e49-49bc-b486-4bd4d4983018'), f"'39da876c-0e49-49bc-b486-4bd4d4983018'::uuid"),
            ([(0, 1), 2, (3,)], '0, 1, 2, 3'),
            ({(0, 1, 2), (3, (4, 5)), 6}, '0, 1, 2, 3, 4, 5, 6')
        ):
            self.assertEqual(SqlEscaper.escape_literal(value), ans)

    def test_get_condition(self):
        CONDITION1 = '... AND Contractor'
        CONDITION2 = '... EXISTS(SELECT "@PrivateFace" FROM PrivateFace WHERE ...) AND contr."HasAddress" ='
        for value, condition, ans in (
            (
                None,
                CONDITION1,
                f'{CONDITION1} IS NULL'
            ), (
                False,
                CONDITION2,
                f'{CONDITION2} False'
            )
        ):
            self.assertEqual(SqlEscaper.get_condition(value, condition), ans)

    def test_format_field(self):
        # in
        self.assertEqual(
            QF.format_field('0', "in:2,1,0:... AND TRUE ...", None),
            ("... AND TRUE ...", False)
        )
        # !in
        self.assertEqual(
            QF.format_field('cotton', "!in:wool,polyester,silk,cotton:... AND FALSE ...", None),
            (str(), False)
        )
        # eq
        self.assertEqual(
            QF.format_field(0, 'eq:0:... AND TRUE ...', None),
            ("... AND TRUE ...", False)
        )
        # !eq
        self.assertEqual(
            QF.format_field('cotton', '!eq:cotton:... AND FALSE ...', None),
            (str(), False)
        )
        # gt
        self.assertEqual(
            QF.format_field(2, 'gt:0:... AND TRUE ...', None),
            ("... AND TRUE ...", False)
        )
        # lt
        self.assertEqual(
            QF.format_field(False, 'lt:True:... AND TRUE ...', None),
            ("... AND TRUE ...", False)
        )
        # if
        self.assertEqual(
            QF.format_field(False, 'if:... AND FALSE ...', None),
            (str(), False)
        )
        # !if
        self.assertEqual(
            QF.format_field('False', '!if:... AND FALSE ...', None),
            (str(), False)
        )
        # tmpl
        self.assertEqual(
            QF.format_field('SELECT * FROM Contractor WHERE "OurClient" IS TRUE', 'tmpl', None),
            ('SELECT * FROM Contractor WHERE "OurClient" IS TRUE', True)
        )
        # exists
        self.assertEqual(
            QF.format_field([0, 'wool', 'None'], 'exists:None:... AND TRUE ...', None),
            ('... AND TRUE ...', False)
        )
        # !exists
        self.assertEqual(
            QF.format_field([0, 'wool', 'None'], '!exists:bobcat:... AND TRUE ...', None),
            ('... AND TRUE ...', False)
        )
        # include
        pattern0 = """SELECT_BLOCK,FROM_BLOCK,WHERE_BLOCK({some_value1:if:... AND TRUE ...} AND {some_value2:in:True,False,None:... AND TRUE ...})"""
        tmpl = """
            SELECT_BLOCK,
            FROM_BLOCK,
            WHERE_BLOCK({pattern0:include})
        """
        ans_tmpl = """
            SELECT_BLOCK,
            FROM_BLOCK,
            WHERE_BLOCK(SELECT_BLOCK,FROM_BLOCK,WHERE_BLOCK(... AND TRUE ... AND ... AND TRUE ...))
        """
        kwargs = {
            'some_value1': 'wool',
            'some_value2': 'True',
            'pattern0': pattern0
        }
        self.assertEqual(
            QF.format(tmpl, **kwargs),
            ans_tmpl
        )
        # repeat
        arg_list = ["""{some_value2:in:True,False,None:... OR FALSE ...}""", """{some_value2:in:True,False,None:... OR NONE ...}"""]
        tmpl = """SELECT_BLOCK,FROM_BLOCK,WHERE_BLOCK({arg_list:repeat:UNION ALL:... OR ...{some_value1:if:... AND TRUE ...} AND {some_value2:in:True,False,None:... AND TRUE ...}... OR ...{item:include}})"""
        kwargs = {
            'some_value1': 'wool',
            'some_value2': 'True',
            'arg_list': arg_list
        }
        ans_tmpl = """SELECT_BLOCK,FROM_BLOCK,WHERE_BLOCK(... OR ...... AND TRUE ... AND ... AND TRUE ...... OR ...... OR FALSE ...UNION ALL... OR ...... AND TRUE ... AND ... AND TRUE ...... OR ...... OR NONE ...)"""
        self.assertEqual(
            QF.format(tmpl, **kwargs),
            ans_tmpl
        )
        # idf
        tmpl = 'SELECT * FROM Contractor WHERE "OurClient" IS TRUE GROUP BY {person_id:idf}'
        kwargs = {
            'person_id': 'PersonId'
        }
        ans_tmpl = 'SELECT * FROM Contractor WHERE "OurClient" IS TRUE GROUP BY "PersonId"'
        self.assertEqual(
            QF.format(tmpl, **kwargs),
            ans_tmpl
        )

    def test_vformat(self):
        kwargs = {
            'exclude_assignee_ids': 444,
            'client_type': 'contractor',
            'contractor': 'contractor'
        }
        tmpl = """
            SELECT_BLOCK,
            FROM_BLOCK,
            WHERE_BLOCK({exclude_assignee_ids:if:some_query=TRUE}, {client_type:eq:contractor:some_query=TRUE})
        """
        ans = """
            SELECT_BLOCK,
            FROM_BLOCK,
            WHERE_BLOCK(some_query=TRUE, some_query=TRUE)
        """
        self.assertEqual(QF.format(tmpl, **kwargs), ans)
