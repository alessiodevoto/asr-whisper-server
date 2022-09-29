# asr-whisper-server
This is a simple Flask application for the deployment of Speech to Text transcription with whisper. 
## Quick setup and run
Install requirements with:
```pip install -r requirements.txt```

In order to run the app, just use: 

```
python3 app.py 
```

available options are: 
- ```--port```: port where to make the service available.
- ```--logs_path```: path to **existing directory** where to store logs.
- ```--model_path```: path to **existing directory** where to store model weigths.
- ```--verbose```: with this option, debug messages will be also printed to stdout other than log file.
- ```--whisper_version```: which Whisper version to use (options are: ```['tiny', 'base', 'small', 'medium', 'large']```)
- ```--ssl_context```: use this if you want to also access the service via GUI. (When accessing the service you'll have to trust it anyway). Simplest option to enable https GUI access is using ```--ssl_context=adhoc```. See here for enabling https [flak over https](https://werkzeug.palletsprojects.com/en/2.2.x/serving/#werkzeug.serving.run_simple)

## Run in Docker container