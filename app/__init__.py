import os
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from app.repositories.memory_repository import MemoryRepository
from app.services.learning_service import LearningService, APIError

def create_app(config=None, repository=None):
    app=Flask(__name__)
    app.config.from_mapping(APP_ENV=os.getenv('APP_ENV','development'),
        FRONTEND_ORIGINS=os.getenv('FRONTEND_ORIGINS','http://localhost:3000,http://127.0.0.1:3000'),
        MAX_CONTENT_LENGTH=64*1024, MASTERY_THRESHOLD=80)
    if config: app.config.update(config)
    if app.config['APP_ENV'] not in {'development', 'preview', 'production'}:
        raise ValueError('APP_ENV must be development, preview, or production')
    repo=repository if repository is not None else MemoryRepository()
    if app.config['APP_ENV']=='production' and not repo.persistent:
        raise RuntimeError('Production requires a persistent repository. Integrate SQLRepository first.')
    raw=app.config['FRONTEND_ORIGINS']
    origins=[s.strip() for s in raw.split(',') if s.strip()] if isinstance(raw,str) else raw
    if '*' in origins: raise ValueError('FRONTEND_ORIGINS must list explicit origins')
    CORS(app,resources={r'/api/*':{'origins':origins}},methods=['GET','POST','OPTIONS'],
         allow_headers=['Content-Type'],supports_credentials=False)
    app.extensions['learning_service']=LearningService(repo,app.config['MASTERY_THRESHOLD'])
    app.extensions['repository']=repo
    from app.routes import health, topics, students
    for module in (health,topics,students): app.register_blueprint(module.bp,url_prefix='/api')

    @app.get('/')
    def home():
        return render_template('index.html', preview_mode=app.config['APP_ENV']=='preview')

    @app.errorhandler(APIError)
    def api_error(error):
        body=dict(code=error.code,message=error.message)
        if error.details is not None: body['details']=error.details
        return jsonify(error=body),error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=dict(code=error.name.lower().replace(' ','_'),message=error.description)),error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception('Unhandled API error')
        return jsonify(error=dict(code='internal_error',message='An internal server error occurred')),500
    return app
