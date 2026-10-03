from flask import Blueprint, current_app, jsonify
bp=Blueprint('topics',__name__)
def service(): return current_app.extensions['learning_service']
@bp.get('/topics')
def topics(): return jsonify(service().topics())
@bp.get('/topics/<int:topic_id>')
def topic(topic_id): return jsonify(topic=service().topic(topic_id))
@bp.get('/topics/<int:topic_id>/quiz')
def quiz(topic_id): return jsonify(service().quiz(topic_id))
@bp.get('/diagnostic')
def diagnostic(): return jsonify(service().diagnostic())
