#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restplus import Api
import flask_jwt_extended
from flask_cors import CORS
from werkzeug.contrib.profiler import ProfilerMiddleware
from werkzeug.exceptions import HTTPException

app = Flask(__name__, instance_relative_config=True,
            template_folder='../templates')


# Load the default configuration
app.config.from_object('config.default')

# Load the configuration from the instance folder
try:
    app.config.from_pyfile('config.py')
except IOError:
    pass

# Load the file specified by the LWP_CONFIG_FILE environment variable
# Variables defined here will override those in the default configuration
try:
    app.config.from_envvar('LWP_CONFIG_FILE')
except RuntimeError:
    pass

try:
    if app.config['PROFILE']:
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
except KeyError:
    pass

app.config['JWT_AUTH_URL_RULE'] = '/api/v1/auth'
app.config['JWT_AUTH_HEADER_PREFIX'] = app.config['JWT_HEADER_TYPE']


class ExceptionAwareApi(Api):

    def handle_error(self, e):
        if isinstance(e, flask_jwt_extended.exceptions.NoAuthorizationError):
            code = 401
            data = {
                'errors': [{
                    'details': 'Authorization Required. \
                    Request does not contain an access token',
                    'status': str(code),
                    'title': 'Unauthorized'
                }]
            }
        elif isinstance(e, jwt.exceptions.ExpiredSignatureError):
            code = 401
            data = {
                'errors': [{
                    'details': 'Token has expired',
                    'status': str(code),
                    'title': 'Unauthorized'
                }]
            }
        elif isinstance(e, KeyError):
            code = 500
            data = {
                'errors': [{
                    'details': 'Can\'t read JSON',
                    'status': str(code),
                    'title': 'Internal server error'
                }]
            }
        else:
            # Did not match a custom exception, continue normally
            return super(ExceptionAwareApi, self).handle_error(e)
        return self.make_response(data, code)

    def abort(self, code=500, message=None, **kwargs):
        '''
        Properly abort the current request.
        Raise a `HTTPException` for the given status `code`.
        Attach any keyword arguments to the exception for later processing.
        :param int code: The associated HTTP status code
        :param str message: An optional details message
        :param kwargs: Any additional data to pass to the error payload
        :raise HTTPException:
        '''
        try:
            flask.abort(code)
        except HTTPException as e:
            # JSON API specs
            kwargs['errors'] = []
            kwargs['errors'].append({})
            kwargs['errors'][0]['detail'] = message
            kwargs['errors'][0]['status'] = str(code)
            kwargs['errors'][0]['title'] = str(e).split(':')[1].lstrip(' ')
            e.data = kwargs
            raise


cors = CORS(
    app,
    resources={r'/*': {'origins': app.config['ALLOW_ORIGIN']}}
)

db = SQLAlchemy(
    app,
    session_options={
        'autoflush': False,
        'autocommit': False,
        'expire_on_commit': False
    }
)

api = ExceptionAwareApi(
    app,
    doc='/doc/',
    license='MIT',
    title='LXC Web Panel API documentation',
    description='https://github.com/lxc-webpanel/lxc-rest',
    validate=True,
    default_mediatype=u'application/json'
)

auth = api.namespace(
    'api/v1/',
    description='Authentication'
)

nslxc = api.namespace(
    'api/v1/lxc/',
    description='Operations related to LXC'
)

nslwp = api.namespace(
    'api/v1/lwp/',
    description='Operations related to LXC Web Panel'
)

jwt = flask_jwt_extended.JWTManager(app)

from app import handlers, models, views, routes
