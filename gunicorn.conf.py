import os
bind='0.0.0.0:'+os.getenv('PORT','5000')
# Memory mode requires one process; use more workers only with shared SQL storage.
workers=1
threads=4
timeout=30
accesslog='-'
errorlog='-'
