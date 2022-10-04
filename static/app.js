//webkitURL is deprecated but nevertheless
URL = window.URL || window.webkitURL;

var gumStream; 						//stream from getUserMedia()
var rec; 							//Recorder.js object
var input; 							//MediaStreamAudioSourceNode we'll be recording

// shim for AudioContext when it's not avb. 
var AudioContext = window.AudioContext || window.webkitAudioContext;
var audioContext //audio context to help us record

var recordingsList = document.getElementById("recordingsList");
var recordButton = document.getElementById("recordButton");
var stopButton = document.getElementById("stopButton");
var pauseButton = document.getElementById("pauseButton");
var uploadFileButton = document.getElementById("uploadFileButton");

var decodeMethodButton = document.getElementById("decode_method_options");
const beam_search_div = document.getElementById("inference_options_beam");
const greedy_div = document.getElementById("inference_options_greedy");

var langOptions = document.getElementById("language_options")

const patience = document.querySelector('#patience');
const beam_width = document.querySelector('#beam_width');
const temperature = document.querySelector('#temperature');
const best_of = document.querySelector('#best_of');
const use_gpu = document.querySelector('#use_gpu_btn')


// Add listeners
recordButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);
pauseButton.addEventListener("click", pauseRecording);
uploadFileButton.addEventListener('change', uploadFile);
decodeMethodButton.addEventListener("change", showDecodingOptions);

function showDecodingOptions(e){

    method = decodeMethodButton.value;
    if (method == 'beam search'){
        beam_search_div.style.display = "block"
        greedy_div.style.display = "none"
        best_of.value=0 
        temperature.value=0  
    }
    else if ((method == 'sampling')){
        beam_search_div.style.display = "none"
        greedy_div.style.display = "block"
        patience.value=0
        beam_width.value=0 
    }
    else{
        beam_search_div.style.display = "none"
        greedy_div.style.display = "none"
        patience.value=0
        beam_width.value=0 
        best_of.value=0 
        temperature.value=0 
    }
}

function uploadFile(e) {
    const file = e.target.files[0];
    createDownloadLink(file);
}

function startRecording() {
    console.log("recordButton clicked");

    /*
        Simple constraints object, for more advanced audio features see
        https://addpipe.com/blog/audio-constraints-getusermedia/
    */

    var constraints = {audio: true, video: false}

    /*
       Disable the record button until we get a success or fail from getUserMedia()
   */

    recordButton.disabled = true;
    stopButton.disabled = false;
    pauseButton.disabled = false;
    uploadFileButton.diabled = true;

    /*
        We're using the standard promise based getUserMedia()
        https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
    */

    navigator.mediaDevices.getUserMedia(constraints).then(function (stream) {
        console.log("getUserMedia() success, stream created, initializing Recorder.js ...");

        /*
            create an audio context after getUserMedia is called
            sampleRate might change after getUserMedia is called, like it does on macOS when recording through AirPods
            the sampleRate defaults to the one set in your OS for your playback device

        */
        audioContext = new AudioContext();

        //update the format
        document.getElementById("formats").innerHTML = "Format: 1 channel pcm @ " + audioContext.sampleRate / 1000 + "kHz"

        /*  assign to gumStream for later use  */
        gumStream = stream;

        /* use the stream */
        input = audioContext.createMediaStreamSource(stream);

        /*
            Create the Recorder object and configure to record mono sound (1 channel)
            Recording 2 channels  will double the file size
        */
        rec = new Recorder(input, {numChannels: 1})

        //start the recording process
        rec.record()

        console.log("Recording started");

    }).catch(function (err) {
        //enable the record button if getUserMedia() fails
        recordButton.disabled = false;
        stopButton.disabled = true;
        pauseButton.disabled = true
    });
}

function pauseRecording() {
    console.log("pauseButton clicked rec.recording=", rec.recording);
    if (rec.recording) {
        //pause
        rec.stop();
        pauseButton.innerHTML = "Resume";
    } else {
        //resume
        rec.record()
        pauseButton.innerHTML = "Pause";

    }
}

function stopRecording() {
    console.log("stopButton clicked");

    //disable the stop button, enable the record too allow for new recordings
    stopButton.disabled = true;
    recordButton.disabled = false;
    pauseButton.disabled = true;
    uploadFileButton.diabled = false;

    //reset button just in case the recording is stopped while paused
    pauseButton.innerHTML = "Pause";

    //tell the recorder to stop the recording
    rec.stop();

    //stop microphone access
    gumStream.getAudioTracks()[0].stop();

    //create the wav blob and pass it on to createDownloadLink
    rec.exportWAV(createDownloadLink);
}

