
import inspect
from functools import wraps
from stoplight.exceptions import *
from stoplight.rule import *


def validate(**rules):
    """Validation endpoint decorator

    This decorator allows validation of input from user
    API endpoints. This allows separation of business logic
    and avoids convoluted validation logic.

    Typical use is as follows:

    @validate({'bird_id': val_bird_id(allow_none=True), 404)
    def get_one(self, bird_id):
        lookup_bird_data(bird_id)

    In this example, bird_id will be passed to val_bird_id
    and validated. If the validation function throws the
    ValidationFailed exception, the specified code will be returned
    in the response and the resultant function will never actually
    be called.
    """
    def _validate(f):
        @wraps(f)
        def wrapper(*args, **kwargs):

            funcparams = inspect.getargspec(f)

            # Holds the list of validated values. Only
            # these values are passed to the endpoint
            outargs = dict()

            # Create dictionary that maps parameters passed
            # to their values passed
            param_values = dict(zip(funcparams.args, args))

            # Bring in kwargs so that we can validate as well
            param_values.update(kwargs)

            for param, rule in rules.items():
                # Where can we get the value? It's either
                # the getter on the rule or we default
                # to verifying parameters.
                getval = rule.getter or param_values.get

                # Call the validation function, passing
                # the value was retrieved from the getter
                try:
                    value = getval(param)

                    # Ensure that this validation function
                    # did not return a funciton. This
                    # checks that the user did not forget to
                    # execute the outer function of a closure
                    # in the rule declaration

                    resp = rule.vfunc(value)

                    if inspect.isfunction(resp):
                        msg = 'Validation function returned a function.'
                        raise ValidationProgrammingError(msg)

                    # If this is a param rule, add the
                    # param to the list of out args
                    if rule.getter is None:
                        outargs[param] = value

                except ValidationFailed as ex:
                    rule.errfunc(error_info=ex)
                    return

            assert funcparams.args[0] == 'self'

            # Validation was successful, call the wrapped function
            return f(args[0], **outargs)
        return wrapper
    return _validate


def validation_function(func):
    """Decorator for creating a validation function"""
    @wraps(func)
    def inner(none_ok=False, empty_ok=False):
        def wrapper(value, **kwargs):
            if none_ok and value is None:
                return

            if not none_ok and value is None:
                msg = 'None value not permitted'
                raise ValidationFailed(msg)

            if empty_ok and value == '':
                return

            if not empty_ok and value == '':
                msg = 'Empty value not permitted'
                raise ValidationFailed(msg)

            func(value)
        return wrapper
    return inner
