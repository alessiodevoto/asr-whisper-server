import argparse
import logging
import os
import sys
import time
from datetime import datetime
from argparse import ArgumentParser

from flask import Flask, jsonify, request, abort, render_template
from flask import send_from_directory
import whisper

from utils import TextNormalizer, load_audio

 

# Init app and logger, must be visible everywhere.
app = Flask(__name__)
logger = logging.getLogger(__name__)

# Model must be visible everywhere as well. 
# ***IMPORTANT*** when handling a request in multithread option, Flask will create a copy of this, 
# which would be super inefficient. This is intended to be used only in single threaded environement.
model = None 


@app.errorhandler(400)
def resource_not_found(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(500)
def internal_error(e):
    return jsonify(error=str(e)), 500


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/user_manual')
def display_reference():
    return send_from_directory(directory=app.static_folder,
                               path='asr-it-postman-whisper.pdf',
                               mimetype='application/pdf')
                               


@app.route('/predict', methods=['POST'])
def predict():

    # Retrieve model instance. (Works only in single threaded environment).
    global model
    
    # Initialize empty response to be populated further on.
    response = {}
    
    request_start = time.time()
    app.logger.info('Received new request!')

    # Get file.
    files = request.files
    app.logger.info(f'Request files:{files}')
    if 'audio' not in files.keys():
        abort(400, description='Set the key <audio> in the body of the request and load the file to analyze.')

    # Get parameters for inference from request.
    # Check how they are built on client side.
    use_gpu = bool(int(request.form.get('use_gpu', default=0))) # TODO implement GPU prediction, when we have a dedicated GPU (possibly never).
    device = 'cuda' if use_gpu else 'cpu'  
    language = str(request.form.get('language', default='it'))
    beam_size = int(request.form.get('beam_width', default=0)) 
    temperature = float(request.form.get('temperature', default=0.0))
    patience = float(request.form.get('patience', default=0.0))
    best_of = int(request.form.get('best_of', default=0)) 
    
    settings = {
        'language': language if language != 'DETECT' else None, # TODO check this
        'beam_size': beam_size if beam_size > 0 else None, 
        'temperature': temperature,
        'best_of': best_of if best_of > 0 else None,
        'fp16': True if device == 'cuda' else False
        }  
    # whisper bug(?), must add this later.
    if patience > 0: 
        settings['patience'] = patience
    
    app.logger.info(f"Request settings: {settings}")
    app.logger.info(f"Request asked to use: {device}")

    # Try and load model to device, managing CUDA exceptions.
    app.logger.info(f'Loading model to device: {device}')
    load_start = time.time()
    try:
        model = model.to(device)
    except Exception as e: # TODO improve this 
        app.logger.exception(e)
        response['info'] = e
        try:
            app.logger.info('Failed to load to cuda, attempting CPU.')
            model = model.to('cpu')
        except Exception as e:
            app.logger.exception(e)
            abort(500, description=f'{e}')

    
    load_end = time.time()
    loading_time = load_end - load_start
    app.logger.info(f'Loading model to device: {device} took {loading_time:.2f} seconds.')


    try:
        # We have to: (1) load audio, (2) perform inference, (3) post process output.
        # 1. Load audio. Use torch cause can't use whisper default for library incompatibility.
        audio_load_start = time.time()
        audio_filestorage = files['audio']
        audio = load_audio(audio_filestorage)
        audio = whisper.pad_or_trim(audio)
        audio_load_end = time.time()
        audio_load_time = audio_load_end - audio_load_start
        app.logger.info(f'Audio loading took {audio_load_time:.2f} seconds.')

        # 2. Perform inference.
        inference_start = time.time()
        result = model.transcribe(audio, **settings)
        transcript = result['text']
        inference_end = time.time()
        inference_time = inference_end-inference_start
        app.logger.info(f'Raw prediction: {transcript}.')
        app.logger.info(f'Inference took {inference_time:.2f} seconds.')

        # 3. Perform post processing with Normalizer.
        postproc_start = time.time()
        transcript = TextNormalizer().normalize_text(transcript)
        app.logger.info(f'Normalized prediction: {transcript}.')
        postproc_end = time.time()
        postproc_time = postproc_end - postproc_start
        app.logger.info(f'Post processing took {postproc_time:.2f} seconds.')

        # We should now populate the response with: (1) settings, (2) transcription, (3) processing times.
        # 1. Settings. 
        response['settings'] = settings
        
        # 2. Transcription.
        response['results'] = transcript # TODO list of transcriptions
        response['language'] = result['language']
        
        # 3. Processing times. 
        request_end = time.time()
        total_time = request_end - request_start
        response['processing_times'] = {
            f'loading model to {device}': f'{loading_time:.2f}', # TODO maybe should be string
            'audio loading': f'{audio_load_time:.2f}',
            'inference': f'{inference_time:.2f}',
            'post processing': f'{postproc_time:.2f}',
            'total': f'{total_time:.2f}'
            } 
    except Exception as e:
        audio = None
        app.logger.exception(e)
        abort(400, description=f'{e}')

    response = jsonify(response)
    return response


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--port')
    parser.add_argument('--ssl_context') # See here for enabling https https://werkzeug.palletsprojects.com/en/2.2.x/serving/#werkzeug.serving.run_simple
    parser.add_argument('--logs_path', type=str, default=f'./logs/{datetime.now().strftime("%d-%m-%Y_%H:%M:%S")}_whisper.log')
    parser.add_argument('--model_path', type=str, default='./model/')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--whisper_version', type=str, default='tiny')
    args = parser.parse_args()

    

    # Default logging configuration.
    logging.basicConfig(filename=args.logs_path, level=logging.INFO)
    print(f'Just set the default log file to: {args.logs_path}')
    if args.verbose:
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # Load model into memory.
    app.logger.info(f'Starting up application! Downloading and setting up model whisper {args.whisper_version}.')
    model_load_start = time.time()
    model = whisper.load_model(args.whisper_version, download_root=args.model_path, in_memory=True)
    model_load_end = time.time()
    model_load = model_load_end - model_load_start
    app.logger.info(f'Downloading and setting up model took {model_load:.2f} seconds.')
    

    app.run(host='0.0.0.0', port=args.port, ssl_context=args.ssl_context)


"""
@dataclass(frozen=True)
class DecodingOptions:
    task: str = "transcribe"  # whether to perform X->X "transcribe" or X->English "translate"
    language: Optional[str] = None  # language that the audio is in; uses detected language if None

    # sampling-related options
    temperature: float = 0.0
    sample_len: Optional[int] = None  # maximum number of tokens to sample
    best_of: Optional[int] = None     # number of independent samples to collect, when t > 0
    beam_size: Optional[int] = None   # number of beams in beam search, when t == 0
    patience: Optional[float] = None  # patience in beam search (https://arxiv.org/abs/2204.05424)

    # options for ranking generations (either beams or best-of-N samples)
    length_penalty: Optional[float] = None   # "alpha" in Google NMT, None defaults to length norm

    # prompt, prefix, and token suppression
    prompt: Optional[Union[str, List[int]]] = None   # text or tokens for the previous context
    prefix: Optional[Union[str, List[int]]] = None   # text or tokens to prefix the current context
    suppress_blank: bool = True                      # this will suppress blank outputs

    # list of tokens ids (or comma-separated token ids) to suppress
    # "-1" will suppress a set of symbols as defined in `tokenizer.non_speech_tokens()`
    suppress_tokens: Optional[Union[str, Iterable[int]]] = "-1"

    # timestamp sampling options
    without_timestamps: bool = False              # use <|notimestamps|> to sample text tokens only
    max_initial_timestamp: Optional[float] = 0.0  # the initial timestamp cannot be later than this

    # implementation details
    fp16: bool = True  # use fp16 for most of the calculation

@dataclass(frozen=True)
class DecodingResult:
    audio_features: Tensor
    language: str
    language_probs: Optional[Dict[str, float]] = None
    tokens: List[int] = field(default_factory=list)
    text: str = ""
    avg_logprob: float = np.nan
    no_speech_prob: float = np.nan
    temperature: float = np.nan
    compression_ratio: float = np.nan

"""
