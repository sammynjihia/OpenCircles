********************CELERY DEAMON-using supervisord****************
The purpose of this documentation is to deamonize celery functions to run celery tasks and scheduled tasks in supervisor mode

# STEP 1

Create celery worker and beat cinfiguration files in

	/etc/supervisor/conf.d

This configuration files are the celery configs for the worker (Celery tasks) and schedules (Celery beat)

	Config File 1: Worker => Opencircles-celery-worker.conf
	Config File 2: Beat   => Opencircles-celery-beat.conf

# STEP 2

Config File 1: Opencircles-celery-worker.conf

[program:Opencircles-celery-worker] ;name of celery worker
command=/home/open_circles/opencircles/bin/celery worker -A OpenCircles --loglevel=INFO ;exectstart
directory=/home/open_circles/opencircles/opencircles ;working directory
user=open_circles
numprocs=1
stdout_logfile=/home/open_circles/opencircles/celery/opencircles_worker.log ; create these log file
stderr_logfile=/home/open_circles/opencircles/celery/opencircles_worker.log ; create these log file
autostart=true
autorestart=true
startsecs=10

; Need to wait for currently executing tasks to finish at shutdown.
; Increase this if you have very long running tasks.
stopwaitsecs = 600

stopasgroup=true

; Set Celery priority higher than default (999)
; so, if rabbitmq is supervised, it will start first.
priority=1000


# STEP 3

Config File 1: Opencircles-celery-beat.conf

[program:Opencircles-celery-beat];name of celery beat
command=/home/open_circles/opencircles/bin/celery -A OpenCircles beat -l info
directory=/home/open_circles/opencircles/opencircles
user=open_circles
numprocs=1
stdout_logfile=/home/open_circles/opencircles/celery/opencircles_beat.log
stderr_logfile=/home/open_circles/opencircles/celery/opencircles_beat.log
autostart=true
autorestart=true
startsecs=10

; Need to wait for currently executing tasks to finish at shutdown.
; Increase this if you have very long running tasks.

; Set Celery priority higher than default (999)
; so, if rabbitmq is supervised, it will start first.
priority=1001

# STEP 4
Supervisord commands to read, update, start, restart and check status of celery worker and beat

1. Read configuration files
	sudo supervisorctl reread Opencircles-celery-beat   
	sudo supervisorctl reread Opencircles-celery-worker

2. Update configuration files
	sudo supervisorctl update Opencircles-celery-beat   
	sudo supervisorctl update Opencircles-celery-worker

3. Start celery worker or beat
	sudo supervisorctl start Opencircles-celery-beat   
	sudo supervisorctl start Opencircles-celery-worker

4. Check status of celery worker or beat
	sudo supervisorctl status Opencircles-celery-beat   
	sudo supervisorctl status Opencircles-celery-worker


