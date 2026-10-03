from flask import Blueprint, current_app, jsonify, request
bp=Blueprint('students',__name__)
def service(): return current_app.extensions['learning_service']
@bp.post('/students')
def create(): return jsonify(service().create_student(request.get_json())),201
@bp.get('/students/<int:student_id>/dashboard')
def dashboard(student_id): return jsonify(service().dashboard(student_id))
@bp.get('/students/<int:student_id>/progress')
def progress(student_id): return jsonify(service().progress(student_id))
@bp.get('/students/<int:student_id>/attempts')
def attempts(student_id): return jsonify(service().attempts(student_id))
@bp.post('/students/<int:student_id>/diagnostic')
def diagnostic(student_id): return jsonify(service().submit(student_id,request.get_json()))
@bp.post('/students/<int:student_id>/topics/<int:topic_id>/quiz')
def quiz(student_id,topic_id): return jsonify(service().submit(student_id,request.get_json(),topic_id))
