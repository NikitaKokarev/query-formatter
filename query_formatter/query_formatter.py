# -*- coding: utf-8 -*-
""" QUERY FORMATTER MODULE
"""
__author__ = 'kokarev.nv'

from datetime import datetime
import string


def cast_to_type(value, to_type):    
    """ Converts the value to the specified type.

    Args:
        value (any type): variables value to the cast 
        to_type (str): name of cast operation

    Raises:
        ValueError: returned the exception when "to_type" is not in the whitelist

    Returns:
        any type: casted value of a variable
    """    
    cast_type_func = {
        to_type == 'str': lambda: value,
        to_type == 'int': lambda: int(value),
        to_type == 'date': lambda: datetime.strptime(value, '%Y-%m-%d') ,
        to_type == 'datetime': lambda: datetime.strptime(value, '%Y-%m-%d %H:%M:%S'),
        to_type == 'time': lambda: datetime.strptime(value, '%H:%M:%S'),
        to_type == 'bool' and value == 'True': lambda: True,
        to_type == 'bool' and value == 'False': lambda: False,
        to_type == 'NoneType': lambda: None if value == 'None' else value
    }.get(True)

    # whitelist validation strategy
    if cast_type_func is None:
        raise ValueError(f'Could not cast "{value}" to type "{to_type}"')

    return cast_type_func()


class SqlEscaper():
    """ Isolate and sqlize the value before executing.

    """
    @classmethod
    def escape_literal(cls, value):
        """ Isolate unsupported values by raising an exception. Sqlize the value with specified type.

        Args:
            value (any type): the value of the variable to sqlize

        Raises:
            ValueError: returned the exception when "type_name" is not in the whitelist

        Returns:
            str: sqlized value in the string
        """
        type_name = type(value).__name__
        escape_literal_func = {
            type_name == 'NoneType': lambda: 'NULL',
            type_name in ('int', 'bool'): lambda: str(value),
            type_name == 'date': lambda: f"'{value}'::date",
            type_name == 'datetime': lambda: f"'{value}'::timestamp",
            type_name == 'time': lambda: f"'{value}'::time",
            type_name == 'UUID': lambda: f"'{value}'::uuid",
            type_name == 'str': lambda: value.replace("'", "''"),
            type_name in ('list', 'tuple', 'set'): lambda: ', '.join([cls.escape_literal(item) for item in value])
        }.get(True)
        
        if escape_literal_func is None:
            raise ValueError(f'Type "{value}" unsupported yet')

        return escape_literal_func()

    @classmethod
    def get_condition(cls, value, condition):
        """ Build the string with condition and sqlized value.

        Args:
            value (any type): the value of the variable to sqlize
            condition (str): sql expression, the part of predicate as example

        Returns:
            str: result sql expression
        """
        type_name = type(value).__name__
        if type_name == 'NoneType':
            res = 'IS NULL'
        else:
            res = cls.escape_literal(value)

        return f'{condition} {res}'