function createDownloadLink(blob) {

    var url = URL.createObjectURL(blob);
    var au_options = document.createElement('div');
    var au = document.createElement('audio');
    var li = document.createElement('li');
    li.style.marginBottom = "5rem";
    var link = document.createElement('a');


    //name of .wav file to use during upload and download (without extension)
    var filename = new Date().toISOString();

    //add controls to the <audio> element
    au.controls = true;
    au.src = url;
    au.style.float = 'left';
    au.style.width = '75%';

    au_options.appendChild(au)

    //save to disk link
    link.href = url;
    link.download = filename + ".wav"; //download forces the browser to download the file using the filename
    link.innerHTML = "Save to disk";

    //add the filename to the li
    li.appendChild(document.createTextNode(filename))

	//add the new audio element to li
	li.appendChild(au_options)

    //add the save to disk link to li
    // li.appendChild(link);

    //upload link
    var upload = document.createElement('button');
    upload.href = "#";
    upload.innerHTML = "Transcribe";
    upload.addEventListener("click", function (event) {

        loading_div = document.createElement("div");
        loading_div.className="loader";
        li.appendChild(loading_div);

        var xhr = new XMLHttpRequest();
        xhr.onload = function (e) {
            if (this.readyState === 4) {
                // console.log("Server returned: ", e.target.responseText);
                li.appendChild(processResponse(e.target));
                loading_div.remove();
            }
        };

        var fd = new FormData();
        fd.append("audio", blob, filename);
        fd.append("use_gpu", +use_gpu_btn.checked);
        fd.append("beam_width", beam_width.value);
        fd.append("patience", patience.value);
        fd.append("temperature", temperature.value);
        fd.append("best_of", best_of.value);
        fd.append("language", langOptions.value)
        xhr.open("POST", "/predict", true);
        xhr.send(fd);
    })
    li.appendChild(document.createTextNode(" "))//add a space in between
   	// li.appendChild(upload)//add the upload link to li
	au_options.appendChild(upload)
	upload.className = "upload"

    //add the li element to the ol
    recordingsList.prepend(li);
}

function processResponse(response) {
    console.log("Server returned: ", response);
    json_response = JSON.parse(response.responseText);

    results_panel = document.createElement('div');
    results_panel.className = "results";

    if (response.status !== 200) {
        console.log('ERROR');
        error_message = document.createElement("div");
        error_message.setAttribute("style", "margin-top:20%");
        error_message.className = "error_message";
        error_message.appendChild(document.createTextNode(json_response['error']));
        results_panel.appendChild(error_message);
    } else {
        console.log('Json response: ', json_response);
        for (let key in json_response) {

            dropdown_title = document.createElement('button');
            dropdown_title.appendChild(document.createTextNode(key));
            dropdown_title.className = 'dropdown-btn';
            dropdown_elems = document.createElement('div');
            dropdown_elems.className = "dropdown-container"
            
                  
            if (typeof json_response[key] != 'string'){
                dropdown_list = document.createElement('ul');
                for (var elem in json_response[key]) {
                    // console.log(json_response[key][elem])
                    new_elem = document.createElement('li');
                    new_elem.appendChild(document.createTextNode(elem + ': ' + json_response[key][elem]));
                    // console.log(new_elem)
                    dropdown_list.appendChild(new_elem);
                }

                dropdown_elems.appendChild(dropdown_list);
                results_panel.appendChild(dropdown_title);
                results_panel.appendChild(dropdown_elems);
            }
            else{
                field = document.createElement('div');
                field.setAttribute("style", "margin-left:5%");
                field.appendChild(document.createTextNode(json_response[key]))
                dropdown_elems.appendChild(field);
                results_panel.appendChild(dropdown_title);
                results_panel.appendChild(dropdown_elems);
            }

            
            dropdown_title.addEventListener("click", function () {
                this.classList.toggle("active");
                var dropdownContent = this.nextElementSibling;
                console.log(dropdownContent)
                if (dropdownContent.style.display === "block") {
                    dropdownContent.style.display = "none";
                } else {
                    dropdownContent.style.display = "block";
                }
            });

            if (key === 'results' || key === 'info'){
                dropdown_elems.style.display="block";
            }

        }


        // Add a field containing raw response.
        dropdown_title = document.createElement('button');
        dropdown_title.appendChild(document.createTextNode('raw'));
        dropdown_title.className = 'dropdown-btn';
        dropdown_elems = document.createElement('div');
        dropdown_elems.className = "dropdown-container";
        dropdown_elems.appendChild(document.createTextNode(response.responseText));

        results_panel.appendChild(dropdown_title);
        results_panel.appendChild(dropdown_elems);

        dropdown_title.addEventListener("click", function () {
            this.classList.toggle("active");
            var dropdownContent = this.nextElementSibling;
            console.log(dropdownContent)
            if (dropdownContent.style.display === "block") {
                dropdownContent.style.display = "none";
            } else {
                dropdownContent.style.display = "block";
            }
        });

    }
    return results_panel;

}
