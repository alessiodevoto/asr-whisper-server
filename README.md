# asr-whisper-server
This is a simple Flask application for the deployment of Speech to Text transcription with [whisper](https://github.com/openai/whisper). 
## Option 1: quick setup and run
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
- ```--ssl_context```: use this if you want to also access the service via GUI. (When accessing the service you'll have to trust it anyway). Simplest option to enable https GUI access is using ```--ssl_context=adhoc```. See here for enabling https [flask over https](https://werkzeug.palletsprojects.com/en/2.2.x/serving/#werkzeug.serving.run_simple)

## Option 2: run in Docker container
First build the docker container with:

```
docker build . -t label/whisper-service-image 
```

Run the container:

```
docker run -v /mount/whisper-service:/workspace --shm-size=512m --name whisper-service -p 4006:4006 --gpus all -dit label/whisper-service-image
```
and spawn a shell inside it:
```
sudo docker exec -it whisper-service /bin/bash
```

Follow steps in option 1 to run the app, skipping the installation of requirements.

IMPORTANT: if you run in low level libraries incompatibilities you might wanna run:

```
pip install torch==1.10.0+cu111 torchvision==0.11.0+cu111 torchaudio==0.10.0+cu111 -f https://download.pytorch.org/wh
l/torch_stable.html
```

This will download another torch version.