class QueryFormatter(string.Formatter):
    """ Format query string pattern by string literals as conditions. Child of the string.Formatter.

        Attrs:
            vformat, _vformat, get_field, format_field: have been redefined
            others: new methods

    """
    def __init__(self, escape_class=None):
        self.escape_class = escape_class
        super(QueryFormatter, self).__init__()

    def vformat(self, format_string, args, kwargs):
        """ Redifined and num recursion depth increased to 10. """
        used_args = set()
        result, _ = self._vformat(format_string, args, kwargs, used_args, 10)
        self.check_unused_args(used_args, args, kwargs)
        return result

    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth, auto_arg_index=0):
        """ Redifined with exception handling during variable processing. Also, the method is prettier. """
        if recursion_depth < 0:
            raise ValueError('Max string recursion exceeded')
        
        result = list()
        for literal_text, field_name, format_spec, transform in self.parse(format_string):

            # add the literal text
            if literal_text:
                result.append(literal_text)

            #  skip iteration if aint no value of a field
            if field_name is None:
                continue
            
            # handle arg indexing when empty field_names are given.
            if (
                field_name == str and auto_arg_index is False or 
                field_name.isdigit() and auto_arg_index
            ):
                raise ValueError(
                    'cannot switch from manual field '
                    'specification to automatic field '
                    'numbering'
                )
            
            if field_name == str():
                field_name = str(auto_arg_index)
                auto_arg_index += 1
            elif field_name.isdigit():
                # disable auto incrementing of arg is digit
                # used later on, then an exception will be raised
                auto_arg_index = False

            # find the object by the field_name reference
            # define the used argument or not
            obj, arg_used = self.get_field(field_name, args, kwargs)
            used_args.add(arg_used)

            # do the object converting by the transform value
            obj = self.convert_field(obj, transform)

            try:
                format_spec, already_formatted = self.format_field(obj, format_spec, kwargs)
            except Exception as ex:
                raise ValueError(
                    f'Error during processing variable "{field_name}" with value "{obj}" in template:\n{format_string}'
                ) from ex

            if not already_formatted:
                # expand the format specification if this is a collection
                format_spec, auto_arg_index = self._vformat(
                    format_spec,
                    args,
                    kwargs,
                    used_args,
                    recursion_depth-1,
                    auto_arg_index=auto_arg_index
                )

            # append it to the result
            result.append(format_spec)

        return ''.join(result), auto_arg_index

    def get_field(self, field_name, args, kwargs):
        """ Redifined with exception handling while getting a field item. """
        try:
            item = super(QueryFormatter, self).get_field(field_name, args, kwargs)
        except (KeyError, AttributeError, TypeError):
            # handle the key if not found
            item = None, field_name
        return item

    def format_field(self, value, spec, kwargs):
        """ Redifined, format the field value with the formatting function. """
        if callable(value):
            value = value()

        format_func = {
            spec.startswith('include'): lambda: self.format_include_value(value, kwargs),
            spec.startswith('repeat:'): lambda: self.format_repeat_value(value, spec, kwargs),
            spec.startswith('in:'): lambda: self.format_in_value(value, spec, is_contained=True),
            spec.startswith('!in:'): lambda: self.format_in_value(value, spec, is_contained=False),
            spec.startswith('exists:'): lambda: self.format_exists_value(value, spec),
            spec.startswith('!exists:'): lambda: self.format_not_exists_value(value, spec),
            spec.startswith('eq:'): lambda: self.format_eq_value(value, spec),
            spec.startswith('!eq:'): lambda: self.format_not_eq_value(value, spec),
            spec.startswith('gt:'): lambda: self.format_gt_value(value, spec),
            spec.startswith('lt:'): lambda: self.format_lt_value(value, spec),
            spec.startswith('if:'): lambda: self.format_if_value(value, spec),
            spec.startswith('!if:'): lambda: self.format_not_if_value(value, spec),
            spec.startswith('tmpl'): lambda: self.format_tmpl_value(value)
        }.get(True)

        if format_func is None:
            field_item = self.format_default_value(value, spec)
        else:
            field_item = format_func()
        
        return field_item

    @staticmethod
    def get_param_list(spec):
        """ Get a list with elems of string.

        Args:
            spec (str): source string to split

        Returns:
            list: elems of string
        """        
        return spec.split(':', 2)
    
    @staticmethod
    def get_compared_value(param_list, value_cond):
        """ Get value from list of params or empty str in item.

        Args:
            param_list (list): string literal parameters
            value_cond (bool): condition for retrieving from a list of elements

        Returns:
            tuple: output item
        """        
        return param_list[2] if value_cond else str(), False

    def format_default_value(self, value, spec):
        """ Format the field value to default.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        if self.escape_class is not None:
            value = self.escape_class.escape_literal(value)
        return super(QueryFormatter, self).format_field(value, spec), True

    def format_include_value(self, value, kwargs):
        """ Format the field value with included value. Formatting patern using an another formatting patern.

        Args:
            value (any type): the value of the variable

        Returns:
            tuple: output item
        """
        param_dict = kwargs
        if isinstance(value, list):
            value, value_param = value
            param_dict = dict(kwargs, **value_param)

        # there is no need to analyze the result of the internal format
        return self.format(value or str(), **param_dict), True

    def format_repeat_value(self, value, spec, kwargs):
        """ Format the field value with repeated value.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :
            kwargs(dict): extended kwargs
        Returns:
            tuple: output item
        """
        if not value:
            return str(), False

        param_list = self.get_param_list(spec)
        res_list = list()

        if isinstance(value, dict):
            for key, item in value.items():
                param_dict = dict(kwargs, **{'item':item, 'key':key})
                res_list.append(self.format(param_list[2], **param_dict))
        else:
            for item in value:
                param_dict = dict(kwargs, **{'item':item})
                res_list.append(self.format(param_list[2], **param_dict))

        # there is no need to analyze the result of the internal format
        return param_list[1].join(res_list), True

    def format_in_value(self, value, spec, is_contained):
        """ Format the field value if it is in the specified value.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :
            is_contained(bool): is contained or not

        Returns:
            tuple: output item
        """
        param_list = self.get_param_list(spec)
        item_list = param_list[1].split(',')
        
        if is_contained:
            item_value = param_list[2]
            def_value = str()
        else:
            item_value = str()
            def_value = param_list[2]
        
        if isinstance(value, list):
            item = item_value if any(
                item_value in map(
                    lambda x: cast_to_type(x, type(item_value).__name__), item_list
                ) for item_value in value
            ) else def_value, False
        else:
            item = item_value if value in item_list else def_value, False

        return item

    def format_exists_value(self, value, spec):
        """ Format the field value if the value exists.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        param_list = self.get_param_list(spec)
        value_cond = type(value).__name__ in ('list', 'tuple') and param_list[1] in value
        return self.get_compared_value(param_list, value_cond)

    def format_not_exists_value(self, value, spec):
        """ Format the field value if the value doesn't exist.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        param_list = self.get_param_list(spec)
        value_cond = not (type(value).__name__ in ('list', 'tuple') and param_list[1] in value)
        return self.get_compared_value(param_list, value_cond)

    def format_eq_value(self, value, spec):
        """ Format the field value if the value has equation.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        param_list = self.get_param_list(spec)
        value_cond = value == cast_to_type(param_list[1], type(value).__name__)
        return self.get_compared_value(param_list, value_cond)

    def format_not_eq_value(self, value, spec):
        """ Format the field value if the value has't equation.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        param_list = self.get_param_list(spec)
        value_cond = value != cast_to_type(param_list[1], type(value).__name__)
        return self.get_compared_value(param_list, value_cond)

    def format_gt_value(self, value, spec):
        """ Format the field value if the value is greater than another value.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        param_list = self.get_param_list(spec)
        value_cond = value is not None and value > cast_to_type(param_list[1], type(value).__name__)
        return self.get_compared_value(param_list, value_cond)

    def format_lt_value(self, value, spec):
        """ Format the field value if the value is lower than another value.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        param_list = self.get_param_list(spec)
        value_cond = value is not None and value < cast_to_type(param_list[1], type(value).__name__)
        return self.get_compared_value(param_list, value_cond)

    @staticmethod
    def format_if_value(value, spec):
        """ Format the field value if the value is not None.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        return spec.partition(':')[-1] if value else str(), False

    @staticmethod
    def format_not_if_value(value, spec):
        """ Format the field value if the value is None.

        Args:
            value (any type): the value of the variable
            spec (str): string literals separated by :

        Returns:
            tuple: output item
        """
        return spec.partition(':')[-1] if not value else str(), False

    def format_tmpl_value(self, value):
        """ Format the field value if the value is a template.

        Args:
            value (any type): the value of the variable

        Returns:
            tuple: output item
        """
        return super(QueryFormatter, self).format_field(value or str(), str()), True
